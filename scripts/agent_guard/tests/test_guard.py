"""Testy strážce skillů (scripts/agent_guard/guard.py).

Události se posílají stejně jako z Claude Code (JSON hooku) přes `run_claude`,
takže testy pokrývají jádro i adaptér. Stav sessions jde do dočasného adresáře.
Testy nezávisí na skillech repozitáře, takže soubor je shodný ve všech
repozitářích se strážcem (kanonická verze je v linuxadm).
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from guard_module import guard

SKILL_EDIT = """---
name: edit-skill
description: "Úprava konfigurace: vzor s dvojtečkou v popisu."
metadata:
  guard:
    paths:
      - "conf/*.conf"
      - {glob: "inventory/*.yml", contains: "special_block"}
    commands: ['\\bdeploy-tool\\b']
    verify:
      - paths: ["conf/*.conf"]
        commands: ['check_conf\\.sh']
        message: "spusť check_conf.sh"
      - paths: ["ui/*.html"]
        reads: ["**/*.png"]
        message: "prohlédni snímky"
---

# Edit skill
"""

SKILL_FOREIGN = """---
name: foreign-skill
description: Příspěvky do cizích projektů.
metadata:
  guard:
    foreign_repos:
      own_owners: [me]
      forbid: ['Co-Authored-By:\\s*Claude', 'Generated with \\[?Claude Code']
      confirm: true
---

# Foreign skill
"""


def git(cwd: Path, *args: str) -> None:
    """Spustí git v adresáři bez globální konfigurace."""
    subprocess.run(["git", "-C", str(cwd), "-c", "user.name=T", "-c", "user.email=t@e",
                    *args], check=True, capture_output=True)


@pytest.fixture(name="project")
def fixture_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Projekt se dvěma skilly v gitu a vlastním adresářem stavu."""
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    root = tmp_path / "proj"
    for name, text in (("edit-skill", SKILL_EDIT), ("foreign-skill", SKILL_FOREIGN)):
        (root / "skills" / name).mkdir(parents=True)
        (root / "skills" / name / "SKILL.md").write_text(text, encoding="utf-8")
    (root / "conf").mkdir()
    (root / "conf" / "a.conf").write_text("x\n", encoding="utf-8")
    (root / "inventory").mkdir()
    (root / "inventory" / "plain.yml").write_text("a: 1\n", encoding="utf-8")
    (root / "inventory" / "special.yml").write_text("special_block: |\n", encoding="utf-8")
    git(root, "init", "-q")
    git(root, "add", ".")
    git(root, "commit", "-qm", "init")
    return root


def foreign_repo(tmp_path: Path, owner: str) -> Path:
    """Repozitář s originem na GitHubu daného vlastníka a jedním commitem."""
    repo = tmp_path / f"repo-{owner}"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "remote", "add", "origin", f"https://github.com/{owner}/x.git")
    (repo / "f").write_text("1", encoding="utf-8")
    git(repo, "add", "f")
    git(repo, "commit", "-qm", "první")
    return repo


class Session:
    """Pomocník, který posílá události jedné session."""

    def __init__(self, root: Path, session_id: str = "s1", agent_id: str = "") -> None:
        self.root = root
        self.session_id = session_id
        self.agent_id = agent_id
        self.counter = 0

    def send(self, event: str, **fields: Any) -> dict[str, Any]:
        """Pošle událost a vrátí výstup hooku."""
        payload = {"hook_event_name": event, "session_id": self.session_id,
                   "cwd": str(fields.pop("cwd", self.root)), **fields}
        if self.agent_id:
            payload["agent_id"] = self.agent_id
        return guard.run_claude(json.dumps(payload), self.root)

    def read(self, rel: str) -> None:
        """Agent přečte soubor nástrojem Read."""
        self.send("PostToolUse", tool_name="Read",
                  tool_input={"file_path": str(self.root / rel)})

    def edit(self, rel: str, new: str = "y", post: bool = True) -> dict[str, Any]:
        """Agent upraví soubor nástrojem Edit (před akcí a případně po ní)."""
        tool_input = {"file_path": str(self.root / rel), "old_string": "x",
                      "new_string": new}
        out = self.send("PreToolUse", tool_name="Edit", tool_input=tool_input)
        if post and not denied(out):
            self.send("PostToolUse", tool_name="Edit", tool_input=tool_input)
        return out

    def bash(self, command: str, cwd: Path | None = None,
             run: bool = True) -> tuple[dict[str, Any], dict[str, Any]]:
        """Agent spustí příkaz: hook před, příkaz, hook po."""
        self.counter += 1
        tool_use_id = f"t{self.counter}"
        common = {"tool_name": "Bash", "tool_input": {"command": command},
                  "tool_use_id": tool_use_id, "cwd": cwd or self.root}
        pre = self.send("PreToolUse", **common)
        post: dict[str, Any] = {}
        if not denied(pre) and run:
            subprocess.run(command, shell=True, cwd=cwd or self.root, check=False,
                           capture_output=True)
            post = self.send("PostToolUse", **common)
        return pre, post


