#!/usr/bin/env python3
"""Strážce skillů: vynutí načtení skillu před akcí a ověření před koncem práce.

Pravidla nejsou v tomto souboru. Každý `skills/<nazev>/SKILL.md` je má
ve frontmatteru v bloku `metadata.guard` (popis v `scripts/agent_guard/README.md`).
Jádro je nezávislé na agentovi. Napojení na Claude Code zajišťuje adaptér
`claude` (hooky v `.claude/settings.json`), další agenti mohou mít vlastní.

Stav (načtené skilly, upravené soubory, proběhlá ověření) se vede pro každou
session zvlášť v `${XDG_STATE_HOME:-~/.local/state}/agent-guard/`.

Při vnitřní chybě strážce akci nezablokuje, ale ohlásí chybu uživateli.
Pokud by chyba zablokovala všechny akce, agent by nemohl pracovat ani chybu
opravit. Testy jsou v `tests/` a spouští je `.githooks/pre-commit`.
"""
from __future__ import annotations

import contextlib
import fcntl
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

STATE_TTL_DAYS = 14
STOP_BLOCK_LIMIT = 3
MAIN_AGENT = "main"

READ_VERBS = re.compile(r"\b(cat|sed|head|tail|less|bat|more)\b")
SKILL_PATH = re.compile(r"(?:^|[\s/'\"=])skills/([^/\s'\"]+)/SKILL\.md")
SKILL_DIR = re.compile(r"^skills/([^/]+)/")
# Pole frontmatteru podle specifikace Agent Skills (https://agentskills.io/specification).
FRONTMATTER_FIELDS = {"name", "description", "license", "compatibility", "metadata",
                      "allowed-tools"}
CD_TARGET = re.compile(r"(?:^|[;&|(]\s*)cd\s+(\"[^\"]+\"|'[^']+'|[^\s;&|)]+)")
GIT_C_TARGET = re.compile(r"\bgit\b[^;&|\n]*?\s-C\s+(\"[^\"]+\"|'[^']+'|\S+)")
GIT_OUTGOING = re.compile(r"\bgit\b[^;&|\n]*?\s(commit|push)\b")
GH_OUTGOING = re.compile(
    r"\bgh\s+(?:(?:pr|issue)\s+(?:create|comment|edit|review|close|reopen|merge)"
    r"|repo\s+fork|release\s+create)\b"
)
GH_API = re.compile(r"\bgh\s+api\b[^;&|\n]*")
GH_API_WRITE = re.compile(
    r"(?:-X|--method)\s*['\"]?(?:POST|PATCH|PUT|DELETE)|\s(?:-f|-F|--field|--raw-field)\s"
)
GH_API_REPO = re.compile(r"\brepos/([^/\s'\"]+)/([^/\s'\"]+)")
GH_REPO_ARG = re.compile(r"(?:-R|--repo)[=\s]+['\"]?([^/\s'\"]+)/([^\s'\"]+)")
BODY_FILES = re.compile(
    r"(?:--body-file|--file|-F\s+body=@|--field\s+body=@|\bcommit\b[^;&|\n]*?\s-F)"
    r"[=\s]*(\"[^\"]+\"|'[^']+'|[^\s;&|]+)"
)
GITHUB_OWNER = re.compile(r"github\.com[:/]+([^/]+)/")
GIT_PUSH = re.compile(r"\bgit\b[^;&|\n]*?\spush\b")


@dataclass(frozen=True)
class PathRule:
    """Glob cesty (relativní ke kořeni projektu, nebo absolutní či `~/`)
    s volitelným regexem, který musí soubor obsahovat."""

    glob: str
    contains: re.Pattern[str] | None = None


@dataclass(frozen=True)
class VerifyRule:
    """Po úpravě souboru z `paths` musí úspěšně proběhnout příkaz
    odpovídající `commands`, nebo se musí přečíst soubor z `reads`."""

    rule_id: str
    paths: tuple[PathRule, ...]
    commands: tuple[re.Pattern[str], ...]
    reads: tuple[str, ...]
    message: str


