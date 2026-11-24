"""Locate the running Minecraft instance directory (where ``wpstateout.txt`` lives)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import psutil

from .detector import STATE_FILE_NAME


@dataclass(frozen=True, slots=True)
class Instance:
    pid: int
    directory: Path


def _game_dir_from_cmdline(cmdline: list[str]) -> Path | None:
    for i, arg in enumerate(cmdline):
        if arg == "--gameDir" and i + 1 < len(cmdline):
            return Path(cmdline[i + 1])
        if arg.startswith("--gameDir="):
            return Path(arg.split("=", 1)[1])
    return None


def instance_dir_for_pid(pid: int) -> Path | None:
    """Best guess at the game directory of a Java process.

    MultiMC/Prism launch Minecraft with the instance's ``.minecraft`` folder as the working
    directory; other launchers pass ``--gameDir``. Prefer whichever has a state file.
    """
    try:
        proc = psutil.Process(pid)
        candidates = [_game_dir_from_cmdline(proc.cmdline()), Path(proc.cwd())]
    except (psutil.Error, OSError):
        return None
    existing = [c for c in candidates if c is not None and c.is_dir()]
    for candidate in existing:
        if (candidate / STATE_FILE_NAME).is_file():
            return candidate
    return existing[0] if existing else None


def scan_java_instances() -> list[Instance]:
    """Fallback when no window matches: every Java process whose game dir has a state file."""
    found: list[Instance] = []
    for proc in psutil.process_iter(["pid", "name"]):
        name = (proc.info.get("name") or "").lower()
        if "java" not in name:
            continue
        directory = instance_dir_for_pid(int(proc.info["pid"]))
        if directory and (directory / STATE_FILE_NAME).is_file():
            found.append(Instance(pid=int(proc.info["pid"]), directory=directory))
    return found
