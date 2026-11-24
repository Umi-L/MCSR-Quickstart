"""Effect handlers: the only place where reducer decisions touch the outside world."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from datetime import datetime
from typing import assert_never

from ..domain.seed import SeedRequest
from ..game.detector import StateFile
from ..game.monitor import GameMonitor, Target
from ..game.runner import RunAborted as RunAbortedError
from ..game.runner import RunError, Runner, RunTiming
from ..game.state import GameState
from ..infra.abort_hotkey import AbortHotkey
from ..infra.config import ConfigStore, Settings
from ..infra.keyboard import KeySender
from ..infra.server import BridgeServer, LaunchOutcome, ServerHooks
from .intents import (
    AbortRequested,
    GameStateChanged,
    MinecraftDetected,
    RunAborted,
    RunFailed,
    RunFinished,
    RunProgress,
    SeedReceived,
    ServerStatusChanged,
)
from .reducer import (
    CancelRun,
    Effect,
    Notify,
    RestartHotkey,
    RestartServer,
    SaveSettings,
    StartRun,
)
from .state import MinecraftInfo
from .store import Store

log = logging.getLogger(__name__)

NotifyFn = Callable[[str, str], None]


class RunController:
    """Runs at most one key sequence at a time on a worker thread."""

    def __init__(self, store: Store, keys: KeySender, monitor: GameMonitor) -> None:
        self._store = store
        self._keys = keys
        self._monitor = monitor
        self._cancel = threading.Event()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    @property
    def busy(self) -> bool:
        with self._lock:
            return self._thread is not None and self._thread.is_alive()

    def start(self, request: SeedRequest, settings: Settings) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._cancel = threading.Event()
            self._thread = threading.Thread(
                target=self._run, args=(request, settings, self._cancel), daemon=True
            )
            self._thread.start()

    def cancel(self) -> None:
        self._cancel.set()

    def _run(self, request: SeedRequest, settings: Settings, cancel: threading.Event) -> None:
        dispatch = self._store.dispatch
        directory = self._monitor.instance_dir()
        if directory is None:
            dispatch(RunFailed("Minecraft instance not found"))
            return
        runner = Runner(
            keys=self._keys,
            states=StateFile(directory),
            focus=self._monitor.focus,
            cancel=cancel,
            on_progress=lambda msg: dispatch(RunProgress(msg)),
            timing=RunTiming(
                key_delay_ms=settings.key_delay_ms,
                menu_wait_ms=settings.menu_wait_ms,
                startup_delay_ms=settings.startup_delay_ms,
                focus_settle_ms=settings.focus_settle_ms,
                step_timeout_s=float(settings.step_timeout_s),
                load_timeout_s=float(settings.load_timeout_s),
            ),
        )
        try:
            runner.run(request.seeds)
        except RunAbortedError:
            dispatch(RunAborted())
        except RunError as exc:
            dispatch(RunFailed(str(exc)))
        except Exception as exc:
            log.exception("run crashed")
            dispatch(RunFailed(f"Unexpected error: {exc}"))
        else:
            dispatch(RunFinished())


class EffectHandler:
    def __init__(
        self,
        store: Store,
        config: ConfigStore,
        keys: KeySender,
        monitor: GameMonitor,
        notify: NotifyFn,
    ) -> None:
        self._store = store
        self._config = config
        self._monitor = monitor
        self._notify = notify
        self._runs = RunController(store, keys, monitor)
        self._server: BridgeServer | None = None
        self._hotkey: AbortHotkey | None = None

    # -- lifecycle ------------------------------------------------------------------------

    def start(self) -> None:
        settings = self._store.state.settings
        self._monitor.configure(settings.window_title_pattern, settings.instance_dir_override)
        self._monitor.start()
        self._start_server(settings.port)
        self._start_hotkey(settings.abort_key)

    def stop(self) -> None:
        self._runs.cancel()
        self._monitor.stop()
        if self._server:
            self._server.stop()
        if self._hotkey:
            self._hotkey.stop()

    # -- dispatch target ------------------------------------------------------------------

    def __call__(self, effect: Effect) -> None:
        match effect:
            case StartRun(request=request, settings=settings):
                self._runs.start(request, settings)
            case CancelRun():
                self._runs.cancel()
            case SaveSettings(settings=settings):
                self._config.save(settings)
                self._monitor.configure(
                    settings.window_title_pattern, settings.instance_dir_override
                )
            case RestartServer(port=port):
                self._start_server(port)
            case RestartHotkey(key=key):
                self._start_hotkey(key)
            case Notify(title=title, message=message):
                self._notify(title, message)
            case _:
                assert_never(effect)

    # -- callbacks from infra (any thread) ------------------------------------------------

    def on_target(self, target: Target | None) -> None:
        info = None
        if target is not None:
            window = target.window
            info = MinecraftInfo(
                title=window.title if window else "(window not found)",
                pid=window.pid if window else 0,
                instance_dir=target.instance_dir,
            )
        self._store.dispatch(MinecraftDetected(info))

    def on_game_state(self, state: GameState) -> None:
        self._store.dispatch(GameStateChanged(state))

    # -- helpers --------------------------------------------------------------------------

    def _on_launch(self, request: SeedRequest) -> LaunchOutcome:
        if self._runs.busy:
            return "busy"
        self._store.dispatch(SeedReceived(request, datetime.now()))
        return "accepted"

    def _start_server(self, port: int) -> None:
        if self._server is not None:
            self._server.stop()
            self._server = None
        hooks = ServerHooks(
            token=lambda: self._store.state.settings.token,
            known_sites=lambda: {s.id for s in self._store.state.sites},
            is_running=lambda: self._runs.busy,
            on_launch=self._on_launch,
        )
        try:
            self._server = BridgeServer(port, hooks)
            self._server.start()
        except OSError as exc:
            log.error("Could not listen on port %s: %s", port, exc)
            self._store.dispatch(ServerStatusChanged(False, port, str(exc)))
            return
        self._store.dispatch(ServerStatusChanged(True, self._server.port))

    def _start_hotkey(self, key: str) -> None:
        if self._hotkey is not None:
            self._hotkey.stop()
        self._hotkey = AbortHotkey(key, lambda: self._store.dispatch(AbortRequested()))
        try:
            self._hotkey.start()
        except Exception:
            log.exception("abort hotkey unavailable")