@dataclass(frozen=True)
class ForeignRules:
    """Pravidla pro akce, které jdou do cizích (upstream) repozitářů."""

    own_owners: frozenset[str]
    forbid: tuple[re.Pattern[str], ...]
    confirm: bool


@dataclass(frozen=True)
class IsolateRule:
    """Příkaz odpovídající `commands` smí běžet jen přes obal `wrapper`
    (např. s limitem paměti a disku)."""

    commands: tuple[re.Pattern[str], ...]
    wrapper: re.Pattern[str]
    message: str


@dataclass(frozen=True)
class Skill:
    """Skill a jeho spouštěče z frontmatteru."""

    name: str
    description: str
    paths: tuple[PathRule, ...] = ()
    commands: tuple[re.Pattern[str], ...] = ()
    verify: tuple[VerifyRule, ...] = ()
    foreign: ForeignRules | None = None
    isolate: IsolateRule | None = None

    @property
    def rel_path(self) -> str:
        """Cesta k SKILL.md relativně ke kořeni projektu."""
        return f"skills/{self.name}/SKILL.md"


@dataclass
class Decision:
    """Výsledek vyhodnocení události, nezávislý na agentovi."""

    action: str = "allow"  # allow | deny | ask | feedback | block_stop
    reason: str = ""
    user_message: str = ""
    context: str = ""


class GuardConfigError(ValueError):
    """Chybný blok `guard:` ve frontmatteru skillu."""


def _paths(raw: Any, where: str) -> tuple[PathRule, ...]:
    rules: list[PathRule] = []
    for item in raw or []:
        if isinstance(item, str):
            rules.append(PathRule(item))
        elif isinstance(item, dict) and isinstance(item.get("glob"), str):
            contains = item.get("contains")
            rules.append(PathRule(item["glob"], re.compile(contains) if contains else None))
        else:
            raise GuardConfigError(f"{where}: neplatná položka paths: {item!r}")
    return tuple(rules)


def _regexes(raw: Any, flags: int = 0) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(str(item), flags) for item in raw or [])


def parse_frontmatter(text: str, where: str) -> dict[str, Any]:
    """Vrátí `name`, `description` a `guard` z frontmatteru SKILL.md.

    Frontmatter musí být platný YAML jen s poli specifikace Agent Skills,
    jinak ho nativní načítání skillů (Claude Code, Codex, Gemini) nebo
    validátor `skills-ref` může odmítnout. Blok strážce je proto
    v `metadata.guard`; `guard` na nejvyšší úrovni je chyba.
    """
    if not text.startswith("---\n"):
        raise GuardConfigError(f"{where}: chybí frontmatter")
    end = text.find("\n---", 4)
    if end < 0:
        raise GuardConfigError(f"{where}: neukončený frontmatter")
    try:
        parsed = yaml.safe_load(text[4:end])
    except yaml.YAMLError as exc:
        raise GuardConfigError(f"{where}: frontmatter není platný YAML: {exc}") from exc
    if not isinstance(parsed, dict):
        raise GuardConfigError(f"{where}: frontmatter není mapa")
    unknown = set(parsed) - FRONTMATTER_FIELDS
    if unknown:
        raise GuardConfigError(
            f"{where}: pole mimo specifikaci Agent Skills: {sorted(unknown)}"
            + (" (blok guard patří pod metadata)" if "guard" in unknown else ""))
    metadata = parsed.get("metadata") or {}
    if not isinstance(metadata, dict):
        raise GuardConfigError(f"{where}: metadata nejsou mapa")
    data: dict[str, Any] = {k: v for k, v in parsed.items() if k != "metadata"}
    if "guard" in metadata:
        data["guard"] = metadata["guard"]
    return data


