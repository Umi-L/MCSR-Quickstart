"""Windows backend using the Win32 API through ctypes."""

from __future__ import annotations

import ctypes
import re
import sys
from ctypes import wintypes

from .base import WindowRef

assert sys.platform == "win32"

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

_EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
_SW_RESTORE = 9
_VK_MENU = 0x12
_KEYEVENTF_KEYUP = 0x0002


def _window_title(hwnd: int) -> str:
    length = _user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    _user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def _window_pid(hwnd: int) -> int:
    pid = wintypes.DWORD()
    _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return int(pid.value)


class Win32Focuser:
    def find(self, title_pattern: re.Pattern[str]) -> WindowRef | None:
        found: list[WindowRef] = []

        def callback(hwnd: int, _lparam: int) -> bool:
            if _user32.IsWindowVisible(hwnd):
                title = _window_title(hwnd)
                if title and title_pattern.search(title):
                    found.append(WindowRef(pid=_window_pid(hwnd), title=title, handle=str(hwnd)))
                    return False
            return True

        _user32.EnumWindows(_EnumWindowsProc(callback), 0)
        return found[0] if found else None

    def focus(self, window: WindowRef) -> bool:
        hwnd = int(window.handle)
        if not _user32.IsWindow(hwnd):
            return False
        if _user32.IsIconic(hwnd):
            _user32.ShowWindow(hwnd, _SW_RESTORE)

        foreground = _user32.GetForegroundWindow()
        if foreground == hwnd:
            return True

        # Windows only lets the foreground process steal focus; attach to its input
        # queue and tap Alt so SetForegroundWindow is allowed.
        current_tid = _kernel32.GetCurrentThreadId()
        fg_tid = _user32.GetWindowThreadProcessId(foreground, None)
        attached = bool(fg_tid) and fg_tid != current_tid and bool(
            _user32.AttachThreadInput(current_tid, fg_tid, True)
        )
        try:
            _user32.keybd_event(_VK_MENU, 0, 0, 0)
            _user32.keybd_event(_VK_MENU, 0, _KEYEVENTF_KEYUP, 0)
            _user32.BringWindowToTop(hwnd)
            _user32.SetForegroundWindow(hwnd)
        finally:
            if attached:
                _user32.AttachThreadInput(current_tid, fg_tid, False)
        return bool(_user32.GetForegroundWindow() == hwnd)