def decision(out: dict[str, Any]) -> str:
    """Rozhodnutí PreToolUse z výstupu hooku."""
    return str(out.get("hookSpecificOutput", {}).get("permissionDecision", "allow"))


def denied(out: dict[str, Any]) -> bool:
    """Zamítl hook akci?"""
    return decision(out) == "deny"


def test_edit_requires_skill_until_read(project: Path) -> None:
    """Úprava souboru pod skillem projde až po jeho načtení."""
    session = Session(project)
    out = session.edit("conf/a.conf")
    assert denied(out)
    assert "skills/edit-skill/SKILL.md" in out["hookSpecificOutput"]["permissionDecisionReason"]
    session.read("skills/edit-skill/SKILL.md")
    assert not denied(session.edit("conf/a.conf"))


def test_unrelated_edit_and_read_pass(project: Path) -> None:
    """Soubor mimo spouštěče se upravuje volně; čtení se nehlídá."""
    session = Session(project)
    assert session.edit("inventory/plain.yml") == {}
    assert session.send("PreToolUse", tool_name="Read",
                        tool_input={"file_path": str(project / "conf/a.conf")}) == {}


def test_contains_qualifier(project: Path) -> None:
    """Spouštěč s `contains` platí podle obsahu souboru nebo nového textu."""
    session = Session(project)
    assert denied(session.edit("inventory/special.yml", post=False))
    assert not denied(session.edit("inventory/plain.yml", post=False))
    assert denied(session.edit("inventory/plain.yml", new="special_block: 1", post=False))


def test_compaction_resets_reads(project: Path) -> None:
    """Po zhuštění kontextu je potřeba skill načíst znovu."""
    session = Session(project)
    session.read("skills/edit-skill/SKILL.md")
    out = session.send("SessionStart", source="compact")
    assert "zhuštěn" in out["hookSpecificOutput"]["additionalContext"]
    assert denied(session.edit("conf/a.conf"))


def test_sessions_and_subagents_are_separate(project: Path) -> None:
    """Načtení platí jen pro tutéž session a téhož (sub)agenta."""
    Session(project).read("skills/edit-skill/SKILL.md")
    assert not denied(Session(project).edit("conf/a.conf", post=False))
    assert denied(Session(project, "s2").edit("conf/a.conf", post=False))
    assert denied(Session(project, agent_id="sub1").edit("conf/a.conf", post=False))


def test_command_trigger_and_read_via_cat(project: Path) -> None:
    """Příkaz se spouštěčem projde až po načtení skillu (i přes cat)."""
    session = Session(project)
    pre, _ = session.bash("echo deploy-tool")
    assert denied(pre)
    session.bash("cat skills/edit-skill/SKILL.md >/dev/null")
    pre, _ = session.bash("echo deploy-tool")
    assert not denied(pre)


def test_bash_edit_detected_after_the_fact(project: Path) -> None:
    """Úprava souboru z shellu se zjistí po běhu a agent dostane zpětnou vazbu."""
    session = Session(project)
    _, post = session.bash("echo z >> conf/a.conf")
    assert post.get("decision") == "block"
    assert "conf/a.conf" in post["reason"]
    _, post = session.bash("echo z >> inventory/plain.yml")
    assert post == {}


def test_bash_edit_in_subproject(project: Path) -> None:
    """Podprojekt s vlastním skills/ uvnitř repozitáře: cesty z gitu sedí."""
    sub = project / "sub"
    (sub / "skills" / "edit-skill").mkdir(parents=True)
    (sub / "skills" / "edit-skill" / "SKILL.md").write_text(SKILL_EDIT, encoding="utf-8")
    (sub / "conf").mkdir()
    (sub / "conf" / "a.conf").write_text("x\n", encoding="utf-8")
    git(project, "add", ".")
    git(project, "commit", "-qm", "sub")
    session = Session(sub)
    _, post = session.bash("echo z >> conf/a.conf", cwd=sub)
    assert post.get("decision") == "block" and "conf/a.conf" in post["reason"]
    _, post = session.bash("echo z >> conf/a.conf", cwd=project)
    assert "sub/conf" not in post.get("reason", "")


