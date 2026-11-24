"""Model: the single immutable application state."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

from ..domain.seed import SeedRequest
from ..domain.sites import SiteInfo
from ..game.state import GameState, NotRunning
from ..infra.config import Settings

HISTORY_LIMIT = 50


class RunPhase(Enum):
    IDLE = "idle"
    RUNNING = "running"
    DONE = "done"
    ABORTED = "aborted"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class RunStatus:
    phase: RunPhase = RunPhase.IDLE
    message: str = ""

    @property
    def busy(self) -> bool:
        return self.phase is RunPhase.RUNNING


@dataclass(frozen=True, slots=True)
class ServerStatus:
    listening: bool = False
    port: int = 0
    error: str | None = None


@dataclass(frozen=True, slots=True)
class MinecraftInfo:
    title: str
    pid: int
    instance_dir: Path | None


@dataclass(frozen=True, slots=True)
class HistoryEntry:
    request: SeedRequest
    received_at: datetime


@dataclass(frozen=True, slots=True)
class AppState:
    settings: Settings
    sites: tuple[SiteInfo, ...] = ()
    server: ServerStatus = field(default_factory=ServerStatus)
    minecraft: MinecraftInfo | None = None
    game: GameState = field(default_factory=NotRunning)
    run: RunStatus = field(default_factory=RunStatus)
    current: SeedRequest | None = None
    history: tuple[HistoryEntry, ...] = ()
