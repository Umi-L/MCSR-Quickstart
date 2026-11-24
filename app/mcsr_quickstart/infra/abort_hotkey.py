"""Global abort key so a runaway key sequence can always be stopped."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

log = logging.getLogger(__name__)


class AbortHotkey:
    def __init__(self, key_name: str, on_abort: Callable[[], None]) -> None:
        self._key_name = key_name.lower().strip()
        self._on_abort = on_abort
        self._listener: Any = None

    def start(self) -> None:
        from pynput import keyboard

        target = getattr(keyboard.Key, self._key_name, None)
        if target is None and len(self._key_name) == 1:
            target = keyboard.KeyCode.from_char(self._key_name)
        if target is None:
            log.error("Unknown abort key %r; abort hotkey disabled", self._key_name)
            return

        def on_press(key: object) -> None:
            if key == target:
                self._on_abort()

        self._listener = keyboard.Listener(on_press=on_press)
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
