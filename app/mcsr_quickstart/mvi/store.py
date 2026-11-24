"""Store: owns the state, runs the reducer on the Qt thread, and publishes new states."""

from __future__ import annotations

import logging
from collections.abc import Callable

from PySide6.QtCore import QObject, Qt, Signal

from .intents import Intent
from .reducer import Effect, reduce
from .state import AppState

log = logging.getLogger(__name__)

EffectHandler = Callable[[Effect], None]


class Store(QObject):
    state_changed = Signal(object)  # AppState
    _incoming = Signal(object)  # Intent, possibly emitted from worker threads

    def __init__(self, initial: AppState) -> None:
        super().__init__()
        self._state = initial
        self._effect_handler: EffectHandler | None = None
        # Queued connection: intents from any thread are reduced on the Qt thread, in order.
        self._incoming.connect(self._handle, Qt.ConnectionType.QueuedConnection)

    @property
    def state(self) -> AppState:
        return self._state

    def set_effect_handler(self, handler: EffectHandler) -> None:
        self._effect_handler = handler

    def dispatch(self, intent: Intent) -> None:
        """Thread-safe."""
        self._incoming.emit(intent)

    def _handle(self, intent: Intent) -> None:
        log.debug("intent %s", type(intent).__name__)
        new_state, effects = reduce(self._state, intent)
        if new_state != self._state:
            self._state = new_state
            self.state_changed.emit(new_state)
        if self._effect_handler is not None:
            for effect in effects:
                try:
                    self._effect_handler(effect)
                except Exception:
                    log.exception("effect %s failed", type(effect).__name__)
