"""Linux (X11) backend using xdotool. Wayland sessions are not supported."""

from __future__ import annotations

import re
import shutil
import subprocess

from .base import WindowRef


def _run(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["xdotool", *args], capture_output=True, text=True, timeout=5, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else None


class XdotoolFocuser:
    @staticmethod
    def available() -> bool:
        return shutil.which("xdotool") is not None

    def find(self, title_pattern: re.Pattern[str]) -> WindowRef | None:
        ids = _run("search", "--onlyvisible", "--name", ".")
        if not ids:
            return None
        for wid in ids.split():
            title = (_run("getwindowname", wid) or "").strip()
            if title and title_pattern.search(title):
                pid_text = (_run("getwindowpid", wid) or "").strip()
                pid = int(pid_text) if pid_text.isdigit() else 0
                return WindowRef(pid=pid, title=title, handle=wid)
        return None

    def focus(self, window: WindowRef) -> bool:
        return _run("windowactivate", "--sync", window.handle) is not None
