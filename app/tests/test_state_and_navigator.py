from __future__ import annotations

import pytest

from mcsr_quickstart.game import sequences
from mcsr_quickstart.game.navigator import AtTitle, Fail, SendKeys, WaitForChange, next_action
from mcsr_quickstart.game.state import (
    GameState,
    Generating,
    InWorld,
    NotRunning,
    Previewing,
    Title,
    Unknown,
    Waiting,
    Wall,
    WorldSub,
    parse_state,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("title", Title()),
        ("waiting\n", Waiting()),
        ("wall", Wall()),
        ("generating,42", Generating(42)),
        ("previewing,100", Previewing(100)),
        ("generating,abc", Generating(0)),
        ("inworld,unpaused", InWorld(WorldSub.UNPAUSED)),
        ("inworld,paused", InWorld(WorldSub.PAUSED)),
        ("inworld,gamescreenopen", InWorld(WorldSub.GAME_SCREEN_OPEN)),
        ("inworld,weird", Unknown("inworld,weird")),
        ("??", Unknown("??")),
    ],
)
def test_parse_state(raw: str, expected: GameState) -> None:
    assert parse_state(raw) == expected


def test_navigator_paths() -> None:
    assert next_action(Title()) == AtTitle()
    unpaused = next_action(InWorld(WorldSub.UNPAUSED))
    assert isinstance(unpaused, SendKeys) and unpaused.steps == sequences.OPEN_PAUSE_MENU
    paused = next_action(InWorld(WorldSub.PAUSED))
    assert isinstance(paused, SendKeys) and paused.steps == sequences.SAVE_AND_QUIT
    screen = next_action(InWorld(WorldSub.GAME_SCREEN_OPEN))
    assert isinstance(screen, SendKeys) and screen.steps == sequences.CLOSE_SCREEN
    for loading in (Generating(1), Previewing(2), Waiting()):
        assert isinstance(next_action(loading), WaitForChange)
    for bad in (Wall(), Unknown("x"), NotRunning()):
        assert isinstance(next_action(bad), Fail)