def test_stop_requires_verification(project: Path) -> None:
    """Konec práce po úpravě vyžaduje úspěšné ověření předepsané skillem."""
    session = Session(project)
    session.read("skills/edit-skill/SKILL.md")
    session.edit("conf/a.conf")
    out = session.send("Stop", stop_hook_active=False)
    assert out.get("decision") == "block" and "check_conf.sh" in out["reason"]
    session.bash("true check_conf.sh")
    assert not session.send("Stop", stop_hook_active=False)
    session.edit("conf/a.conf")
    assert session.send("Stop", stop_hook_active=False).get("decision") == "block"


def test_failed_verification_does_not_count(project: Path) -> None:
    """Neúspěšný příkaz (PostToolUseFailure) se za ověření nepočítá."""
    session = Session(project)
    session.read("skills/edit-skill/SKILL.md")
    session.edit("conf/a.conf")
    common = {"tool_name": "Bash", "tool_input": {"command": "false check_conf.sh"},
              "tool_use_id": "f1"}
    session.send("PreToolUse", **common)
    session.send("PostToolUseFailure", **common)
    assert session.send("Stop", stop_hook_active=False).get("decision") == "block"


def test_verification_by_reading_screenshot(project: Path) -> None:
    """Ověření typu `reads` splní přečtení odpovídajícího souboru."""
    session = Session(project)
    (project / "ui").mkdir()
    (project / "ui" / "i.html").write_text("x", encoding="utf-8")
    session.edit("ui/i.html")
    assert session.send("Stop", stop_hook_active=False).get("decision") == "block"
    session.read("shots/a.png")
    assert not session.send("Stop", stop_hook_active=False)


def test_stop_block_limit_tells_user(project: Path) -> None:
    """Opakované zablokování konce má strop a pak se ohlásí uživateli."""
    session = Session(project)
    session.read("skills/edit-skill/SKILL.md")
    session.edit("conf/a.conf")
    for _ in range(guard.STOP_BLOCK_LIMIT):
        assert session.send("Stop", stop_hook_active=True).get("decision") == "block"
    out = session.send("Stop", stop_hook_active=True)
    assert "decision" not in out and "bez ověření" in out["systemMessage"]


def test_own_repo_commit_needs_nothing(project: Path, tmp_path: Path) -> None:
    """Commit do vlastního repozitáře strážce nehlídá."""
    repo = foreign_repo(tmp_path, "me")
    pre, _ = Session(project).bash(f"cd {repo} && git commit --allow-empty -qm x", run=False)
    assert decision(pre) == "allow"


def test_foreign_commit_requires_skill_and_clean_text(project: Path, tmp_path: Path) -> None:
    """Commit do cizího repozitáře: skill, zakázané texty, žádný dotaz na uživatele."""
    repo = foreign_repo(tmp_path, "upstream")
    session = Session(project)
    pre, _ = session.bash(f"git -C {repo} commit --allow-empty -qm fix", run=False)
    assert denied(pre)
    session.read("skills/foreign-skill/SKILL.md")
    message = "fix\n\nCo-Authored-By: Claude Opus <noreply@anthropic.com>"
    pre, _ = session.bash(f"git -C {repo} commit --allow-empty -qm '{message}'", run=False)
    assert denied(pre)
    assert "Co-Authored-By: Claude" in pre["hookSpecificOutput"]["permissionDecisionReason"]
    pre, _ = session.bash(f"git -C {repo} commit --allow-empty -qm fix", run=False)
    assert decision(pre) == "allow"


def test_foreign_push_checks_unpushed_commits(project: Path, tmp_path: Path) -> None:
    """Push do cizího repozitáře kontroluje zprávy neodeslaných commitů a ptá se."""
    repo = foreign_repo(tmp_path, "upstream")
    session = Session(project)
    session.read("skills/foreign-skill/SKILL.md")
    git(repo, "commit", "--allow-empty", "-qm", "x\n\nGenerated with [Claude Code](u)")
    pre, _ = session.bash("git push fork main", cwd=repo, run=False)
    assert denied(pre)
    git(repo, "commit", "--amend", "--allow-empty", "-qm", "x")
    pre, _ = session.bash("git push fork main", cwd=repo, run=False)
    assert decision(pre) == "ask"


