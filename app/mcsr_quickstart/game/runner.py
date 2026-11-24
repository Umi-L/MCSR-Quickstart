"""Closed-loop runner: navigate to the title screen using live game state, then create the world."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from ..domain.seed import SeedSet
from ..infra.keyboard import KeySender
from . import sequences
from .detector import StateSource
from .navigator import AtTitle, Fail, SendKeys, WaitForChange, next_action
from .sequences import Press, Step, Type, Wait
from .state import GameState, Generating, InWorld, Previewing, Waiting, describe

log = logging.getLogger(__name__)


class RunError(Exception):
    pass


class RunAborted(Exception):
    pass


@dataclass(frozen=True, slots=True)
class RunTiming:
    key_delay_ms: int = 5
    menu_wait_ms: int = 500
    startup_delay_ms: int = 500
    focus_settle_ms: int = 300
    step_timeout_s: float = 10.0
    load_timeout_s: float = 120.0
    max_nav_steps: int = 12
    poll_s: float = 0.05


ProgressFn = Callable[[str], None]


def _changed_from(previous: GameState) -> Callable[[GameState], bool]:
    return lambda state: state != previous


class Runner:
    def __init__(
        self,
        keys: KeySender,
        states: StateSource,
        focus: Callable[[], bool],
        cancel: threading.Event,
        on_progress: ProgressFn,
        timing: RunTiming | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._keys = keys
        self._states = states
        self._focus = focus
        self._cancel = cancel
        self._progress = on_progress
        self._timing = timing or RunTiming()
        self._clock = clock

    # -- public -------------------------------------------------------------------------

    def run(self, seeds: SeedSet) -> None:
        self._check_cancel()
        self._sleep_ms(self._timing.startup_delay_ms)
        self._progress("Focusing Minecraft")
        if not self._focus():
            raise RunError("Could not focus the Minecraft window")
        self._sleep_ms(self._timing.focus_settle_ms)

        self._navigate_to_title()

        self._progress("Creating world")
        self._execute(sequences.CREATE_WORLD, seeds)
        self._wait_until(
            lambda s: isinstance(s, Generating | Previewing | Waiting | InWorld),
            self._timing.step_timeout_s * 2,
            "World creation did not start — check the key sequence in sequences.py",
        )
        self._progress("World is generating")

    # -- internals ----------------------------------------------------------------------

    def _navigate_to_title(self) -> None:
        for _ in range(self._timing.max_nav_steps):
            state = self._states.read()
            match next_action(state):
                case AtTitle():
                    return
                case Fail(reason=reason):
                    raise RunError(reason)
                case WaitForChange(description=text):
                    self._progress(text)
                    self._wait_until(
                        _changed_from(state),
                        self._timing.load_timeout_s,
                        f"Game stuck at '{describe(state)}'",
                    )
                case SendKeys(steps=steps, description=text):
                    self._progress(text)
                    self._execute(steps, None)
                    self._wait_until(
                        _changed_from(state),
                        self._timing.step_timeout_s,
                        f"No reaction to input while '{describe(state)}'",
                    )
        raise RunError("Could not reach the title screen")

    def _execute(self, steps: tuple[Step, ...], seeds: SeedSet | None) -> None:
        for step in steps:
            self._check_cancel()
            match step:
                case Press(key=key, times=times, shift=shift, ctrl=ctrl):
                    for _ in range(times):
                        self._check_cancel()
                        log.debug("press %s", key.value)
                        self._keys.press(key, shift=shift, ctrl=ctrl)
                        self._sleep_ms(self._timing.key_delay_ms)
                case Type(field=field):
                    value = seeds.get(field) if seeds else None
                    if value is None:
                        raise RunError(f"No {field.value} seed in this seed set")
                    self._keys.type_text(value)
                    self._sleep_ms(self._timing.key_delay_ms)
                case Wait(ms=ms):
                    self._sleep_ms(self._timing.menu_wait_ms if ms is None else ms)

    def _wait_until(
        self, predicate: Callable[[GameState], bool], timeout_s: float, error: str
    ) -> GameState:
        deadline = self._clock() + timeout_s
        while True:
            self._check_cancel()
            state = self._states.read()
            if predicate(state):
                return state
            if self._clock() >= deadline:
                raise RunError(error)
            self._sleep_ms(int(self._timing.poll_s * 1000))

    def _sleep_ms(self, ms: int) -> None:
        if ms > 0 and self._cancel.wait(ms / 1000):
            raise RunAborted()

    def _check_cancel(self) -> None:
        if self._cancel.is_set():
            raise RunAborted()
