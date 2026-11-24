"""Pure reducer: (state, intent) -> (new state, effects to perform)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import assert_never

from ..domain.seed import SeedRequest
from ..infra.config import Settings
from .intents import (
    AbortRequested,
    ClearHistory,
    GameStateChanged,
    Intent,
    MinecraftDetected,
    RunAborted,
    RunFailed,
    RunFinished,
    RunProgress,
    RunRequested,
    SeedReceived,
    ServerStatusChanged,
    SettingsChanged,
)
from .state import HISTORY_LIMIT, AppState, HistoryEntry, RunPhase, RunStatus, ServerStatus

# -- Effects ------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class StartRun:
    request: SeedRequest
    settings: Settings


@dataclass(frozen=True, slots=True)
class CancelRun:
    pass


@dataclass(frozen=True, slots=True)
class SaveSettings:
    settings: Settings


@dataclass(frozen=True, slots=True)
class RestartServer:
    port: int


@dataclass(frozen=True, slots=True)
class RestartHotkey:
    key: str


@dataclass(frozen=True, slots=True)
class Notify:
    title: str
    message: str


Effect = StartRun | CancelRun | SaveSettings | RestartServer | RestartHotkey | Notify


# -- Reducer ------------------------------------------------------------------------------


def _start(state: AppState, request: SeedRequest) -> tuple[AppState, list[Effect]]:
    if state.run.busy:
        return state, []
    new = replace(
        state, current=request, run=RunStatus(RunPhase.RUNNING, "Starting"),
    )
    return new, [StartRun(request, state.settings)]


def reduce(state: AppState, intent: Intent) -> tuple[AppState, list[Effect]]:
    match intent:
        case SeedReceived(request=request, at=at):
            entry = HistoryEntry(request, at)
            history = (entry, *state.history)[:HISTORY_LIMIT]
            received = replace(state, current=request, history=history)
            if state.settings.auto_run:
                return _start(received, request)
            return received, []

        case RunRequested(request=request):
            return _start(state, request)

        case RunProgress(message=message):
            if not state.run.busy:
                return state, []
            return replace(state, run=RunStatus(RunPhase.RUNNING, message)), []

        case RunFinished():
            return replace(state, run=RunStatus(RunPhase.DONE, "World created")), []

        case RunFailed(message=message):
            return (
                replace(state, run=RunStatus(RunPhase.ERROR, message)),
                [Notify("Quickstart failed", message)],
            )

        case RunAborted():
            return replace(state, run=RunStatus(RunPhase.ABORTED, "Aborted")), []

        case AbortRequested():
            return (state, [CancelRun()]) if state.run.busy else (state, [])

        case GameStateChanged(state=game):
            return replace(state, game=game), []

        case MinecraftDetected(info=info):
            return replace(state, minecraft=info), []

        case ServerStatusChanged(listening=listening, port=port, error=error):
            return replace(state, server=ServerStatus(listening, port, error)), []

        case SettingsChanged(settings=settings):
            effects: list[Effect] = [SaveSettings(settings)]
            if settings.port != state.settings.port:
                effects.append(RestartServer(settings.port))
            if settings.abort_key != state.settings.abort_key:
                effects.append(RestartHotkey(settings.abort_key))
            return replace(state, settings=settings), effects

        case ClearHistory():
            return replace(state, history=()), []

        case _:
            assert_never(intent)
