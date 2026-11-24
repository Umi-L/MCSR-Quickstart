"""Dashboard page: live status, current seed set, history."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...domain.seed import SeedRequest
from ...game.state import (
    GameState,
    Generating,
    InWorld,
    NotRunning,
    Previewing,
    Title,
    Unknown,
    Waiting,
    Wall,
    describe,
)
from ...mvi.intents import AbortRequested, ClearHistory, RunRequested
from ...mvi.state import AppState, HistoryEntry, RunPhase
from ...mvi.store import Store
from ..widgets import Card, SeedField, Status, StatusCard, set_status


def _game_status(state: GameState) -> Status:
    match state:
        case Title() | InWorld():
            return "ok"
        case Generating() | Previewing() | Waiting():
            return "busy"
        case Wall() | Unknown():
            return "warn"
        case NotRunning():
            return "idle"


_RUN_STATUS: dict[RunPhase, Status] = {
    RunPhase.IDLE: "idle",
    RunPhase.RUNNING: "busy",
    RunPhase.DONE: "ok",
    RunPhase.ABORTED: "warn",
    RunPhase.ERROR: "error",
}


class DashboardPage(QWidget):
    def __init__(self, store: Store, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._store = store
        self._rendered_history: tuple[HistoryEntry, ...] | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        title = QLabel("Dashboard")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Click ▶ Play on a supported seed site to start a run.")
        subtitle.setObjectName("PageSubtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        # Status row
        grid = QGridLayout()
        grid.setSpacing(12)
        self.bridge_card = StatusCard("Browser bridge")
        self.mc_card = StatusCard("Minecraft")
        self.game_card = StatusCard("Game state")
        for col, card in enumerate((self.bridge_card, self.mc_card, self.game_card)):
            grid.addWidget(card, 0, col)
            grid.setColumnStretch(col, 1)
        root.addLayout(grid)

        # Current seed
        seed_card = Card("Current seed")
        self.seed_label = QLabel("No seed received yet")
        self.seed_label.setObjectName("CardValue")
        seed_card.body.addWidget(self.seed_label)
        seeds_row = QHBoxLayout()
        seeds_row.setSpacing(24)
        self.ow_field = SeedField("Overworld / End")
        self.nether_field = SeedField("Nether")
        self.rng_field = SeedField("RNG")
        for widget in (self.ow_field, self.nether_field, self.rng_field):
            seeds_row.addWidget(widget, 1)
        seed_card.body.addLayout(seeds_row)

        actions = QHBoxLayout()
        self.run_dot = QLabel("●")
        self.run_dot.setObjectName("Dot")
        self.run_message = QLabel("Idle")
        self.run_message.setObjectName("Muted")
        self.run_button = QPushButton("▶  Run")
        self.run_button.setObjectName("Primary")
        self.run_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.run_button.clicked.connect(self._run_current)
        self.abort_button = QPushButton("Abort")
        self.abort_button.setObjectName("Danger")
        self.abort_button.clicked.connect(lambda: self._store.dispatch(AbortRequested()))
        actions.addWidget(self.run_dot)
        actions.addWidget(self.run_message, 1)
        actions.addWidget(self.abort_button)
        actions.addWidget(self.run_button)
        seed_card.body.addLayout(actions)
        root.addWidget(seed_card)

        # History
        history_card = Card("History")
        header = QHBoxLayout()
        hint = QLabel("Double-click an entry to run it again.")
        hint.setObjectName("Muted")
        clear = QPushButton("Clear")
        clear.setObjectName("Ghost")
        clear.clicked.connect(lambda: self._store.dispatch(ClearHistory()))
        header.addWidget(hint, 1)
        header.addWidget(clear)
        history_card.body.addLayout(header)
        self.history = QListWidget()
        self.history.itemDoubleClicked.connect(self._rerun)
        history_card.body.addWidget(self.history, 1)
        root.addWidget(history_card, 1)

    # -- rendering ------------------------------------------------------------------------

    def render_state(self, state: AppState) -> None:
        server = state.server
        if server.listening:
            self.bridge_card.show_status("ok", "Connected", f"Listening on 127.0.0.1:{server.port}")
        elif server.error:
            self.bridge_card.show_status("error", "Offline", server.error)
        else:
            self.bridge_card.show_status("idle", "Starting…")

        mc = state.minecraft
        if mc is None:
            self.mc_card.show_status("idle", "Not found", "Start your MCSR Ranked instance")
        elif mc.instance_dir is None:
            self.mc_card.show_status("warn", "Instance unknown", mc.title)
        else:
            self.mc_card.show_status("ok", mc.title, str(mc.instance_dir))

        self.game_card.show_status(
            _game_status(state.game),
            describe(state.game),
            "via wpstateout.txt" if not isinstance(state.game, NotRunning) else "State Output mod",
        )

        current = state.current
        if current is None:
            self.seed_label.setText("No seed received yet")
        else:
            self.seed_label.setText(current.label or self._site_name(state, current.site))
        self.ow_field.set_seed(current.seeds.overworld if current else None)
        self.nether_field.set_seed(current.seeds.nether if current else None)
        self.rng_field.set_seed(current.seeds.rng if current else None)

        set_status(self.run_dot, _RUN_STATUS[state.run.phase])
        self.run_message.setText(state.run.message or state.run.phase.value.capitalize())
        self.run_button.setEnabled(current is not None and not state.run.busy)
        self.abort_button.setVisible(state.run.busy)

        if state.history is not self._rendered_history:
            self._rendered_history = state.history
            self._render_history(state)

    def _render_history(self, state: AppState) -> None:
        self.history.clear()
        for entry in state.history:
            req = entry.request
            name = req.label or self._site_name(state, req.site)
            text = (
                f"{name}   ·   {self._site_name(state, req.site)}   ·   "
                f"{entry.received_at:%H:%M}\n{req.seeds.overworld}  /  {req.seeds.nether}"
            )
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, req)
            item.setToolTip(req.source_url)
            self.history.addItem(item)

    @staticmethod
    def _site_name(state: AppState, site_id: str) -> str:
        return next((s.name for s in state.sites if s.id == site_id), site_id)

    # -- actions --------------------------------------------------------------------------

    def _run_current(self) -> None:
        current = self._store.state.current
        if current is not None:
            self._store.dispatch(RunRequested(current))

    def _rerun(self, item: QListWidgetItem) -> None:
        request = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(request, SeedRequest):
            self._store.dispatch(RunRequested(request))
