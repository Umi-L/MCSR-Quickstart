"""Pure decision logic: given the current game state, what gets us closer to the title screen."""

from __future__ import annotations

from dataclasses import dataclass

from . import sequences
from .sequences import Step
from .state import (
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
)


@dataclass(frozen=True, slots=True)
class SendKeys:
    steps: tuple[Step, ...]
    description: str


@dataclass(frozen=True, slots=True)
class WaitForChange:
    description: str


@dataclass(frozen=True, slots=True)
class AtTitle:
    pass


@dataclass(frozen=True, slots=True)
class Fail:
    reason: str


NavAction = SendKeys | WaitForChange | AtTitle | Fail


_IN_WORLD_ACTIONS: dict[WorldSub, NavAction] = {
    WorldSub.GAME_SCREEN_OPEN: SendKeys(sequences.CLOSE_SCREEN, "Closing open screen"),
    WorldSub.UNPAUSED: SendKeys(sequences.OPEN_PAUSE_MENU, "Pausing"),
    WorldSub.PAUSED: SendKeys(sequences.SAVE_AND_QUIT, "Saving and quitting to title"),
}


def next_action(state: GameState) -> NavAction:
    match state:
        case Title():
            return AtTitle()
        case InWorld(sub=sub):
            return _IN_WORLD_ACTIONS[sub]
        case Generating() | Previewing() | Waiting():
            return WaitForChange("Waiting for the game to finish loading")
        case Wall():
            return Fail("Instance is on a wall screen; single-instance setups only")
        case Unknown(raw=raw):
            return Fail(f"Unrecognised game state '{raw}'")
        case NotRunning():
            return Fail("Minecraft state file not found — is the State Output mod installed?")
