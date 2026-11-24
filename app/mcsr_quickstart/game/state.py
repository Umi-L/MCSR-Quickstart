"""Typed model of the game state reported by the State Output mod (``wpstateout.txt``).

Known file contents:
    waiting | title | wall
    generating,<pct> | previewing,<pct>
    inworld,unpaused | inworld,paused | inworld,gamescreenopen
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class WorldSub(Enum):
    UNPAUSED = "unpaused"
    PAUSED = "paused"
    GAME_SCREEN_OPEN = "gamescreenopen"


@dataclass(frozen=True, slots=True)
class Title:
    pass


@dataclass(frozen=True, slots=True)
class Waiting:
    pass


@dataclass(frozen=True, slots=True)
class Wall:
    pass


@dataclass(frozen=True, slots=True)
class Generating:
    percent: int


@dataclass(frozen=True, slots=True)
class Previewing:
    percent: int


@dataclass(frozen=True, slots=True)
class InWorld:
    sub: WorldSub


@dataclass(frozen=True, slots=True)
class Unknown:
    raw: str


@dataclass(frozen=True, slots=True)
class NotRunning:
    """No instance found, or no state file present."""


GameState = Title | Waiting | Wall | Generating | Previewing | InWorld | Unknown | NotRunning


def _percent(value: str) -> int:
    try:
        return max(0, min(100, int(value)))
    except ValueError:
        return 0


def parse_state(raw: str) -> GameState:
    text = raw.strip().lower()
    head, _, tail = text.partition(",")
    match head:
        case "title":
            return Title()
        case "waiting":
            return Waiting()
        case "wall":
            return Wall()
        case "generating":
            return Generating(_percent(tail))
        case "previewing":
            return Previewing(_percent(tail))
        case "inworld":
            try:
                return InWorld(WorldSub(tail))
            except ValueError:
                return Unknown(raw.strip())
        case _:
            return Unknown(raw.strip())


_WORLD_LABELS: dict[WorldSub, str] = {
    WorldSub.UNPAUSED: "In world",
    WorldSub.PAUSED: "Paused",
    WorldSub.GAME_SCREEN_OPEN: "In world (menu open)",
}


def describe(state: GameState) -> str:
    """Short human-readable label for the UI."""
    match state:
        case Title():
            return "Title screen"
        case Waiting():
            return "Loading…"
        case Wall():
            return "Wall"
        case Generating(percent=p):
            return f"Generating {p}%"
        case Previewing(percent=p):
            return f"Previewing {p}%"
        case InWorld(sub=sub):
            return _WORLD_LABELS[sub]
        case Unknown(raw=r):
            return f"Unknown ({r})"
        case NotRunning():
            return "Not detected"
