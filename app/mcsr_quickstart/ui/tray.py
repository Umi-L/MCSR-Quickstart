"""System tray icon."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from ..game.state import describe
from ..mvi.intents import AbortRequested
from ..mvi.state import AppState
from ..mvi.store import Store
from .icon import app_icon
from .main_window import MainWindow


class Tray(QSystemTrayIcon):
    def __init__(self, store: Store, window: MainWindow) -> None:
        super().__init__(app_icon())
        self._window = window
        menu = QMenu()
        menu.addAction("Open", self._show)
        menu.addAction("Abort run", lambda: store.dispatch(AbortRequested()))
        menu.addSeparator()
        menu.addAction("Quit", QApplication.quit)
        self._menu = menu  # keep a reference
        self.setContextMenu(menu)
        self.activated.connect(self._on_activated)
        store.state_changed.connect(self.render_state)
        self.render_state(store.state)

    def render_state(self, state: AppState) -> None:
        self.setToolTip(f"MCSR Quickstart — {describe(state.game)}\n{state.run.message}".strip())

    def notify(self, title: str, message: str) -> None:
        self.showMessage(title, message, QSystemTrayIcon.MessageIcon.Warning, 4000)

    def _show(self) -> None:
        self._window.showNormal()
        self._window.raise_()
        self._window.activateWindow()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._show()
