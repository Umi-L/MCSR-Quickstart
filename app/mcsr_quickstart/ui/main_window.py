"""Main window: title bar, navigation island, page island and status bar (islands layout)."""

from __future__ import annotations

from importlib import resources

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from ..mvi.state import AppState, RunPhase
from ..mvi.store import Store
from .icon import app_icon
from .pages.dashboard import DashboardPage
from .pages.settings import SettingsPage
from .widgets import Status, set_status

_PAGES = ("Dashboard", "Settings")

_RUN_STATUS: dict[RunPhase, Status] = {
    RunPhase.IDLE: "idle",
    RunPhase.RUNNING: "busy",
    RunPhase.DONE: "ok",
    RunPhase.ABORTED: "warn",
    RunPhase.ERROR: "error",
}


def load_stylesheet() -> str:
    return resources.files("mcsr_quickstart.ui").joinpath("theme.qss").read_text("utf-8")


class MainWindow(QMainWindow):
    def __init__(self, store: Store, *, hide_on_close: bool) -> None:
        super().__init__()
        self._hide_on_close = hide_on_close
        self.setWindowTitle("MCSR Quickstart")
        self.setWindowIcon(app_icon())
        self.resize(1040, 700)
        self.setMinimumSize(800, 560)

        root = QWidget()
        root.setObjectName("Root")
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.setCentralWidget(root)

        outer.addWidget(self._build_titlebar())

        body = QHBoxLayout()
        body.setContentsMargins(8, 0, 8, 0)
        body.setSpacing(8)
        body.addWidget(self._build_nav())

        self.pages = QStackedWidget()
        self.dashboard = DashboardPage(store)
        self.settings = SettingsPage(store)
        self.pages.addWidget(self.dashboard)
        self.pages.addWidget(self.settings)
        island = QFrame()
        island.setObjectName("Island")
        island_layout = QVBoxLayout(island)
        island_layout.setContentsMargins(0, 0, 0, 0)
        island_layout.addWidget(self.pages)
        body.addWidget(island, 1)
        outer.addLayout(body, 1)

        outer.addWidget(self._build_statusbar())

        store.state_changed.connect(self.render_state)
        self.render_state(store.state)

    # -- layout pieces --------------------------------------------------------------------

    def _build_titlebar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("TitleBar")
        bar.setFixedHeight(46)
        row = QHBoxLayout(bar)
        row.setContentsMargins(14, 0, 14, 0)
        row.setSpacing(8)

        badge = QLabel("MQ")
        badge.setObjectName("Badge")
        brand = QLabel("MCSR Quickstart")
        brand.setObjectName("Brand")
        self.title_center = QLabel("Dashboard")
        self.title_center.setObjectName("TitleCenter")

        self.pill_dot = QLabel("●")
        self.pill_dot.setObjectName("Dot")
        self.pill_text = QLabel("Idle")
        self.pill_text.setObjectName("PillText")

        row.addWidget(badge)
        row.addWidget(brand)
        row.addStretch(1)
        row.addWidget(self.title_center)
        row.addStretch(1)
        row.addWidget(self.pill_dot)
        row.addWidget(self.pill_text)
        return bar

    def _build_nav(self) -> QWidget:
        nav = QFrame()
        nav.setObjectName("Island")
        nav.setFixedWidth(220)
        col = QVBoxLayout(nav)
        col.setContentsMargins(0, 0, 0, 10)
        col.setSpacing(0)

        head = QLabel("Quickstart")
        head.setObjectName("PanelHead")
        col.addWidget(head)
        group = QLabel("PAGES")
        group.setObjectName("GroupLabel")
        col.addWidget(group)

        buttons = QButtonGroup(self)
        for index, label in enumerate(_PAGES):
            button = QPushButton(f"{index + 1}   {label}")
            button.setObjectName("NavButton")
            button.setCheckable(True)
            button.setChecked(index == 0)
            button.clicked.connect(lambda _=False, i=index: self._show_page(i))
            buttons.addButton(button)
            col.addWidget(button)
        col.addStretch(1)
        return nav

    def _build_statusbar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("StatusBar")
        bar.setFixedHeight(30)
        row = QHBoxLayout(bar)
        row.setContentsMargins(16, 0, 16, 0)
        row.setSpacing(16)
        self.crumb = QLabel("MCSR Quickstart  >  Dashboard")
        self.crumb.setObjectName("StatusText")
        self.bridge_text = QLabel("")
        self.bridge_text.setObjectName("StatusText")
        version = QLabel(f"v{__version__}")
        version.setObjectName("Version")
        row.addWidget(self.crumb, 1)
        row.addWidget(self.bridge_text)
        row.addWidget(version)
        return bar

    def _show_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        self.title_center.setText(_PAGES[index])
        self.crumb.setText(f"MCSR Quickstart  >  {_PAGES[index]}")

    # -- state ----------------------------------------------------------------------------

    def render_state(self, state: AppState) -> None:
        self.dashboard.render_state(state)
        self.settings.render_state(state)

        run = state.run
        self.pill_text.setText(run.message or run.phase.value.capitalize())
        set_status(self.pill_dot, _RUN_STATUS[run.phase])
        server = state.server
        if server.listening:
            self.bridge_text.setText(f"Bridge 127.0.0.1:{server.port}")
        else:
            self.bridge_text.setText("Bridge offline" if server.error else "Bridge starting…")

    def set_hide_on_close(self, value: bool) -> None:
        self._hide_on_close = value

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._hide_on_close:
            event.ignore()
            self.hide()
        else:
            event.accept()
