"""Shared helpers for the dev/build scripts (standard library only)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
EXT = ROOT / "extension"
RELEASE = ROOT / "release"


def venv_python() -> Path:
    sub = "Scripts/python.exe" if os.name == "nt" else "bin/python"
    return APP / ".venv" / sub


def npm() -> str:
    exe = shutil.which("npm")
    if exe is None:
        sys.exit("npm not found on PATH (Node.js 18+ is required for the extension)")
    return exe


def run(cmd: list[str | Path], cwd: Path) -> None:
    printable = " ".join(str(c) for c in cmd)
    print(f"\n$ ({cwd.relative_to(ROOT) or '.'}) {printable}", flush=True)
    result = subprocess.run([str(c) for c in cmd], cwd=cwd, check=False)
    if result.returncode != 0:
        sys.exit(f"command failed ({result.returncode}): {printable}")


def ensure_venv() -> Path:
    """Create app/.venv and install the app with dev extras if needed."""
    python = venv_python()
    if not python.exists():
        run([sys.executable, "-m", "venv", APP / ".venv"], ROOT)
        run([python, "-m", "pip", "install", "--upgrade", "pip"], APP)
        run([python, "-m", "pip", "install", "-e", ".[dev]"], APP)
    return python


def ensure_node_modules() -> None:
    if not (EXT / "node_modules").exists():
        run([npm(), "install"], EXT)