def skill_from_frontmatter(name: str, data: dict[str, Any], where: str) -> Skill:
    """Sestaví Skill z frontmatteru; blok `guard` je povinný (i prázdný)."""
    if "guard" not in data:
        raise GuardConfigError(f"{where}: chybí blok metadata.guard (spouštěče skillu)")
    guard = data["guard"] or {}
    if not isinstance(guard, dict):
        raise GuardConfigError(f"{where}: guard není mapa")
    unknown = set(guard) - {"paths", "commands", "verify", "foreign_repos", "isolate"}
    if unknown:
        raise GuardConfigError(f"{where}: neznámé klíče guard: {sorted(unknown)}")
    verify = []
    for index, item in enumerate(guard.get("verify") or []):
        if not item.get("commands") and not item.get("reads"):
            raise GuardConfigError(f"{where}: verify[{index}] bez commands i reads")
        verify.append(VerifyRule(
            rule_id=f"{name}#{index}",
            paths=_paths(item.get("paths"), where),
            commands=_regexes(item.get("commands")),
            reads=tuple(str(r) for r in item.get("reads") or []),
            message=str(item.get("message", "")),
        ))
    foreign = None
    raw_foreign = guard.get("foreign_repos")
    if raw_foreign:
        foreign = ForeignRules(
            own_owners=frozenset(str(o).lower() for o in raw_foreign.get("own_owners") or []),
            forbid=_regexes(raw_foreign.get("forbid"), re.IGNORECASE),
            confirm=bool(raw_foreign.get("confirm", True)),
        )
    isolate = None
    raw_isolate = guard.get("isolate")
    if raw_isolate:
        if not raw_isolate.get("commands") or not raw_isolate.get("wrapper"):
            raise GuardConfigError(f"{where}: isolate potřebuje commands i wrapper")
        isolate = IsolateRule(
            commands=_regexes(raw_isolate["commands"]),
            wrapper=re.compile(str(raw_isolate["wrapper"])),
            message=str(raw_isolate.get("message", "")),
        )
    return Skill(
        name=name,
        description=str(data.get("description", "")),
        paths=_paths(guard.get("paths"), where),
        commands=_regexes(guard.get("commands")),
        verify=tuple(verify),
        foreign=foreign,
        isolate=isolate,
    )


def load_skills(root: Path) -> list[Skill]:
    """Načte spouštěče všech skillů projektu."""
    skills = []
    for skill_md in sorted(root.glob("skills/*/SKILL.md")):
        where = str(skill_md.relative_to(root))
        data = parse_frontmatter(skill_md.read_text(encoding="utf-8"), where)
        name = skill_md.parent.name
        if data.get("name") != name:
            raise GuardConfigError(f"{where}: name se neshoduje s adresářem")
        skills.append(skill_from_frontmatter(name, data, where))
    return skills


# --- cesty -----------------------------------------------------------------


def to_abs(path: str, cwd: Path) -> Path:
    """Absolutní cesta bez rozbalování symlinků."""
    expanded = os.path.expandvars(os.path.expanduser(path.strip("'\"")))
    return Path(os.path.normpath(cwd / expanded))


def rel_to_root(path: Path, root: Path) -> str | None:
    """Cesta relativně ke kořeni projektu, nebo None mimo projekt."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return None


def real_rel(path: Path, root: Path) -> str | None:
    """Cesta po rozbalení symlinků relativně ke skutečnému kořeni projektu.

    Skilly jsou dostupné i přes symlinky `.claude/skills` a `.agents/skills`,
    takže stejný soubor má víc cest; porovnává se až skutečná cesta.
    """
    return rel_to_root(Path(os.path.realpath(path)), Path(os.path.realpath(root)))


def skill_md_name(path: Path, root: Path) -> str | None:
    """Název skillu, pokud cesta (i přes symlink) vede na jeho SKILL.md."""
    rel = real_rel(path, root) or ""
    match = SKILL_DIR.match(rel)
    if match and rel == f"skills/{match.group(1)}/SKILL.md":
        return match.group(1)
    return None


def glob_matches(rule: PathRule, path: Path, root: Path) -> bool:
    """Shoda absolutní cesty s globem pravidla."""
    if rule.glob.startswith(("/", "~")):
        pattern = os.path.expanduser(rule.glob)
        return PurePosixPath(path.as_posix()).full_match(pattern)
    rel = rel_to_root(path, root)
    return rel is not None and PurePosixPath(rel).full_match(rule.glob)


def file_text(path: Path) -> str:
    """Obsah textového souboru, prázdný řetězec u chyby nebo binárky."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def path_rule_matches(rule: PathRule, path: Path, root: Path, extra_text: str = "") -> bool:
    """Shoda cesty a případně obsahu (současný obsah + nový text úpravy)."""
    if not glob_matches(rule, path, root):
        return False
    if rule.contains is None:
        return True
    return bool(rule.contains.search(file_text(path)) or rule.contains.search(extra_text))


