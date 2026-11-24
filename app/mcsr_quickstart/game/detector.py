"""Reading and watching ``wpstateout.txt``."""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from .state import GameState, NotRunning, parse_state

STATE_FILE_NAME = "wpstateout.txt"


class StateSource(Protocol):
    def read(self) -> GameState: ...


class StateFile:
    """Reads the State Output file for one instance directory."""

    def __init__(self, instance_dir: Path) -> None:
        self.path = instance_dir / STATE_FILE_NAME

    def read(self) -> GameState:
        # The mod rewrites the file in place, so a read can briefly see it empty.
        for _ in range(3):
            try:
                text = self.path.read_text(encoding="utf-8", errors="replace")
            except FileNotFoundError:
                return NotRunning()
            except OSError:
                continue
            if text.strip():
                return parse_state(text)
        return NotRunning()


class StateWatcher:
    """Polls the state file of whatever instance ``dir_provider`` returns and reports changes."""

    def __init__(
        self,
        dir_provider: Callable[[], Path | None],
        on_change: Callable[[GameState], None],
        interval_s: float = 0.1,
    ) -> None:
        self._dir_provider = dir_provider
        self._on_change = on_change
        self._interval = interval_s
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="state-watcher", daemon=True)
        self._last: GameState | None = None

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        while not self._stop.is_set():
            directory = self._dir_provider()
            state: GameState = StateFile(directory).read() if directory else NotRunning()
            if state != self._last:
                self._last = state
                self._on_change(state)
            self._stop.wait(self._interval)
