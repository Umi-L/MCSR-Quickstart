"""The only hardcoded key inputs in the app.

Everything here is keyboard-only. Adjust the Tab counts below if your MCSR Ranked
client's menus differ — these are the *only* values that should need calibrating.

Menu navigation notes (1.16.1): no widget is focused when a screen opens, so ``Tab``
focuses the first widget and ``Shift+Tab`` focuses the last. ``Enter`` activates the
focused widget.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..domain.seed import SeedField


class Key(Enum):
    ESCAPE = "escape"
    TAB = "tab"
    ENTER = "enter"
    SPACE = "space"
    BACKSPACE = "backspace"
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    A = "a"


@dataclass(frozen=True, slots=True)
class Press:
    key: Key
    times: int = 1
    shift: bool = False
    ctrl: bool = False


@dataclass(frozen=True, slots=True)
class Type:
    """Type one of the seeds from the requested seed set."""

    field: SeedField


@dataclass(frozen=True, slots=True)
class Wait:
    """Pause for a screen transition. ``ms=None`` uses the configurable menu wait."""

    ms: int | None = None


Step = Press | Type | Wait

# Clear the focused text field before typing into it.
_CLEAR_FIELD: tuple[Step, ...] = (Press(Key.A, ctrl=True), Press(Key.BACKSPACE))

# --- In world -> title screen -------------------------------------------------------

# Close any open screen (inventory, chat, ...) -> back to the unpaused game.
CLOSE_SCREEN: tuple[Step, ...] = (Press(Key.ESCAPE),)

# Unpaused game -> pause menu.
OPEN_PAUSE_MENU: tuple[Step, ...] = (Press(Key.ESCAPE),)

# Pause menu -> "Save and Quit to Title". It is the last button, so Shift+Tab reaches it.
SAVE_AND_QUIT: tuple[Step, ...] = (
    Press(Key.TAB, shift=True),
    Press(Key.ENTER),
)

# --- Title screen -> new world ------------------------------------------------------

CREATE_WORLD: tuple[Step, ...] = (
    # Title screen: first button is "Singleplayer".
    Press(Key.TAB),
    Press(Key.ENTER),
    Wait(),
    # Select World screen: search box, world list, Play Selected, Create New World.
    Press(Key.TAB, times=3),
    Press(Key.ENTER),
    # advanced seed
    Press(Key.TAB, times=9),
    Press(Key.ENTER),
    Press(Key.TAB, times=4),
    *_CLEAR_FIELD,
    Type(SeedField.OVERWORLD), # OW
    Press(Key.TAB),
    *_CLEAR_FIELD,
    Type(SeedField.NETHER), # Nether
    Press(Key.TAB),
    *_CLEAR_FIELD,
    Type(SeedField.OVERWORLD), # End
    Press(Key.TAB),
    *_CLEAR_FIELD,
    Type(SeedField.OVERWORLD), # RNG
    Press(Key.TAB),
    Press(Key.ENTER), # Done
    Press(Key.TAB, times=3), # Difficulty
    Press(Key.ENTER, times=3), # Easy
    Press(Key.TAB, times=3), # Game Rules
    Press(Key.ENTER),
    Press(Key.TAB, times=44), # portal mechanics
    Press(Key.ENTER),
    Press(Key.TAB, times=7),
    Press(Key.ENTER),
    Press(Key.TAB),
    Press(Key.ENTER),
    Press(Key.TAB, times=4),
    Press(Key.ENTER),
    Press(Key.TAB, times=7),
    Press(Key.ENTER)
)
