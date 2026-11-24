"""Keeps track of the Minecraft window/instance and its live game state."""

from __future__ import annotations

import logging
import re
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..infra.window import WindowFocuser, WindowRef
from .detector import StateWatcher
from .instance import instance_dir_for_pid, scan_java_instances
from .state import GameState

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Target:
    window: WindowRef | None
    instance_dir: Path | None


class GameMonitor:
    """Polls for the Minecraft window (slowly) and its state file (quickly)."""

    def __init__(
        self,
        focuser: WindowFocuser,
        on_target: Callable[[Target | None], None],
        on_state: Callable[[GameState], None],
        window_interval_s: float = 1.5,
    ) -> None:
        self._focuser = focuser
        self._on_target = on_target
        self._interval = window_interval_s
        self._lock = threading.Lock()
        self._pattern = re.compile(r"^Minecraft")
        self._override: Path | None = None
        self._target: Target | None = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="game-monitor", daemon=True)
        self._watcher = StateWatcher(self.instance_dir, on_state)

    def configure(self, title_pattern: str, instance_override: str) -> None:
        try:
            pattern = re.compile(title_pattern)
        except re.error:
            log.warning("Invalid window title regex %r; keeping previous", title_pattern)
            pattern = self._pattern
        with self._lock:
            self._pattern = pattern
            self._override = Path(instance_override) if instance_override.strip() else None

    def start(self) -> None:
        self._thread.start()
        self._watcher.start()

    def stop(self) -> None:
        self._stop.set()
        self._watcher.stop()

    def instance_dir(self) -> Path | None:
        with self._lock:
            if self._override is not None:
                return self._override
            return self._target.instance_dir if self._target else None

    def focus(self) -> bool:
        """Re-find the window (it may have been recreated) and focus it."""
        target = self.refresh()
        if target is None or target.window is None:
            return False
        return self._focuser.focus(target.window)

    def refresh(self) -> Target | None:
        with self._lock:
            pattern = self._pattern
        window = self._focuser.find(pattern)
        target: Target | None = None
        if window is not None:
            target = Target(window, instance_dir_for_pid(window.pid) if window.pid else None)
        else:
            instances = scan_java_instances()
            if instances:
                target = Target(None, instances[0].directory)
        with self._lock:
            changed = target != self._target
            self._target = target
        if changed:
            self._on_target(target)
        return target

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.refresh()
            except Exception:
                log.exception("window scan failed")
            self._stop.wait(self._interval)
