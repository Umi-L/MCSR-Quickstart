from __future__ import annotations

import threading

import pytest

from mcsr_quickstart.domain.seed import SeedSet
from mcsr_quickstart.game.runner import RunAborted, RunError, Runner, RunTiming
from mcsr_quickstart.game.sequences import Key
from mcsr_quickstart.game.state import GameState, Generating, InWorld, Title, Waiting, WorldSub

SEEDS = SeedSet(overworld="123", nether="456", rng="789")
FAST = RunTiming(key_delay_ms=0, focus_settle_ms=0, step_timeout_s=0.3, load_timeout_s=0.3,
                 poll_s=0.001)


class FakeGame:
    """Simulates the game's state machine reacting to keys."""

    def __init__(self, state: GameState, *, responsive: bool = True) -> None:
        self.state = state
        self.responsive = responsive
        self.log: list[str] = []

    # StateSource
    def read(self) -> GameState:
        return self.state

    # KeySender
    def press(self, key: Key, *, shift: bool = False, ctrl: bool = False) -> None:
        self.log.append(("shift+" if shift else "") + ("ctrl+" if ctrl else "") + key.value)
        if not self.responsive:
            return
        match self.state, key:
            case InWorld(sub=WorldSub.GAME_SCREEN_OPEN), Key.ESCAPE:
                self.state = InWorld(WorldSub.UNPAUSED)
            case InWorld(sub=WorldSub.UNPAUSED), Key.ESCAPE:
                self.state = InWorld(WorldSub.PAUSED)
            case InWorld(sub=WorldSub.PAUSED), Key.ENTER:
                self.state = Title()
            case Title(), Key.ENTER if sum(e.startswith("type:") for e in self.log) >= 2:
                # Final "Create New World" press after both seeds were typed.
                self.state = Generating(0)
            case _:
                pass

    def type_text(self, text: str) -> None:
        self.log.append(f"type:{text}")


def make_runner(game: FakeGame, cancel: threading.Event | None = None) -> Runner:
    return Runner(
        keys=game,
        states=game,
        focus=lambda: True,
        cancel=cancel or threading.Event(),
        on_progress=lambda _msg: None,
        timing=FAST,
    )


def test_from_open_screen_to_new_world() -> None:
    game = FakeGame(InWorld(WorldSub.GAME_SCREEN_OPEN))
    make_runner(game).run(SEEDS)
    assert game.log[:2] == ["escape", "escape"]
    assert "type:123" in game.log and "type:456" in game.log
    assert isinstance(game.state, Generating)


def test_from_title_types_seeds_in_order() -> None:
    game = FakeGame(Title())
    make_runner(game).run(SEEDS)
    typed = [entry for entry in game.log if entry.startswith("type:")]
    assert typed == ["type:123", "type:456"]


def test_unresponsive_game_times_out() -> None:
    game = FakeGame(InWorld(WorldSub.UNPAUSED), responsive=False)
    with pytest.raises(RunError, match="No reaction"):
        make_runner(game).run(SEEDS)


def test_stuck_loading_times_out() -> None:
    game = FakeGame(Waiting())
    with pytest.raises(RunError, match="stuck"):
        make_runner(game).run(SEEDS)


def test_abort() -> None:
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(RunAborted):
        make_runner(FakeGame(Title()), cancel).run(SEEDS)


def test_focus_failure() -> None:
    game = FakeGame(Title())
    runner = Runner(game, game, lambda: False, threading.Event(), lambda _m: None, FAST)
    with pytest.raises(RunError, match="focus"):
        runner.run(SEEDS)