# --- stav ------------------------------------------------------------------


def state_dir() -> Path:
    """Adresář se stavem sessions."""
    base = os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
    return Path(base) / "agent-guard"


def empty_state() -> dict[str, Any]:
    """Výchozí stav session."""
    return {"seq": 0, "reads": {}, "read_log": [], "edits": {}, "verify_runs": {},
            "snapshots": {}, "stop_blocks": 0}


@contextlib.contextmanager
def session_state(session_id: str) -> Iterator[dict[str, Any]]:
    """Načte stav session pod zámkem a po skončení ho uloží."""
    directory = state_dir()
    directory.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", session_id or "unknown")
    path = directory / f"{safe}.json"
    with open(directory / f"{safe}.lock", "a", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = empty_state()
        if path.exists():
            with contextlib.suppress(json.JSONDecodeError, OSError):
                state.update(json.loads(path.read_text(encoding="utf-8")))
        yield state
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state), encoding="utf-8")
        tmp.replace(path)


def cleanup_states() -> None:
    """Smaže stav sessions starších než STATE_TTL_DAYS."""
    limit = time.time() - STATE_TTL_DAYS * 86400
    with contextlib.suppress(OSError):
        for item in state_dir().iterdir():
            if item.stat().st_mtime < limit:
                item.unlink(missing_ok=True)


def next_seq(state: dict[str, Any]) -> int:
    """Pořadové číslo události v session."""
    state["seq"] += 1
    return int(state["seq"])


# --- jádro -----------------------------------------------------------------


