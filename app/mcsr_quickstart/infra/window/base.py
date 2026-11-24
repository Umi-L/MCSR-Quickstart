"""Platform-neutral window finding/focusing interface."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class WindowRef:
    pid: int
    title: str
    handle: str  # platform-specific id (HWND, X11 window id, ...)


class WindowFocuser(Protocol):
    def find(self, title_pattern: re.Pattern[str]) -> WindowRef | None:
        """Return the first visible top-level window whose title matches."""
        ...

    def focus(self, window: WindowRef) -> bool:
        """Bring the window to the foreground. Returns False if it could not be focused."""
        ...


class NullFocuser:
    """Fallback when the platform is unsupported: never finds anything."""

    def find(self, title_pattern: re.Pattern[str]) -> WindowRef | None:
        return None

    def focus(self, window: WindowRef) -> bool:
        return False
