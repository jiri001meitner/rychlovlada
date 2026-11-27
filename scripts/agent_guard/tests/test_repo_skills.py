"""Obecné testy skillů repozitáře, ve kterém strážce leží.

Soubor je shodný ve všech repozitářích se strážcem (kanonická verze je
v linuxadm). Spouštěče konkrétních skillů patří do `test_repo_triggers.py`.
"""
from __future__ import annotations

import pytest
import yaml
from guard_module import REPO, guard


def test_repo_skills_load() -> None:
    """Každý skill repozitáře má platný blok guard a shodné jméno."""
    names = {s.name for s in guard.load_skills(REPO)}
    expected = {p.parent.name for p in REPO.glob("skills/*/SKILL.md")}
    assert names == expected


@pytest.mark.parametrize("tool_dir", [".claude/skills", ".agents/skills"])
def test_repo_skill_symlinks(tool_dir: str) -> None:
    """Nativní adresáře skillů jsou symlinky na skills/."""
    link = REPO / tool_dir
    assert link.is_symlink() and link.resolve() == (REPO / "skills").resolve()


def test_repo_frontmatter_follows_spec() -> None:
    """Frontmatter skillů je platný YAML jen s poli specifikace Agent Skills
    a s limity délky, které kontroluje validátor skills-ref."""
    for skill_md in REPO.glob("skills/*/SKILL.md"):
        text = skill_md.read_text(encoding="utf-8")
        data = yaml.safe_load(text[4:text.find("\n---", 4)])
        assert set(data) <= guard.FRONTMATTER_FIELDS, skill_md
        assert "guard" in data["metadata"], skill_md
        assert len(data["name"]) <= 64 and len(data["description"]) <= 1024, skill_md


def test_claude_hooks_call_guard() -> None:
    """Hooky Claude Code volají strážce u všech událostí, které zpracovává."""
    settings = REPO / ".claude" / "settings.json"
    text = settings.read_text(encoding="utf-8")
    hooks = yaml.safe_load(text)["hooks"]
    for event in ("PreToolUse", "PostToolUse", "PostToolUseFailure", "SessionStart", "Stop"):
        commands = [h["command"] for entry in hooks[event] for h in entry["hooks"]]
        assert any("agent_guard/guard.py" in c for c in commands), event
    post = [e.get("matcher", "") for e in hooks["PostToolUse"]
            if any("agent_guard/guard.py" in h["command"] for h in e["hooks"])]
    assert all(tool in post[0].split("|") for tool in ("Read", "Skill", "Bash", "Edit"))