@dataclass
class Guard:
    """Vyhodnocuje normalizované události jedné session."""

    root: Path
    skills: list[Skill]
    state: dict[str, Any]
    agent: str = MAIN_AGENT
    notes: list[str] = field(default_factory=list)

    def _reads(self) -> dict[str, int]:
        return self.state["reads"].setdefault(self.agent, {})

    def has_read(self, skill: Skill) -> bool:
        """Načetl agent skill od posledního zhuštění kontextu?"""
        return skill.name in self._reads()

    def _require(self, skills: list[Skill], trigger: str) -> Decision:
        missing = [s for s in dict.fromkeys(skills) if not self.has_read(s)]
        if not missing:
            return Decision()
        listing = "\n".join(f"- {s.rel_path}: {s.description[:160]}" for s in missing)
        return Decision("deny", (
            f"Akce spadá pod skill, který jsi v této session (od posledního zhuštění "
            f"kontextu) nenačetl. Spouštěč: {trigger}\n{listing}\n"
            "Načti skill (nástrojem Skill, nebo celý SKILL.md nástrojem Read), "
            "postupuj podle něj a akci zopakuj."))

    def skills_for_path(self, path: Path, extra_text: str = "") -> list[Skill]:
        """Skilly, jejichž spouštěče odpovídají cestě."""
        found = [s for s in self.skills
                 if any(path_rule_matches(r, path, self.root, extra_text) for r in s.paths)]
        rel = real_rel(path, self.root)
        own = SKILL_DIR.match(rel or "")
        if own and not (rel or "").endswith("/SKILL.md"):
            found += [s for s in self.skills if s.name == own.group(1)]
        return found

    # události před akcí ----------------------------------------------------

    def pre_edit(self, path: Path, new_text: str) -> Decision:
        """Úprava souboru nástrojem (Edit, Write…)."""
        return self._require(self.skills_for_path(path, new_text),
                             f"úprava {rel_to_root(path, self.root) or path}")

    def pre_bash(self, command: str, cwd: Path, tool_use_id: str) -> Decision:
        """Příkaz v shellu: spouštěče příkazů a akce do cizích repozitářů."""
        self.state["snapshots"][tool_use_id] = snapshot(self.root)
        matched = [s for s in self.skills if any(p.search(command) for p in s.commands)]
        decision = self._require(matched, f"příkaz `{command[:120]}`")
        if decision.action != "allow":
            return decision
        decision = self.check_isolate(command)
        if decision.action != "allow":
            return decision
        return self.check_foreign(command, cwd)

    def check_isolate(self, command: str) -> Decision:
        """Náročný příkaz musí běžet přes obal s limity (pravidlo `isolate`)."""
        for skill in self.skills:
            rule = skill.isolate
            if rule and any(p.search(command) for p in rule.commands) \
                    and not rule.wrapper.search(command):
                return Decision("deny", (
                    f"Příkaz musí běžet přes obal podle {skill.rel_path}"
                    f"{': ' + rule.message if rule.message else ''}"))
        return Decision()

    def check_foreign(self, command: str, cwd: Path) -> Decision:
        """Commit, push, PR či komentář do cizího repozitáře."""
        rules = [s for s in self.skills if s.foreign]
        if not rules:
            return Decision()
        own = frozenset().union(*(s.foreign.own_owners for s in rules if s.foreign))
        targets = outgoing_targets(command, cwd, own)
        if not targets:
            return Decision()
        decision = self._require(rules, f"akce do cizího repozitáře ({', '.join(targets)})")
        if decision.action != "allow":
            return decision
        problem = self.forbidden_text(command, cwd, rules)
        if problem:
            return Decision("deny", problem)
        if publishes(command) and any(s.foreign and s.foreign.confirm for s in rules):
            return Decision("ask", (
                f"Odesílá se do cizího projektu ({', '.join(targets)}). Uživatel musí "
                "schválit text a příkaz (skill prispivani-do-cizich-projektu, krok 3)."))
        return Decision()

    @staticmethod
    def forbidden_text(command: str, cwd: Path, rules: list[Skill]) -> str:
        """Důvod zamítnutí, pokud odesílaný text nejde ověřit nebo obsahuje zakázané."""
        texts, unresolved = outgoing_texts(command, cwd)
        if unresolved:
            return ("Text odesílaný do cizího repozitáře nejde zkontrolovat, soubor "
                    f"{', '.join(unresolved)} nejde najít. Uveď cestu bez shellových "
                    "proměnných (absolutní nebo relativní k pracovnímu adresáři).")
        for skill in rules:
            patterns = skill.foreign.forbid if skill.foreign else ()
            for pattern in patterns:
                for text in texts:
                    hit = pattern.search(text)
                    if hit:
                        return (f"Text pro cizí repozitář obsahuje zakázané `{hit.group(0)}` "
                                f"(pravidlo {skill.rel_path}). Odstraň ho, včetně textu, "
                                "který přidává nástroj automaticky.")
        return ""

    # události po akci ------------------------------------------------------

    def post_read(self, path: Path) -> None:
        """Agent přečetl soubor."""
        seq = next_seq(self.state)
        name = skill_md_name(path, self.root)
        if name and any(s.name == name for s in self.skills):
            self._reads()[name] = seq
        log = self.state["read_log"]
        log.append([path.as_posix(), seq])
        del log[:-200]

    def post_skill(self, name: str) -> None:
        """Agent úspěšně načetl skill nativním mechanismem (nástroj Skill)."""
        seq = next_seq(self.state)
        if any(s.name == name for s in self.skills):
            self._reads()[name] = seq

    def post_edit(self, path: Path) -> None:
        """Soubor byl upraven nástrojem."""
        self.state["edits"][path.as_posix()] = next_seq(self.state)
        self.state["stop_blocks"] = 0

    def post_bash(self, command: str, tool_use_id: str) -> Decision:
        """Úspěšně doběhlý příkaz: čtení skillu, ověření, změněné soubory."""
        seq = next_seq(self.state)
        self.state["stop_blocks"] = 0
        if READ_VERBS.search(command):
            for name in SKILL_PATH.findall(command):
                if any(s.name == name for s in self.skills):
                    self._reads()[name] = seq
        for skill in self.skills:
            for rule in skill.verify:
                if any(p.search(command) for p in rule.commands):
                    self.state["verify_runs"][rule.rule_id] = seq
        before = self.state["snapshots"].pop(tool_use_id, None)
        if before is None:
            return Decision()
        changed = changed_files(before, snapshot(self.root))
        need: list[Skill] = []
        for rel in changed:
            path = self.root / rel
            self.state["edits"][path.as_posix()] = seq
            need += [s for s in self.skills_for_path(path) if not self.has_read(s)]
        if not need:
            return Decision()
        decision = self._require(need, f"příkaz změnil {', '.join(changed)}")
        return Decision("feedback", decision.reason
                        + " Změna už proběhla: po načtení skillu ji zkontroluj a oprav.")

    def compacted(self) -> Decision:
        """Zhuštění kontextu: načtené skilly už v kontextu nejsou."""
        self.state["reads"] = {}
        return Decision(context=(
            "Kontext byl zhuštěn, obsah dříve načtených skillů v něm už není. "
            "Strážce (scripts/agent_guard) bude před akcemi vyžadovat jejich nové načtení."))

    def stop(self, stop_hook_active: bool) -> Decision:
        """Konec práce: proběhla po posledních úpravách předepsaná ověření?"""
        missing = self.unverified()
        if not missing:
            self.state["stop_blocks"] = 0
            return Decision()
        text = "\n".join(missing)
        if stop_hook_active and self.state["stop_blocks"] >= STOP_BLOCK_LIMIT:
            self.state["stop_blocks"] = 0
            return Decision(user_message=(
                "agent-guard: práce skončila bez ověření předepsaného skilly:\n" + text))
        self.state["stop_blocks"] += 1
        return Decision("block_stop", (
            "Po posledních úpravách chybí ověření předepsané skillem. Proveď ho, "
            "nebo uživateli výslovně napiš, proč ho provést nejde:\n" + text))

    def unverified(self) -> list[str]:
        """Seznam nesplněných ověření."""
        result = []
        for skill in self.skills:
            for rule in skill.verify:
                edited = [(Path(p), s) for p, s in self.state["edits"].items()
                          if any(path_rule_matches(r, Path(p), self.root) for r in rule.paths)]
                if not edited:
                    continue
                last_edit = max(s for _, s in edited)
                done = self.state["verify_runs"].get(rule.rule_id, 0)
                done = max([done] + [s for p, s in self.state["read_log"]
                                     if any(PurePosixPath(p).full_match(os.path.expanduser(g))
                                            for g in rule.reads)])
                if done < last_edit:
                    files = ", ".join(sorted({rel_to_root(p, self.root) or str(p)
                                              for p, _ in edited}))
                    result.append(f"- {skill.rel_path}: {rule.message} (upraveno: {files})")
        return result