def test_foreign_pr_body_file(project: Path, tmp_path: Path) -> None:
    """Tělo PR ze souboru se kontroluje; proměnná v cestě se odmítne."""
    session = Session(project)
    session.read("skills/foreign-skill/SKILL.md")
    body = tmp_path / "body.md"
    body.write_text("Popis\n\n🤖 Generated with [Claude Code](https://claude.com)\n",
                    encoding="utf-8")
    cmd = f"gh pr create -R upstream/x --title t --body-file {body}"
    pre, _ = session.bash(cmd, run=False)
    assert denied(pre)
    body.write_text("Popis\n", encoding="utf-8")
    pre, _ = session.bash(cmd, run=False)
    assert decision(pre) == "ask"
    pre, _ = session.bash("gh pr create -R upstream/x --body-file $S/b.md", run=False)
    assert denied(pre) and "$S/b.md" in pre["hookSpecificOutput"]["permissionDecisionReason"]


def test_gh_api_write_vs_read(project: Path) -> None:
    """`gh api` do cizího repa: zápis se hlídá, čtení ne."""
    session = Session(project)
    pre, _ = session.bash("gh api repos/upstream/x/pulls/1 -q .body", run=False)
    assert decision(pre) == "allow"
    pre, _ = session.bash("gh api -X PATCH repos/upstream/x/pulls/1 -f body=x", run=False)
    assert denied(pre)
    pre, _ = session.bash("gh api -X PATCH repos/me/x/pulls/1 -f body=x", run=False)
    assert decision(pre) == "allow"


def test_broken_skill_fails_open_with_message(project: Path) -> None:
    """Chybný skill akci nezablokuje, ale uživatel se to dozví."""
    (project / "skills" / "bad").mkdir()
    (project / "skills" / "bad" / "SKILL.md").write_text(
        "---\nname: bad\ndescription: x\n---\n", encoding="utf-8")
    out = Session(project).edit("conf/a.conf", post=False)
    assert "agent-guard nefunguje" in out["systemMessage"]
    assert "chybí blok metadata.guard" in out["systemMessage"]


# --- nativní skilly a symlinky ---------------------------------------------


def link_skill_dirs(root: Path) -> None:
    """Symlinky `.claude/skills` a `.agents/skills` jako v repozitáři."""
    for tool_dir in (".claude", ".agents"):
        (root / tool_dir).mkdir(exist_ok=True)
        (root / tool_dir / "skills").symlink_to("../skills")


def skill_tool(session: Session, name: str, event: str = "PostToolUse") -> None:
    """Agent načte skill nativně nástrojem Skill."""
    session.send(event, tool_name="Skill", tool_input={"skill": name},
                 tool_response={"success": True, "commandName": name})


@pytest.mark.parametrize("tool_dir", [".claude", ".agents"])
def test_read_through_symlink_counts(project: Path, tool_dir: str) -> None:
    """Čtení SKILL.md přes symlink se počítá stejně jako přes skills/."""
    link_skill_dirs(project)
    session = Session(project)
    session.read(f"{tool_dir}/skills/edit-skill/SKILL.md")
    assert not denied(session.edit("conf/a.conf"))


@pytest.mark.parametrize("tool_dir", [".claude", ".agents"])
def test_cat_through_symlink_counts(project: Path, tool_dir: str) -> None:
    """`cat` na SKILL.md přes symlink se počítá jako načtení."""
    link_skill_dirs(project)
    session = Session(project)
    session.bash(f"cat {tool_dir}/skills/edit-skill/SKILL.md >/dev/null")
    pre, _ = session.bash("echo deploy-tool", run=False)
    assert not denied(pre)


def test_edit_through_symlink_needs_own_skill(project: Path) -> None:
    """Úprava skriptu skillu přes symlink vyžaduje jeho SKILL.md."""
    link_skill_dirs(project)
    (project / "skills" / "edit-skill" / "run.sh").write_text("x", encoding="utf-8")
    session = Session(project)
    assert denied(session.edit(".claude/skills/edit-skill/run.sh", post=False))
    session.read(".agents/skills/edit-skill/SKILL.md")
    assert not denied(session.edit(".claude/skills/edit-skill/run.sh", post=False))


def test_native_skill_tool_counts(project: Path) -> None:
    """Úspěšné nativní načtení nástrojem Skill odemkne akci."""
    session = Session(project)
    skill_tool(session, "edit-skill")
    assert not denied(session.edit("conf/a.conf"))


