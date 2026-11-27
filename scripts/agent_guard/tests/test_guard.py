"""Testy strážce skillů (scripts/agent_guard/guard.py).

Události se posílají stejně jako z Claude Code (JSON hooku) přes `run_claude`,
takže testy pokrývají jádro i adaptér. Stav sessions jde do dočasného adresáře.
Příkazy se v testech nespouštějí: změnu souborů, kterou by příkaz udělal,
provede test sám mezi hookem před příkazem a po něm.
Testy nezávisí na skillech repozitáře, takže soubor je shodný ve všech
repozitářích se strážcem (kanonická verze je v linuxadm).
"""

from __future__ import annotations

import json
import unittest
from collections.abc import Callable
from pathlib import Path
from typing import Any

from guard_module import git, guard, isolate_git_env, set_env, temp_dir

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

SKILL_REQUIRES = """---
name: req-skill
description: Skill s povinnými soubory.
metadata:
  guard:
    paths: ["web/*.html"]
    requires: ["kb/pravidla.md", "~/kb-home.md"]
---

# Req skill
"""

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

TOOL_DIRS = (".claude", ".agents")


def make_project(root: Path) -> Path:
    """Projekt se dvěma skilly v gitu."""
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


def foreign_repo(base: Path, owner: str) -> Path:
    """Repozitář s originem na GitHubu daného vlastníka a jedním commitem."""
    repo = base / f"repo-{owner}"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "remote", "add", "origin", f"https://github.com/{owner}/x.git")
    (repo / "f").write_text("1", encoding="utf-8")
    git(repo, "add", "f")
    git(repo, "commit", "-qm", "první")
    return repo


def append(path: Path, text: str = "z\n") -> Callable[[], None]:
    """Účinek příkazu `echo z >> soubor`."""

    def effect() -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(text)

    return effect


def link_skill_dirs(root: Path) -> None:
    """Symlinky `.claude/skills` a `.agents/skills` jako v repozitáři."""
    for tool_dir in TOOL_DIRS:
        (root / tool_dir).mkdir(exist_ok=True)
        (root / tool_dir / "skills").symlink_to("../skills")


def decision(out: dict[str, Any]) -> str:
    """Rozhodnutí PreToolUse z výstupu hooku."""
    return str(out.get("hookSpecificOutput", {}).get("permissionDecision", "allow"))


def denied(out: dict[str, Any]) -> bool:
    """Zamítl hook akci?"""
    return decision(out) == "deny"


def reason(out: dict[str, Any]) -> str:
    """Důvod rozhodnutí PreToolUse."""
    return str(out["hookSpecificOutput"]["permissionDecisionReason"])