# --- git a cizí repozitáře -------------------------------------------------


def snapshot(root: Path) -> dict[str, list[int]]:
    """Změněné a nesledované soubory projektu s mtime a velikostí.

    Klíčem je cesta relativně ke kořeni projektu. Ten může být podadresářem
    repozitáře (podprojekt s vlastním `skills/`), kdežto `git status
    --porcelain` vypisuje cesty vždy od kořene repozitáře, proto se převádějí.
    """
    try:
        top = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True, timeout=10).stdout.strip()
        out = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain=v1", "-z",
             "--untracked-files=all", "--", "."],
            capture_output=True, check=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return {}
    prefix = rel_to_root(Path(os.path.realpath(root)), Path(os.path.realpath(top)))
    prefix = "" if prefix in (None, ".") else prefix + "/"
    result: dict[str, list[int]] = {}
    entries = out.decode("utf-8", "replace").split("\0")
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if len(entry) < 4:
            continue
        if entry[0] in "RC":
            index += 1  # původní název u přejmenování
        rel = entry[3:]
        if not rel.startswith(prefix):
            continue
        rel = rel[len(prefix):]
        with contextlib.suppress(OSError):
            stat = (root / rel).stat()
            result[rel] = [stat.st_mtime_ns, stat.st_size]
            continue
        result[rel] = [0, -1]
    return result


