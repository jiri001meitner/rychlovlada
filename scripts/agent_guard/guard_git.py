"""Git, GitHub a CI pro strážce skillů (`guard.py`).

Spouštění programů (jediné místo: `run_tool`), snímky `git status`, cílové
adresáře příkazů, vlastníci vzdálených repozitářů, odchozí texty a stav CI
pushnutých commitů. Modul nezná skilly ani stav session.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import subprocess
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

TOOL_TIMEOUT = 10
# Stav běhů CI, který se počítá za úspěch (gh run list, pole conclusion).
CI_OK = frozenset({"success", "skipped", "neutral"})
CI_FIELDS = "databaseId,workflowName,status,conclusion"
# Řádek `git status --porcelain=v1`: dva znaky stavu, mezera, cesta.
PORCELAIN_PATH = 3

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


def file_text(path: Path) -> str:
    """Obsah textového souboru, prázdný řetězec u chyby nebo binárky."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def run_tool(
    argv: Sequence[str], cwd: Path, timeout: float = TOOL_TIMEOUT
) -> subprocess.CompletedProcess[str]:
    """Spustí program a vrátí jeho výsledek; jediné místo, kde se spouští procesy.

    Program se hledá v `PATH` a spouští se absolutní cestou, argumenty jdou
    seznamem, bez shellu. Chybějící program vyvolá `FileNotFoundError`,
    překročení času `subprocess.TimeoutExpired`; nenulový návratový kód ne.
    """
    program = shutil.which(argv[0])
    if program is None:
        raise FileNotFoundError(f"program {argv[0]} není v PATH")
    return subprocess.run(  # noqa: S603 - absolutní cesta, seznam argumentů, bez shellu
        [program, *argv[1:]],
        cwd=cwd,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=timeout,
        check=False,
    )


def git_output(directory: Path, *args: str) -> str | None:
    """Výstup příkazu git v adresáři, nebo None, když git selže nebo chybí."""
    try:
        result = run_tool(["git", *args], directory)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout if result.returncode == 0 else None


def ci_status(top: Path, push: dict[str, Any], settle_seconds: int) -> str:
    """Stav CI pushnutého commitu: prázdný řetězec, když je hotovo, jinak popis."""
    sha = str(push["sha"])
    runs, error = fetch_ci_runs(top, sha)
    if error:
        return f"stav CI commitu {sha[:7]} nejde zjistit: {error}"
    if not runs and time.time() - float(push["time"]) < settle_seconds:
        return f"CI commitu {sha[:7]} se ještě nespustilo; počkej a zkontroluj gh run list"
    return describe_runs(sha, runs)


def fetch_ci_runs(top: Path, sha: str) -> tuple[list[dict[str, Any]], str]:
    """Běhy CI commitu z `gh run list`, nebo popis chyby."""
    try:
        result = run_tool(
            ["gh", "run", "list", "--commit", sha, "--json", CI_FIELDS, "--limit", "50"], top
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return [], str(exc)
    if result.returncode != 0:
        return [], result.stderr.strip()[:200]
    try:
        runs = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return [], "gh vrátil neplatný výstup"
    return [r for r in runs if isinstance(r, dict)], ""


def describe_runs(sha: str, runs: list[dict[str, Any]]) -> str:
    """Popis běžících nebo neúspěšných běhů; prázdný, když vše skončilo úspěchem."""
    running = [r for r in runs if r.get("status") != "completed"]
    if running:
        names = ", ".join(f"{r.get('workflowName')} ({r.get('databaseId')})" for r in running)
        return f"CI commitu {sha[:7]} běží: {names}; počkej: gh run watch <id> --exit-status"
    failed = [r for r in runs if r.get("conclusion") not in CI_OK]
    if failed:
        names = ", ".join(
            f"{r.get('workflowName')} ({r.get('databaseId')}: {r.get('conclusion')})"
            for r in failed
        )
        return f"CI commitu {sha[:7]} selhalo: {names}; oprav a pushni znovu"
    return ""


def snapshot(root: Path) -> dict[str, list[int]]:
    """Změněné a nesledované soubory projektu s mtime a velikostí.

    Klíčem je cesta relativně ke kořeni projektu. Ten může být podadresářem
    repozitáře (podprojekt s vlastním `skills/`), kdežto `git status
    --porcelain` vypisuje cesty vždy od kořene repozitáře, proto se převádějí.
    """
    top = git_output(root, "rev-parse", "--show-toplevel")
    out = git_output(root, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--", ".")
    if top is None or out is None:
        return {}
    prefix = rel_to_root(Path(os.path.realpath(root)), Path(os.path.realpath(top.strip())))
    prefix = "" if prefix in (None, ".") else prefix + "/"
    result: dict[str, list[int]] = {}
    entries = out.split("\0")
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if len(entry) <= PORCELAIN_PATH:
            continue
        if entry[0] in "RC":
            index += 1  # původní název u přejmenování
        rel = entry[PORCELAIN_PATH:]
        if not rel.startswith(prefix):
            continue
        rel = rel[len(prefix) :]
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
    out = git_output(directory, "remote", "-v") or ""
    owners = set()
    for line in out.splitlines():
        match line.split():
            case [_, url, *_]:
                owner = url_owner(url)
                if owner:
                    owners.add(owner)
    return owners


def has_github_remote(directory: Path) -> bool:
    """Má repozitář vzdálený repozitář na GitHubu (jen tam umí `gh` zjistit CI)?"""
    out = git_output(directory, "remote", "-v") or ""
    return any(GITHUB_OWNER.search(line) for line in out.splitlines())


def url_owner(url: str) -> str:
    """Vlastník repozitáře z adresy remote (u ne-GitHubu host), jinak prázdný řetězec."""
    match = GITHUB_OWNER.search(url)
    if match:
        return match.group(1).lower()
    if "://" in url or re.match(r"^[^/]+@[^/]+:", url):
        return re.sub(r"^[a-z+]+://|^[^@]+@", "", url).split("/")[0].split(":")[0]
    return ""


def api_writes(command: str) -> str:
    """Zapisující volání `gh api` (POST, PATCH, pole -f/-F), jinak prázdný řetězec."""
    api = GH_API.search(command)
    if api and GH_API_WRITE.search(api.group(0)):
        return api.group(0)
    return ""


def publishes(command: str) -> bool:
    """Zveřejní příkaz něco mimo stanici (push, PR, komentář, zápis přes API)?"""
    return bool(GIT_PUSH.search(command) or GH_OUTGOING.search(command) or api_writes(command))


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
        arg = raw.strip("'\"")
        if "$" in arg or "`" in arg:
            unresolved.append(arg)
            continue
        path = to_abs(arg, base)
        if path.is_file():
            texts.append(file_text(path))
        elif arg != "-":
            unresolved.append(arg)
    if GIT_OUTGOING.search(command):
        for directory in effective_dirs(command, cwd):
            texts += pending_commit_messages(directory, amend="--amend" in command)
    return texts, unresolved


def pending_commit_messages(directory: Path, amend: bool) -> list[str]:
    """Zprávy commitů, které ještě nejsou na žádném vzdáleném repozitáři."""
    args = (
        ["log", "-1", "--format=%B%x00", "HEAD"]
        if amend
        else ["log", "--format=%B%x00", "HEAD", "--not", "--remotes"]
    )
    out = git_output(directory, *args) or ""
    return [m for m in out.split("\0") if m.strip()]