class Session:
    """Pomocník, který posílá události jedné session."""

    def __init__(self, root: Path, session_id: str = "s1", agent_id: str = "") -> None:
        self.root = root
        self.session_id = session_id
        self.agent_id = agent_id
        self.counter = 0

    def send(self, event: str, **fields: Any) -> dict[str, Any]:
        """Pošle událost a vrátí výstup hooku."""
        payload = {
            "hook_event_name": event,
            "session_id": self.session_id,
            "cwd": str(fields.pop("cwd", self.root)),
            **fields,
        }
        if self.agent_id:
            payload["agent_id"] = self.agent_id
        result: dict[str, Any] = guard.run_claude(json.dumps(payload), self.root)
        return result

    def read(self, path: str | Path) -> None:
        """Agent přečte soubor nástrojem Read (relativně ke kořeni projektu)."""
        self.send("PostToolUse", tool_name="Read", tool_input={"file_path": str(self.root / path)})

    def edit(self, rel: str, new: str = "y", post: bool = True) -> dict[str, Any]:
        """Agent upraví soubor nástrojem Edit (před akcí a případně po ní)."""
        tool_input = {"file_path": str(self.root / rel), "old_string": "x", "new_string": new}
        out = self.send("PreToolUse", tool_name="Edit", tool_input=tool_input)
        if post and not denied(out):
            self.send("PostToolUse", tool_name="Edit", tool_input=tool_input)
        return out

    def skill(self, name: str, event: str = "PostToolUse", success: bool = True) -> None:
        """Agent načte skill nativně nástrojem Skill."""
        self.send(
            event,
            tool_name="Skill",
            tool_input={"skill": name},
            tool_response={"success": success, "commandName": name},
        )

    def bash(
        self,
        command: str,
        cwd: Path | None = None,
        run: bool = True,
        effect: Callable[[], None] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Agent spustí příkaz: hook před, účinek příkazu, hook po.

        S `run=False` příkaz neproběhne (zajímá jen rozhodnutí před ním).
        """
        self.counter += 1
        common = {
            "tool_name": "Bash",
            "tool_input": {"command": command},
            "tool_use_id": f"t{self.counter}",
            "cwd": cwd or self.root,
        }
        pre = self.send("PreToolUse", **common)
        post: dict[str, Any] = {}
        if not denied(pre) and run:
            if effect:
                effect()
            post = self.send("PostToolUse", **common)
        return pre, post

    def stop(self, active: bool = False) -> dict[str, Any]:
        """Agent končí práci."""
        return self.send("Stop", stop_hook_active=active)


class GuardCase(unittest.TestCase):
    """Společný základ: dočasný adresář, vlastní stav sessions, projekt."""

    def setUp(self) -> None:
        isolate_git_env(self)
        self.tmp = temp_dir(self)
        set_env(self, XDG_STATE_HOME=str(self.tmp / "state"))
        self.project = make_project(self.tmp / "proj")

    def assert_denied(self, out: dict[str, Any]) -> None:
        """Hook akci zamítl."""
        self.assertEqual(decision(out), "deny", out)

    def assert_allowed(self, out: dict[str, Any]) -> None:
        """Hook akci nezamítl."""
        self.assertNotEqual(decision(out), "deny", out)


class EditAndReadTest(GuardCase):
    """Úpravy souborů, čtení skillů a sessions."""

    def test_edit_requires_skill_until_read(self) -> None:
        """Úprava souboru pod skillem projde až po jeho načtení."""
        session = Session(self.project)
        out = session.edit("conf/a.conf")
        self.assert_denied(out)
        self.assertIn("skills/edit-skill/SKILL.md", reason(out))
        session.read("skills/edit-skill/SKILL.md")
        self.assert_allowed(session.edit("conf/a.conf"))

    def test_unrelated_edit_and_read_pass(self) -> None:
        """Soubor mimo spouštěče se upravuje volně; čtení se nehlídá."""
        session = Session(self.project)
        self.assertEqual(session.edit("inventory/plain.yml"), {})
        out = session.send(
            "PreToolUse",
            tool_name="Read",
            tool_input={"file_path": str(self.project / "conf/a.conf")},
        )
        self.assertEqual(out, {})

    def test_contains_qualifier(self) -> None:
        """Spouštěč s `contains` platí podle obsahu souboru nebo nového textu."""
        session = Session(self.project)
        self.assert_denied(session.edit("inventory/special.yml", post=False))
        self.assert_allowed(session.edit("inventory/plain.yml", post=False))
        self.assert_denied(session.edit("inventory/plain.yml", new="special_block: 1", post=False))

    def test_compaction_resets_reads(self) -> None:
        """Po zhuštění kontextu je potřeba skill načíst znovu."""
        session = Session(self.project)
        session.read("skills/edit-skill/SKILL.md")
        out = session.send("SessionStart", source="compact")
        self.assertIn("zhuštěn", out["hookSpecificOutput"]["additionalContext"])
        self.assert_denied(session.edit("conf/a.conf"))

    def test_sessions_and_subagents_are_separate(self) -> None:
        """Načtení platí jen pro tutéž session a téhož (sub)agenta."""
        Session(self.project).read("skills/edit-skill/SKILL.md")
        self.assert_allowed(Session(self.project).edit("conf/a.conf", post=False))
        self.assert_denied(Session(self.project, "s2").edit("conf/a.conf", post=False))
        self.assert_denied(Session(self.project, agent_id="sub1").edit("conf/a.conf", post=False))

    def test_broken_skill_fails_open_with_message(self) -> None:
        """Chybný skill akci nezablokuje, ale uživatel se to dozví."""
        (self.project / "skills" / "bad").mkdir()
        (self.project / "skills" / "bad" / "SKILL.md").write_text(
            "---\nname: bad\ndescription: x\n---\n", encoding="utf-8"
        )
        out = Session(self.project).edit("conf/a.conf", post=False)
        self.assertIn("agent-guard nefunguje", out["systemMessage"])
        self.assertIn("chybí blok metadata.guard", out["systemMessage"])

    def test_invalid_json_is_ignored(self) -> None:
        """Neplatný vstup hooku nic neudělá."""
        self.assertFalse(guard.run_claude("není json", self.project))


class BashTest(GuardCase):
    """Příkazy shellu: spouštěče a úpravy souborů zjištěné po běhu."""

    def test_command_trigger_and_read_via_cat(self) -> None:
        """Příkaz se spouštěčem projde až po načtení skillu (i přes cat)."""
        session = Session(self.project)
        pre, _ = session.bash("echo deploy-tool")
        self.assert_denied(pre)
        session.bash("cat skills/edit-skill/SKILL.md >/dev/null")
        pre, _ = session.bash("echo deploy-tool")
        self.assert_allowed(pre)

    def test_bash_edit_detected_after_the_fact(self) -> None:
        """Úprava souboru z shellu se zjistí po běhu a agent dostane zpětnou vazbu."""
        session = Session(self.project)
        _, post = session.bash(
            "echo z >> conf/a.conf", effect=append(self.project / "conf" / "a.conf")
        )
        self.assertEqual(post.get("decision"), "block")
        self.assertIn("conf/a.conf", post["reason"])
        _, post = session.bash(
            "echo z >> inventory/plain.yml", effect=append(self.project / "inventory" / "plain.yml")
        )
        self.assertEqual(post, {})

    def test_bash_edit_in_subproject(self) -> None:
        """Podprojekt s vlastním skills/ uvnitř repozitáře: cesty z gitu sedí."""
        sub = self.project / "sub"
        (sub / "skills" / "edit-skill").mkdir(parents=True)
        (sub / "skills" / "edit-skill" / "SKILL.md").write_text(SKILL_EDIT, encoding="utf-8")
        (sub / "conf").mkdir()
        (sub / "conf" / "a.conf").write_text("x\n", encoding="utf-8")
        git(self.project, "add", ".")
        git(self.project, "commit", "-qm", "sub")
        session = Session(sub)
        conf = sub / "conf" / "a.conf"
        _, post = session.bash("echo z >> conf/a.conf", cwd=sub, effect=append(conf))
        self.assertEqual(post.get("decision"), "block")
        self.assertIn("conf/a.conf", post["reason"])
        _, post = session.bash("echo z >> conf/a.conf", cwd=self.project, effect=append(conf))
        self.assertNotIn("sub/conf", post.get("reason", ""))


class VerifyTest(GuardCase):
    """Ověření předepsané skillem před koncem práce."""

    def test_stop_requires_verification(self) -> None:
        """Konec práce po úpravě vyžaduje úspěšné ověření předepsané skillem."""
        session = Session(self.project)
        session.read("skills/edit-skill/SKILL.md")
        session.edit("conf/a.conf")
        out = session.stop()
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("check_conf.sh", out["reason"])
        session.bash("true check_conf.sh")
        self.assertFalse(session.stop())
        session.edit("conf/a.conf")
        self.assertEqual(session.stop().get("decision"), "block")

    def test_failed_verification_does_not_count(self) -> None:
        """Neúspěšný příkaz (PostToolUseFailure) se za ověření nepočítá."""
        session = Session(self.project)
        session.read("skills/edit-skill/SKILL.md")
        session.edit("conf/a.conf")
        common = {
            "tool_name": "Bash",
            "tool_input": {"command": "false check_conf.sh"},
            "tool_use_id": "f1",
        }
        session.send("PreToolUse", **common)
        session.send("PostToolUseFailure", **common)
        self.assertEqual(session.stop().get("decision"), "block")

    def test_verification_by_reading_screenshot(self) -> None:
        """Ověření typu `reads` splní přečtení odpovídajícího souboru."""
        session = Session(self.project)
        (self.project / "ui").mkdir()
        (self.project / "ui" / "i.html").write_text("x", encoding="utf-8")
        session.edit("ui/i.html")
        self.assertEqual(session.stop().get("decision"), "block")
        session.read("shots/a.png")
        self.assertFalse(session.stop())

    def test_stop_block_limit_tells_user(self) -> None:
        """Opakované zablokování konce má strop a pak se ohlásí uživateli."""
        session = Session(self.project)
        session.read("skills/edit-skill/SKILL.md")
        session.edit("conf/a.conf")
        for _ in range(guard.STOP_BLOCK_LIMIT):
            self.assertEqual(session.stop(active=True).get("decision"), "block")
        out = session.stop(active=True)
        self.assertNotIn("decision", out)
        self.assertIn("bez ověření", out["systemMessage"])


class ForeignRepoTest(GuardCase):
    """Commity, pushe a zápisy do cizích repozitářů."""

    def test_own_repo_commit_needs_nothing(self) -> None:
        """Commit do vlastního repozitáře strážce nehlídá."""
        repo = foreign_repo(self.tmp, "me")
        pre, _ = Session(self.project).bash(
            f"cd {repo} && git commit --allow-empty -qm x", run=False
        )
        self.assertEqual(decision(pre), "allow")

    def test_foreign_commit_requires_skill_and_clean_text(self) -> None:
        """Commit do cizího repozitáře: skill, zakázané texty, žádný dotaz na uživatele."""
        repo = foreign_repo(self.tmp, "upstream")
        session = Session(self.project)
        pre, _ = session.bash(f"git -C {repo} commit --allow-empty -qm fix", run=False)
        self.assert_denied(pre)
        session.read("skills/foreign-skill/SKILL.md")
        message = "fix\n\nCo-Authored-By: Claude Opus <noreply@anthropic.com>"
        pre, _ = session.bash(f"git -C {repo} commit --allow-empty -qm '{message}'", run=False)
        self.assert_denied(pre)
        self.assertIn("Co-Authored-By: Claude", reason(pre))
        pre, _ = session.bash(f"git -C {repo} commit --allow-empty -qm fix", run=False)
        self.assertEqual(decision(pre), "allow")

    def test_foreign_push_checks_unpushed_commits(self) -> None:
        """Push do cizího repozitáře kontroluje zprávy neodeslaných commitů a ptá se."""
        repo = foreign_repo(self.tmp, "upstream")
        session = Session(self.project)
        session.read("skills/foreign-skill/SKILL.md")
        git(repo, "commit", "--allow-empty", "-qm", "x\n\nGenerated with [Claude Code](u)")
        pre, _ = session.bash("git push fork main", cwd=repo, run=False)
        self.assert_denied(pre)
        git(repo, "commit", "--amend", "--allow-empty", "-qm", "x")
        pre, _ = session.bash("git push fork main", cwd=repo, run=False)
        self.assertEqual(decision(pre), "ask")

    def test_foreign_pr_body_file(self) -> None:
        """Tělo PR ze souboru se kontroluje; proměnná v cestě se odmítne."""
        session = Session(self.project)
        session.read("skills/foreign-skill/SKILL.md")
        body = self.tmp / "body.md"
        body.write_text(
            "Popis\n\n🤖 Generated with [Claude Code](https://claude.com)\n", encoding="utf-8"
        )
        cmd = f"gh pr create -R upstream/x --title t --body-file {body}"
        pre, _ = session.bash(cmd, run=False)
        self.assert_denied(pre)
        body.write_text("Popis\n", encoding="utf-8")
        pre, _ = session.bash(cmd, run=False)
        self.assertEqual(decision(pre), "ask")
        pre, _ = session.bash("gh pr create -R upstream/x --body-file $S/b.md", run=False)
        self.assert_denied(pre)
        self.assertIn("$S/b.md", reason(pre))

    def test_gh_api_write_vs_read(self) -> None:
        """`gh api` do cizího repa: zápis se hlídá, čtení ne."""
        session = Session(self.project)
        pre, _ = session.bash("gh api repos/upstream/x/pulls/1 -q .body", run=False)
        self.assertEqual(decision(pre), "allow")
        pre, _ = session.bash("gh api -X PATCH repos/upstream/x/pulls/1 -f body=x", run=False)
        self.assert_denied(pre)
        pre, _ = session.bash("gh api -X PATCH repos/me/x/pulls/1 -f body=x", run=False)
        self.assertEqual(decision(pre), "allow")


class NativeSkillTest(GuardCase):
    """Nativní načítání skillů nástrojem Skill a přes symlinky."""

    def test_read_through_symlink_counts(self) -> None:
        """Čtení SKILL.md přes symlink se počítá stejně jako přes skills/."""
        link_skill_dirs(self.project)
        for tool_dir in TOOL_DIRS:
            with self.subTest(tool_dir=tool_dir):
                session = Session(self.project, f"read{tool_dir}")
                session.read(f"{tool_dir}/skills/edit-skill/SKILL.md")
                self.assert_allowed(session.edit("conf/a.conf", post=False))

    def test_cat_through_symlink_counts(self) -> None:
        """`cat` na SKILL.md přes symlink se počítá jako načtení."""
        link_skill_dirs(self.project)
        for tool_dir in TOOL_DIRS:
            with self.subTest(tool_dir=tool_dir):
                session = Session(self.project, f"cat{tool_dir}")
                session.bash(f"cat {tool_dir}/skills/edit-skill/SKILL.md >/dev/null")
                pre, _ = session.bash("echo deploy-tool", run=False)
                self.assert_allowed(pre)

    def test_edit_through_symlink_needs_own_skill(self) -> None:
        """Úprava skriptu skillu přes symlink vyžaduje jeho SKILL.md."""
        link_skill_dirs(self.project)
        (self.project / "skills" / "edit-skill" / "run.sh").write_text("x", encoding="utf-8")
        session = Session(self.project)
        self.assert_denied(session.edit(".claude/skills/edit-skill/run.sh", post=False))
        session.read(".agents/skills/edit-skill/SKILL.md")
        self.assert_allowed(session.edit(".claude/skills/edit-skill/run.sh", post=False))

    def test_native_skill_tool_counts(self) -> None:
        """Úspěšné nativní načtení nástrojem Skill odemkne akci."""
        session = Session(self.project)
        session.skill("edit-skill")
        self.assert_allowed(session.edit("conf/a.conf"))

    def test_native_skill_does_not_unlock_other_skill(self) -> None:
        """Načtení skillu A neodemkne akci, která vyžaduje skill B."""
        session = Session(self.project)
        session.skill("foreign-skill")
        self.assert_denied(session.edit("conf/a.conf", post=False))
        other = Session(self.project, "s2")
        other.skill("edit-skill")
        repo = foreign_repo(self.tmp, "upstream")
        pre, _ = other.bash(f"git -C {repo} commit --allow-empty -qm x", run=False)
        self.assert_denied(pre)

    def test_native_skill_failure_or_unknown_does_not_count(self) -> None:
        """Neúspěšné volání, neznámý název ani PreToolUse skill neodemknou."""
        session = Session(self.project)
        session.skill("edit-skill", event="PreToolUse")
        session.skill("edit-skill", event="PostToolUseFailure")
        session.skill("neexistuje")
        session.skill("anthropic-skills:edit-skill")
        session.skill("edit-skill", success=False)
        self.assert_denied(session.edit("conf/a.conf", post=False))

    def test_other_file_in_skill_dir_does_not_count(self) -> None:
        """Přečtení jiného souboru ze složky skillu není načtení skillu."""
        link_skill_dirs(self.project)
        refs = self.project / "skills" / "edit-skill" / "references"
        refs.mkdir()
        (refs / "x.md").write_text("x", encoding="utf-8")
        session = Session(self.project)
        session.read("skills/edit-skill/references/x.md")
        session.read(".claude/skills/edit-skill/references/x.md")
        session.bash("cat skills/edit-skill/references/x.md >/dev/null")
        self.assert_denied(session.edit("conf/a.conf", post=False))

    def test_compaction_resets_native_skill(self) -> None:
        """Zhuštění kontextu vynuluje i skill načtený nástrojem Skill."""
        session = Session(self.project)
        session.skill("edit-skill")
        session.send("SessionStart", source="compact")
        self.assert_denied(session.edit("conf/a.conf", post=False))


class RequiresTest(GuardCase):
    """Skill s povinnými soubory (`requires`)."""

    def setUp(self) -> None:
        super().setUp()
        home = self.tmp / "home"
        set_env(self, HOME=str(home))
        home.mkdir()
        self.home_file = home / "kb-home.md"
        self.home_file.write_text("x", encoding="utf-8")
        (self.project / "kb").mkdir()
        (self.project / "kb" / "pravidla.md").write_text("x", encoding="utf-8")
        (self.project / "web").mkdir()
        (self.project / "web" / "i.html").write_text("x", encoding="utf-8")
        (self.project / "skills" / "req-skill").mkdir()
        (self.project / "skills" / "req-skill" / "SKILL.md").write_text(
            SKILL_REQUIRES, encoding="utf-8"
        )

    def test_requires_needs_skill_and_files(self) -> None:
        """Akce projde až po načtení skillu i všech povinných souborů."""
        session = Session(self.project)
        session.skill("req-skill")
        out = session.edit("web/i.html", post=False)
        self.assert_denied(out)
        self.assertIn("kb/pravidla.md", reason(out))
        self.assertIn("~/kb-home.md", reason(out))
        self.assertNotIn("skills/req-skill/SKILL.md", reason(out))
        session.read("kb/pravidla.md")
        self.assert_denied(session.edit("web/i.html", post=False))
        session.read(self.home_file)
        self.assert_allowed(session.edit("web/i.html", post=False))

    def test_requires_via_symlink_and_cat(self) -> None:
        """Povinný soubor se uzná i přes symlink a přes `cat` v shellu."""
        (self.project / "odkaz").symlink_to("kb")
        session = Session(self.project)
        session.read("skills/req-skill/SKILL.md")
        session.read("odkaz/pravidla.md")
        session.bash("cat ~/kb-home.md >/dev/null")
        self.assert_allowed(session.edit("web/i.html", post=False))

    def test_requires_reset_by_compaction(self) -> None:
        """Po zhuštění kontextu je potřeba povinné soubory přečíst znovu."""
        session = Session(self.project)
        session.read("skills/req-skill/SKILL.md")
        session.read("kb/pravidla.md")
        session.read(self.home_file)
        session.send("SessionStart", source="compact")
        session.read("skills/req-skill/SKILL.md")
        self.assert_denied(session.edit("web/i.html", post=False))

    def test_requires_missing_file_is_config_error(self) -> None:
        """Neexistující povinný soubor je chyba konfigurace (strážce akci propustí a ohlásí)."""
        (self.project / "kb" / "pravidla.md").unlink()
        out = Session(self.project).edit("web/i.html", post=False)
        self.assertIn("requires kb/pravidla.md neexistuje", out["systemMessage"])


class IsolateTest(GuardCase):
    """Náročné příkazy jen přes obal (`isolate`)."""

    def test_isolate_requires_wrapper(self) -> None:
        """Náročný příkaz projde jen přes obal; zmínka v argumentu nevadí."""
        (self.project / "skills" / "isolate-skill").mkdir()
        (self.project / "skills" / "isolate-skill" / "SKILL.md").write_text(
            SKILL_ISOLATE, encoding="utf-8"
        )
        session = Session(self.project)
        pre, _ = session.bash("heavy big.svg", run=False)
        self.assert_denied(pre)
        self.assertIn("wrap.sh", reason(pre))
        pre, _ = session.bash("cd x && heavy big.svg", run=False)
        self.assert_denied(pre)
        pre, _ = session.bash("./wrap.sh -- heavy big.svg", run=False)
        self.assert_allowed(pre)
        pre, _ = session.bash("grep heavy notes.txt", run=False)
        self.assert_allowed(pre)


class FrontmatterTest(unittest.TestCase):
    """Chyby konfigurace ve frontmatteru."""

    def test_top_level_guard_is_rejected(self) -> None:
        """Blok guard na nejvyšší úrovni frontmatteru je chyba (patří pod metadata)."""
        text = "---\nname: x\ndescription: x\nguard: {}\n---\n"
        with self.assertRaisesRegex(guard.GuardConfigError, "patří pod metadata"):
            guard.parse_frontmatter(text, "x")

    def test_invalid_yaml_frontmatter_is_rejected(self) -> None:
        """Frontmatter musí být platný YAML (popis s `: ` v uvozovkách)."""
        text = "---\nname: x\ndescription: a: b\nmetadata:\n  guard: {}\n---\n"
        with self.assertRaisesRegex(guard.GuardConfigError, "platný YAML"):
            guard.parse_frontmatter(text, "x")

    def test_isolate_needs_commands_and_wrapper(self) -> None:
        """Neúplné pravidlo isolate je chyba konfigurace."""
        with self.assertRaises(guard.GuardConfigError):
            guard.skill_from_frontmatter("x", {"guard": {"isolate": {"commands": ["a"]}}}, "x")


if __name__ == "__main__":
    unittest.main()
