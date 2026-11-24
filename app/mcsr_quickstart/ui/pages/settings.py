"""Settings page."""

from __future__ import annotations

import re
from dataclasses import replace

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...domain.sites import SiteInfo
from ...infra.config import Settings, new_token
from ...mvi.intents import SettingsChanged
from ...mvi.state import AppState
from ...mvi.store import Store
from ..widgets import Card


class SettingsPage(QWidget):
    def __init__(self, store: Store, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._store = store
        self._shown: Settings | None = None
        self._shown_sites: tuple[SiteInfo, ...] | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        outer.addWidget(scroll)
        content = QWidget()
        content.setObjectName("PageBody")
        scroll.setWidget(content)

        root = QVBoxLayout(content)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)
        title = QLabel("Settings")
        title.setObjectName("PageTitle")
        root.addWidget(title)

        # Browser pairing
        pairing = Card("Browser extension")
        form = QFormLayout()
        form.setSpacing(10)
        self.port = QSpinBox()
        self.port.setRange(1024, 65535)
        form.addRow("Port", self.port)
        token_row = QHBoxLayout()
        self.token = QLineEdit()
        self.token.setReadOnly(True)
        copy = QPushButton("Copy")
        copy.clicked.connect(lambda: QApplication.clipboard().setText(self.token.text()))
        regen = QPushButton("Regenerate")
        regen.clicked.connect(lambda: self.token.setText(new_token()))
        token_row.addWidget(self.token, 1)
        token_row.addWidget(copy)
        token_row.addWidget(regen)
        form.addRow("Pairing token", token_row)
        pairing.body.addLayout(form)
        hint = QLabel("Paste the port and token into the extension popup.")
        hint.setObjectName("Muted")
        pairing.body.addWidget(hint)
        root.addWidget(pairing)

        # Minecraft
        game = Card("Minecraft")
        gform = QFormLayout()
        gform.setSpacing(10)
        self.title_pattern = QLineEdit()
        self.title_pattern.setPlaceholderText("^Minecraft")
        gform.addRow("Window title regex", self.title_pattern)
        dir_row = QHBoxLayout()
        self.instance_dir = QLineEdit()
        self.instance_dir.setPlaceholderText("Auto-detect from the running game")
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        dir_row.addWidget(self.instance_dir, 1)
        dir_row.addWidget(browse)
        gform.addRow("Instance folder", dir_row)
        self.key_delay = self._spin(0, 2000, " ms")
        gform.addRow("Delay between keys", self.key_delay)
        self.menu_wait = self._spin(0, 10000, " ms")
        gform.addRow("Wait after a menu opens", self.menu_wait)
        self.startup_delay = self._spin(0, 30000, " ms")
        gform.addRow("Delay before starting", self.startup_delay)
        self.focus_settle = self._spin(0, 10000, " ms")
        gform.addRow("Wait after focusing Minecraft", self.focus_settle)
        self.step_timeout = self._spin(1, 300, " s")
        gform.addRow("Give up on a step after", self.step_timeout)
        self.load_timeout = self._spin(1, 1800, " s")
        gform.addRow("Give up on loading after", self.load_timeout)
        self.abort_key = QLineEdit()
        self.abort_key.setPlaceholderText("f8")
        gform.addRow("Abort key", self.abort_key)
        game.body.addLayout(gform)
        root.addWidget(game)

        # Behaviour
        behaviour = Card("Behaviour")
        self.auto_run = QCheckBox("Start a run as soon as a seed arrives from the browser")
        self.start_in_tray = QCheckBox("Start minimised to the system tray")
        behaviour.body.addWidget(self.auto_run)
        behaviour.body.addWidget(self.start_in_tray)
        root.addWidget(behaviour)

        # Sites
        self.sites_card = Card("Supported sites")
        self.sites_label = QLabel()
        self.sites_label.setObjectName("Muted")
        self.sites_label.setWordWrap(True)
        self.sites_card.body.addWidget(self.sites_label)
        root.addWidget(self.sites_card)

        # Save bar
        bar = QHBoxLayout()
        self.error = QLabel("")
        self.error.setProperty("status", "error")
        revert = QPushButton("Revert")
        revert.clicked.connect(self._revert)
        save = QPushButton("Save changes")
        save.setObjectName("Primary")
        save.clicked.connect(self._save)
        bar.addWidget(self.error, 1)
        bar.addWidget(revert)
        bar.addWidget(save)
        root.addLayout(bar)
        root.addStretch(1)

    def render_state(self, state: AppState) -> None:
        # Only overwrite the form when the persisted settings change, never mid-edit.
        if state.settings is not self._shown:
            self._shown = state.settings
            self._fill(state.settings)
        if state.sites is not self._shown_sites:
            self._shown_sites = state.sites
            lines = [f"<b>{s.name}</b> — {', '.join(s.matches)}" for s in state.sites]
            self.sites_label.setText("<br>".join(lines) or "No sites.json found")

    @staticmethod
    def _spin(low: int, high: int, suffix: str) -> QSpinBox:
        box = QSpinBox()
        box.setRange(low, high)
        box.setSuffix(suffix)
        return box

    def _fill(self, s: Settings) -> None:
        self.port.setValue(s.port)
        self.token.setText(s.token)
        self.title_pattern.setText(s.window_title_pattern)
        self.instance_dir.setText(s.instance_dir_override)
        self.key_delay.setValue(s.key_delay_ms)
        self.menu_wait.setValue(s.menu_wait_ms)
        self.startup_delay.setValue(s.startup_delay_ms)
        self.focus_settle.setValue(s.focus_settle_ms)
        self.step_timeout.setValue(s.step_timeout_s)
        self.load_timeout.setValue(s.load_timeout_s)
        self.abort_key.setText(s.abort_key)
        self.auto_run.setChecked(s.auto_run)
        self.start_in_tray.setChecked(s.start_in_tray)
        self.error.setText("")

    def _revert(self) -> None:
        if self._shown is not None:
            self._fill(self._shown)

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select the instance's .minecraft folder")
        if path:
            self.instance_dir.setText(path)

    def _save(self) -> None:
        pattern = self.title_pattern.text().strip() or r"^Minecraft"
        try:
            re.compile(pattern)
        except re.error as exc:
            self.error.setText(f"Invalid regex: {exc}")
            return
        current = self._store.state.settings
        updated = replace(
            current,
            port=self.port.value(),
            token=self.token.text(),
            window_title_pattern=pattern,
            instance_dir_override=self.instance_dir.text().strip(),
            key_delay_ms=self.key_delay.value(),
            menu_wait_ms=self.menu_wait.value(),
            startup_delay_ms=self.startup_delay.value(),
            focus_settle_ms=self.focus_settle.value(),
            step_timeout_s=self.step_timeout.value(),
            load_timeout_s=self.load_timeout.value(),
            abort_key=self.abort_key.text().strip().lower() or "f8",
            auto_run=self.auto_run.isChecked(),
            start_in_tray=self.start_in_tray.isChecked(),
        )
        self.error.setText("")
        if updated != current:
            self._store.dispatch(SettingsChanged(updated))
