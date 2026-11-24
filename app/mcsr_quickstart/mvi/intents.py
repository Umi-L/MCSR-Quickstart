"""Intents: everything that can happen, from the user, the browser, or the game."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..domain.seed import SeedRequest
from ..game.state import GameState
from ..infra.config import Settings
from .state import MinecraftInfo


@dataclass(frozen=True, slots=True)
class SeedReceived:
    request: SeedRequest
    at: datetime


@dataclass(frozen=True, slots=True)
class RunRequested:
    request: SeedRequest


@dataclass(frozen=True, slots=True)
class RunProgress:
    message: str


@dataclass(frozen=True, slots=True)
class RunFinished:
    pass


@dataclass(frozen=True, slots=True)
class RunFailed:
    message: str


@dataclass(frozen=True, slots=True)
class RunAborted:
    pass


@dataclass(frozen=True, slots=True)
class AbortRequested:
    pass


@dataclass(frozen=True, slots=True)
class GameStateChanged:
    state: GameState


@dataclass(frozen=True, slots=True)
class MinecraftDetected:
    info: MinecraftInfo | None


@dataclass(frozen=True, slots=True)
class ServerStatusChanged:
    listening: bool
    port: int
    error: str | None = None


@dataclass(frozen=True, slots=True)
class SettingsChanged:
    settings: Settings


@dataclass(frozen=True, slots=True)
class ClearHistory:
    pass


Intent = (
    SeedReceived
    | RunRequested
    | RunProgress
    | RunFinished
    | RunFailed
    | RunAborted
    | AbortRequested
    | GameStateChanged
    | MinecraftDetected
    | ServerStatusChanged
    | SettingsChanged
    | ClearHistory
)