def changed_files(before: dict[str, list[int]], after: dict[str, list[int]]) -> list[str]:
    """Soubory, které se mezi dvěma snímky změnily."""
    keys = set(before) | set(after)
    return sorted(k for k in keys if before.get(k) != after.get(k))


def effective_dirs(command: str, cwd: Path) -> list[Path]:
    """Adresáře, ve kterých příkaz pracuje (`cd`, `git -C`, jinak cwd)."""
    dirs = [to_abs(m, cwd) for m in CD_TARGET.findall(command)]
    dirs += [to_abs(m, cwd) for m in GIT_C_TARGET.findall(command)]
    return dirs or [cwd]


def remote_owners(directory: Path) -> set[str]:
    """Vlastníci vzdálených repozitářů (u ne-GitHubu celý host)."""
    try:
        out = subprocess.run(["git", "-C", str(directory), "remote", "-v"],
                             capture_output=True, text=True, timeout=10, check=False).stdout
    except (OSError, subprocess.SubprocessError):
        return set()
    owners = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        url = parts[1]
        match = GITHUB_OWNER.search(url)
        if match:
            owners.add(match.group(1).lower())
        elif "://" in url or re.match(r"^[^/]+@[^/]+:", url):
            owners.add(re.sub(r"^[a-z+]+://|^[^@]+@", "", url).split("/")[0].split(":")[0])
    return owners


def api_writes(command: str) -> str:
    """Zapisující volání `gh api` (POST, PATCH, pole -f/-F), jinak prázdný řetězec."""
    api = GH_API.search(command)
    if api and GH_API_WRITE.search(api.group(0)):
        return api.group(0)
    return ""


def publishes(command: str) -> bool:
    """Zveřejní příkaz něco mimo stanici (push, PR, komentář, zápis přes API)?"""
    return bool(GIT_PUSH.search(command) or GH_OUTGOING.search(command)
                or api_writes(command))


def outgoing_targets(command: str, cwd: Path, own: frozenset[str]) -> list[str]:
    """Cizí cíle, kam příkaz zapisuje (commit, push, PR, komentáře)."""
    owners: set[str] = set()
    git_out = bool(GIT_OUTGOING.search(command))
    gh_out = bool(GH_OUTGOING.search(command))
    api = api_writes(command)
    api_write = bool(api)
    if api_write:
        owners |= {m[0].lower() for m in GH_API_REPO.findall(api)}
    if gh_out:
        owners |= {m[0].lower() for m in GH_REPO_ARG.findall(command)}
    if git_out or ((gh_out or api_write) and not owners):
        for directory in effective_dirs(command, cwd):
            owners |= remote_owners(directory)
    return sorted(owners - own)


def outgoing_texts(command: str, cwd: Path) -> tuple[list[str], list[str]]:
    """Texty, které příkaz odešle: příkaz sám, soubory s tělem, zprávy commitů."""
    texts = [command]
    unresolved = []
    base = effective_dirs(command, cwd)[-1]
    for raw in BODY_FILES.findall(command):
        token = raw.strip("'\"")
        if "$" in token or "`" in token:
            unresolved.append(token)
            continue
        path = to_abs(token, base)
        if path.is_file():
            texts.append(file_text(path))
        elif token != "-":
            unresolved.append(token)
    if GIT_OUTGOING.search(command):
        for directory in effective_dirs(command, cwd):
            texts += pending_commit_messages(directory, amend="--amend" in command)
    return texts, unresolved


def pending_commit_messages(directory: Path, amend: bool) -> list[str]:
    """Zprávy commitů, které ještě nejsou na žádném vzdáleném repozitáři."""
    args = ["git", "-C", str(directory), "log", "--format=%B%x00", "HEAD", "--not", "--remotes"]
    if amend:
        args = ["git", "-C", str(directory), "log", "-1", "--format=%B%x00", "HEAD"]
    try:
        out = subprocess.run(args, capture_output=True, text=True, timeout=10, check=False).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    return [m for m in out.split("\0") if m.strip()]


