"""macOS backend using AppleScript (System Events). Requires Accessibility permission."""

from __future__ import annotations

import re
import subprocess

from .base import WindowRef

_LIST_SCRIPT = """
set output to ""
tell application "System Events"
    repeat with p in (every process whose background only is false)
        try
            repeat with w in (every window of p)
                set output to output & (unix id of p) & tab & (name of w) & linefeed
            end repeat
        end try
    end repeat
end tell
return output
"""


def _osascript(script: str) -> str:
    result = subprocess.run(
        ["osascript", "-e", script], capture_output=True, text=True, timeout=5, check=False
    )
    return result.stdout if result.returncode == 0 else ""


class MacFocuser:
    def find(self, title_pattern: re.Pattern[str]) -> WindowRef | None:
        for line in _osascript(_LIST_SCRIPT).splitlines():
            pid_text, _, title = line.partition("\t")
            if title and title_pattern.search(title) and pid_text.strip().isdigit():
                pid = int(pid_text.strip())
                return WindowRef(pid=pid, title=title, handle=str(pid))
        return None

    def focus(self, window: WindowRef) -> bool:
        script = (
            'tell application "System Events" to set frontmost of '
            f"(first process whose unix id is {int(window.pid)}) to true"
        )
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, timeout=5, check=False
        )
        return result.returncode == 0
