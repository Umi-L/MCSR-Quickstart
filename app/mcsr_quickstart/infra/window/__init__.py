"""Pick the window backend for the current platform."""

from __future__ import annotations

import sys

from .base import NullFocuser, WindowFocuser, WindowRef

__all__ = ["WindowFocuser", "WindowRef", "create_focuser"]


def create_focuser() -> WindowFocuser:
    if sys.platform == "win32":
        from .windows import Win32Focuser

        return Win32Focuser()
    elif sys.platform == "darwin":
        from .macos import MacFocuser

        return MacFocuser()
    else:
        from .linux import XdotoolFocuser

        return XdotoolFocuser() if XdotoolFocuser.available() else NullFocuser()