# --- adaptér Claude Code ---------------------------------------------------

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def claude_edit_target(tool_input: dict[str, Any]) -> tuple[str, str]:
    """Cesta a nový text z parametrů nástroje pro úpravy."""
    path = str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")
    parts = [str(tool_input.get(k, "")) for k in ("new_string", "content", "new_source")]
    parts += [str(e.get("new_string", "")) for e in tool_input.get("edits") or []
              if isinstance(e, dict)]
    return path, "\n".join(parts)


def claude_dispatch(guard: Guard, payload: dict[str, Any]) -> Decision:
    """Převede událost Claude Code na volání jádra."""
    event = payload.get("hook_event_name", "")
    tool = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}
    cwd = Path(payload.get("cwd") or guard.root)
    tool_use_id = str(payload.get("tool_use_id", ""))
    decision = Decision()
    if event == "PreToolUse" and tool in EDIT_TOOLS:
        path, text = claude_edit_target(tool_input)
        decision = guard.pre_edit(to_abs(path, cwd), text) if path else Decision()
    elif event == "PreToolUse" and tool == "Bash":
        decision = guard.pre_bash(str(tool_input.get("command", "")), cwd, tool_use_id)
    elif event == "PostToolUse" and tool == "Read":
        guard.post_read(to_abs(str(tool_input.get("file_path", "")), cwd))
    elif event == "PostToolUse" and tool == "Skill":
        response = payload.get("tool_response")
        if not (isinstance(response, dict) and response.get("success") is False):
            guard.post_skill(str(tool_input.get("skill", "")))
    elif event == "PostToolUse" and tool in EDIT_TOOLS:
        path, _ = claude_edit_target(tool_input)
        if path:
            guard.post_edit(to_abs(path, cwd))
    elif event == "PostToolUse" and tool == "Bash":
        decision = guard.post_bash(str(tool_input.get("command", "")), tool_use_id)
    elif event == "PostToolUseFailure" and tool == "Bash":
        guard.state["snapshots"].pop(tool_use_id, None)
    elif event == "SessionStart" and payload.get("source") == "compact":
        decision = guard.compacted()
    elif event == "Stop":
        cleanup_states()
        decision = guard.stop(bool(payload.get("stop_hook_active")))
    return decision


def claude_output(event: str, decision: Decision) -> dict[str, Any]:
    """Výstup hooku Claude Code pro rozhodnutí jádra."""
    out: dict[str, Any] = {}
    if decision.action in ("deny", "ask"):
        out["hookSpecificOutput"] = {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision.action,
            "permissionDecisionReason": decision.reason,
        }
    elif decision.action in ("feedback", "block_stop"):
        out["decision"] = "block"
        out["reason"] = decision.reason
    if decision.context:
        out["hookSpecificOutput"] = {"hookEventName": event,
                                     "additionalContext": decision.context}
    if decision.user_message:
        out["systemMessage"] = decision.user_message
    return out


def run_claude(raw: str, root: Path) -> dict[str, Any]:
    """Zpracuje jednu událost Claude Code; při vnitřní chybě akci propustí."""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    event = str(payload.get("hook_event_name", ""))
    try:
        skills = load_skills(root)
        with session_state(str(payload.get("session_id", ""))) as state:
            guard = Guard(root, skills, state, str(payload.get("agent_id") or MAIN_AGENT))
            decision = claude_dispatch(guard, payload)
    except (GuardConfigError, re.error, yaml.YAMLError, OSError) as exc:
        return {"systemMessage": f"agent-guard nefunguje, akce prošla bez kontroly: {exc}"}
    return claude_output(event, decision)


def main(argv: list[str]) -> int:
    """Vstupní bod: `guard.py claude` čte událost hooku ze stdin."""
    if len(argv) != 2 or argv[1] != "claude":
        print("použití: guard.py claude < událost.json", file=sys.stderr)
        return 2
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
    out = run_claude(sys.stdin.read(), root)
    if out:
        print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
