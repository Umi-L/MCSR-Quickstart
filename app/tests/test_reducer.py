from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from mcsr_quickstart.domain.seed import SeedRequest, SeedSet
from mcsr_quickstart.infra.config import Settings
from mcsr_quickstart.mvi.intents import (
    AbortRequested,
    RunFailed,
    RunFinished,
    RunProgress,
    RunRequested,
    SeedReceived,
    SettingsChanged,
)
from mcsr_quickstart.mvi.reducer import (
    CancelRun,
    Notify,
    RestartServer,
    SaveSettings,
    StartRun,
    reduce,
)
from mcsr_quickstart.mvi.state import AppState, RunPhase

REQ = SeedRequest("gapcheck", SeedSet("1", "2"), "https://gapcheck.gg/m/1", "Village")


def base(auto_run: bool = True) -> AppState:
    return AppState(settings=Settings(token="t", auto_run=auto_run))


def test_seed_received_auto_runs() -> None:
    state, effects = reduce(base(), SeedReceived(REQ, datetime.now()))
    assert state.current == REQ
    assert len(state.history) == 1
    assert state.run.phase is RunPhase.RUNNING
    assert effects == [StartRun(REQ, state.settings)]


def test_seed_received_without_auto_run() -> None:
    state, effects = reduce(base(auto_run=False), SeedReceived(REQ, datetime.now()))
    assert state.run.phase is RunPhase.IDLE
    assert effects == []


def test_no_double_start_while_running() -> None:
    running, _ = reduce(base(), RunRequested(REQ))
    again, effects = reduce(running, RunRequested(REQ))
    assert again is running and effects == []


def test_run_lifecycle() -> None:
    state, _ = reduce(base(), RunRequested(REQ))
    state, _ = reduce(state, RunProgress("Pausing"))
    assert state.run.message == "Pausing"
    state, effects = reduce(state, AbortRequested())
    assert effects == [CancelRun()]
    done, _ = reduce(state, RunFinished())
    assert done.run.phase is RunPhase.DONE
    failed, effects = reduce(state, RunFailed("boom"))
    assert failed.run.phase is RunPhase.ERROR
    assert effects == [Notify("Quickstart failed", "boom")]


def test_progress_ignored_when_idle() -> None:
    state = base()
    assert reduce(state, RunProgress("x"))[0] is state


def test_settings_changed_effects() -> None:
    state = base()
    new_settings = replace(state.settings, port=50000)
    new_state, effects = reduce(state, SettingsChanged(new_settings))
    assert new_state.settings.port == 50000
    assert effects == [SaveSettings(new_settings), RestartServer(50000)]
