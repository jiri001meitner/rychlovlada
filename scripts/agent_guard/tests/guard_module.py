"""Načte `guard.py` jako modul pro testy (není to balíček)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "guard", Path(__file__).resolve().parents[1] / "guard.py")
assert _SPEC is not None and _SPEC.loader is not None
guard = importlib.util.module_from_spec(_SPEC)
sys.modules["guard"] = guard  # dataclasses hledají modul v sys.modules
_SPEC.loader.exec_module(guard)

# Kořen repozitáře, ve kterém strážce leží (scripts/agent_guard/tests/…).
REPO = Path(__file__).resolve().parents[3]
