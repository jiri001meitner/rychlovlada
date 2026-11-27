"""Obecné testy skillů repozitáře, ve kterém strážce leží.

Soubor je shodný ve všech repozitářích se strážcem (kanonická verze je
v linuxadm). Spouštěče konkrétních skillů patří do `test_repo_triggers.py`.
"""

from __future__ import annotations

import json
import unittest

import yaml
from guard_module import REPO, guard

# Limity délky, které kontroluje validátor skills-ref.
NAME_MAX = 64
DESCRIPTION_MAX = 1024
HOOK_EVENTS = ("PreToolUse", "PostToolUse", "PostToolUseFailure", "SessionStart", "Stop")
GUARD_SCRIPT = "agent_guard/guard.py"


class RepoSkillsTest(unittest.TestCase):
    """Skilly, symlinky a hooky repozitáře."""

    def test_repo_skills_load(self) -> None:
        """Každý skill repozitáře má platný blok guard a shodné jméno."""
        names = {s.name for s in guard.load_skills(REPO)}
        expected = {p.parent.name for p in REPO.glob("skills/*/SKILL.md")}
        self.assertEqual(names, expected)

    def test_repo_skill_symlinks(self) -> None:
        """Nativní adresáře skillů jsou symlinky na skills/."""
        for tool_dir in (".claude/skills", ".agents/skills"):
            with self.subTest(tool_dir=tool_dir):
                link = REPO / tool_dir
                self.assertTrue(link.is_symlink(), link)
                self.assertEqual(link.resolve(), (REPO / "skills").resolve())

    def test_repo_frontmatter_follows_spec(self) -> None:
        """Frontmatter skillů je platný YAML jen s poli specifikace Agent Skills
        a s limity délky, které kontroluje validátor skills-ref."""
        for skill_md in REPO.glob("skills/*/SKILL.md"):
            with self.subTest(skill=str(skill_md)):
                text = skill_md.read_text(encoding="utf-8")
                data = yaml.safe_load(text[4 : text.find("\n---", 4)])
                self.assertLessEqual(set(data), guard.FRONTMATTER_FIELDS)
                self.assertIn("guard", data["metadata"])
                self.assertLessEqual(len(data["name"]), NAME_MAX)
                self.assertLessEqual(len(data["description"]), DESCRIPTION_MAX)

    def test_claude_hooks_call_guard(self) -> None:
        """Hooky Claude Code volají strážce u všech událostí, které zpracovává."""
        settings = REPO / ".claude" / "settings.json"
        hooks = json.loads(settings.read_text(encoding="utf-8"))["hooks"]
        for event in HOOK_EVENTS:
            with self.subTest(event=event):
                commands = [h["command"] for entry in hooks[event] for h in entry["hooks"]]
                self.assertTrue(any(GUARD_SCRIPT in c for c in commands), commands)
        post = [
            e.get("matcher", "")
            for e in hooks["PostToolUse"]
            if any(GUARD_SCRIPT in h["command"] for h in e["hooks"])
        ]
        self.assertLessEqual({"Read", "Skill", "Bash", "Edit"}, set(post[0].split("|")))


if __name__ == "__main__":
    unittest.main()
