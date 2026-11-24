"""macOS backend using AppleScript (System Events). Requires Accessibility permission."""

from __future__ import annotations

import logging
import re
import subprocess
import time

from .base import WindowRef

log = logging.getLogger(__name__)

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

# Activating the process alone is not enough for a Java/GLFW game: the window may be
# minimized or sitting behind others, so un-minimize and raise every window too.
_FOCUS_SCRIPT = """
tell application "System Events"
    set p to first process whose unix id is {pid}
    set frontmost of p to true
    try
        repeat with w in (every window of p)
            try
                if (value of attribute "AXMinimized" of w) is true then
                    set value of attribute "AXMinimized" of w to false
                end if
            end try
            try
                perform action "AXRaise" of w
            end try
        end repeat
    end try
    return frontmost of p
end tell
"""

_ACCESSIBILITY_HINT = (
    "macOS refused the request. Grant Accessibility (and Automation > System Events) "
    "permission to the app or terminal running mcsr-quickstart, under "
    "System Settings > Privacy & Security."
)


def _osascript(script: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=5, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        log.warning("osascript failed: %s", exc)
        return False, ""
    if result.returncode != 0:
        err = result.stderr.strip()
        if "not allowed" in err or "assistive" in err or "-1743" in err or "-25211" in err:
            err = f"{err}\n{_ACCESSIBILITY_HINT}"
        log.warning("osascript error: %s", err)
        return False, ""
    return True, result.stdout


class MacFocuser:
    def find(self, title_pattern: re.Pattern[str]) -> WindowRef | None:
        _, output = _osascript(_LIST_SCRIPT)
        for line in output.splitlines():
            pid_text, _, title = line.partition("\t")
            if title and title_pattern.search(title) and pid_text.strip().isdigit():
                pid = int(pid_text.strip())
                return WindowRef(pid=pid, title=title, handle=str(pid))
        return None

    def focus(self, window: WindowRef) -> bool:
        script = _FOCUS_SCRIPT.format(pid=int(window.pid))
        # Activation can race with the window server; verify and retry once.
        for attempt in range(2):
            ok, output = _osascript(script)
            if ok and output.strip().lower() == "true":
                return True
            if attempt == 0:
                time.sleep(0.2)
        return False
