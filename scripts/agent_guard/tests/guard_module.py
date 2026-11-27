"""Načte `guard.py` jako modul pro testy (není to balíček) a sdílené pomůcky."""

from __future__ import annotations

import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest import mock


def load_module(name: str, path: Path) -> ModuleType:
    """Načte skript jako modul a zaregistruje ho v `sys.modules`."""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"{path} nejde načíst jako modul")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses hledají modul v sys.modules
    spec.loader.exec_module(module)
    return module


guard = load_module("guard", Path(__file__).resolve().parents[1] / "guard.py")

# Kořen repozitáře, ve kterém strážce leží (scripts/agent_guard/tests/…).
REPO = Path(__file__).resolve().parents[3]


def temp_dir(test: unittest.TestCase) -> Path:
    """Soukromý dočasný adresář, který zanikne s koncem testu."""
    path = Path(tempfile.mkdtemp(prefix="agent-guard-test-")).resolve()
    test.addCleanup(shutil.rmtree, path, ignore_errors=True)
    return path


def set_env(test: unittest.TestCase, **values: str) -> None:
    """Nastaví proměnné prostředí jen po dobu testu."""
    test.enterContext(mock.patch.dict(os.environ, values))


def isolate_git_env(test: unittest.TestCase) -> None:
    """Po dobu testu odstraní proměnné `GIT_*` z prostředí.

    Git je předává hookům (`GIT_INDEX_FILE`, `GIT_DIR`…). Testy spuštěné
    z pre-commit by s nimi v dočasných repozitářích pracovaly s indexem
    nadřazeného repozitáře.
    """
    test.enterContext(mock.patch.dict(os.environ))
    for name in [n for n in os.environ if n.startswith("GIT_")]:
        del os.environ[name]


def git(cwd: Path, *args: str) -> None:
    """Spustí git v adresáři s pevnou identitou autora; selhání je chyba testu."""
    result = guard.run_tool(["git", "-c", "user.name=T", "-c", "user.email=t@e", *args], cwd)
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {result.stderr.strip()}")