def test_native_skill_does_not_unlock_other_skill(project: Path, tmp_path: Path) -> None:
    """Načtení skillu A neodemkne akci, která vyžaduje skill B."""
    session = Session(project)
    skill_tool(session, "foreign-skill")
    assert denied(session.edit("conf/a.conf", post=False))
    other = Session(project, "s2")
    skill_tool(other, "edit-skill")
    repo = foreign_repo(tmp_path, "upstream")
    pre, _ = other.bash(f"git -C {repo} commit --allow-empty -qm x", run=False)
    assert denied(pre)


def test_native_skill_failure_or_unknown_does_not_count(project: Path) -> None:
    """Neúspěšné volání, neznámý název ani PreToolUse skill neodemknou."""
    session = Session(project)
    skill_tool(session, "edit-skill", event="PreToolUse")
    skill_tool(session, "edit-skill", event="PostToolUseFailure")
    skill_tool(session, "neexistuje")
    skill_tool(session, "anthropic-skills:edit-skill")
    session.send("PostToolUse", tool_name="Skill", tool_input={"skill": "edit-skill"},
                 tool_response={"success": False, "commandName": "edit-skill"})
    assert denied(session.edit("conf/a.conf", post=False))


def test_other_file_in_skill_dir_does_not_count(project: Path) -> None:
    """Přečtení jiného souboru ze složky skillu není načtení skillu."""
    link_skill_dirs(project)
    refs = project / "skills" / "edit-skill" / "references"
    refs.mkdir()
    (refs / "x.md").write_text("x", encoding="utf-8")
    session = Session(project)
    session.read("skills/edit-skill/references/x.md")
    session.read(".claude/skills/edit-skill/references/x.md")
    session.bash("cat skills/edit-skill/references/x.md >/dev/null")
    assert denied(session.edit("conf/a.conf", post=False))


def test_compaction_resets_native_skill(project: Path) -> None:
    """Zhuštění kontextu vynuluje i skill načtený nástrojem Skill."""
    session = Session(project)
    skill_tool(session, "edit-skill")
    session.send("SessionStart", source="compact")
    assert denied(session.edit("conf/a.conf", post=False))


def test_top_level_guard_is_rejected() -> None:
    """Blok guard na nejvyšší úrovni frontmatteru je chyba (patří pod metadata)."""
    text = "---\nname: x\ndescription: x\nguard: {}\n---\n"
    with pytest.raises(guard.GuardConfigError, match="patří pod metadata"):
        guard.parse_frontmatter(text, "x")


def test_invalid_yaml_frontmatter_is_rejected() -> None:
    """Frontmatter musí být platný YAML (popis s `: ` v uvozovkách)."""
    text = "---\nname: x\ndescription: a: b\nmetadata:\n  guard: {}\n---\n"
    with pytest.raises(guard.GuardConfigError, match="platný YAML"):
        guard.parse_frontmatter(text, "x")


def test_invalid_json_is_ignored(project: Path) -> None:
    """Neplatný vstup hooku nic neudělá."""
    assert not guard.run_claude("není json", project)


# --- izolace náročných příkazů ---------------------------------------------

SKILL_ISOLATE = """---
name: isolate-skill
description: Náročné testy jen přes obal.
metadata:
  guard:
    isolate:
      commands: ['(?:^|[;&|(]\\s*)heavy\\b']
      wrapper: 'wrap\\.sh'
      message: "přes wrap.sh"
---

# Isolate skill
"""


def test_isolate_requires_wrapper(project: Path) -> None:
    """Náročný příkaz projde jen přes obal; zmínka v argumentu nevadí."""
    (project / "skills" / "isolate-skill").mkdir()
    (project / "skills" / "isolate-skill" / "SKILL.md").write_text(
        SKILL_ISOLATE, encoding="utf-8")
    session = Session(project)
    pre, _ = session.bash("heavy big.svg", run=False)
    assert denied(pre)
    assert "wrap.sh" in pre["hookSpecificOutput"]["permissionDecisionReason"]
    pre, _ = session.bash("cd x && heavy big.svg", run=False)
    assert denied(pre)
    pre, _ = session.bash("./wrap.sh -- heavy big.svg", run=False)
    assert not denied(pre)
    pre, _ = session.bash("grep heavy notes.txt", run=False)
    assert not denied(pre)


def test_isolate_needs_commands_and_wrapper() -> None:
    """Neúplné pravidlo isolate je chyba konfigurace."""
    with pytest.raises(guard.GuardConfigError):
        guard.skill_from_frontmatter("x", {"guard": {"isolate": {"commands": ["a"]}}}, "x")
