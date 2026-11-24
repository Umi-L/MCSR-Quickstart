"""Small reusable widgets."""

from __future__ import annotations

from typing import Literal

from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

Status = Literal["ok", "warn", "error", "idle", "busy"]


def set_status(label: QLabel, status: Status) -> None:
    if label.property("status") != status:
        label.setProperty("status", status)
        label.style().unpolish(label)
        label.style().polish(label)


class Card(QFrame):
    def __init__(self, title: str | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(18, 16, 18, 16)
        self.body.setSpacing(10)
        if title:
            heading = QLabel(title.upper())
            heading.setObjectName("CardTitle")
            self.body.addWidget(heading)


class StatusCard(Card):
    """Title, coloured dot, value and a muted detail line."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(title, parent)
        row = QHBoxLayout()
        row.setSpacing(8)
        self.dot = QLabel("●")
        self.dot.setObjectName("Dot")
        self.value = QLabel("—")
        self.value.setObjectName("CardValue")
        row.addWidget(self.dot)
        row.addWidget(self.value, 1)
        self.body.addLayout(row)
        self.detail = QLabel("")
        self.detail.setObjectName("Muted")
        self.detail.setWordWrap(True)
        self.body.addWidget(self.detail)
        set_status(self.dot, "idle")

    def show_status(self, status: Status, value: str, detail: str = "") -> None:
        set_status(self.dot, status)
        self.value.setText(value)
        self.detail.setText(detail)
        self.detail.setToolTip(detail)


class SeedField(QWidget):
    """Caption + monospace seed + copy button."""

    def __init__(self, caption: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        cap = QLabel(caption.upper())
        cap.setObjectName("CardTitle")
        row = QHBoxLayout()
        self.value = QLabel("—")
        self.value.setObjectName("Seed")
        self.copy = QPushButton("Copy")
        self.copy.setObjectName("Ghost")
        self.copy.clicked.connect(self._copy)
        row.addWidget(self.value, 1)
        row.addWidget(self.copy)
        layout.addWidget(cap)
        layout.addLayout(row)

    def set_seed(self, seed: str | None) -> None:
        self.value.setText(seed or "—")
        self.copy.setEnabled(bool(seed))

    def _copy(self) -> None:
        clipboard = QApplication.clipboard()
        text = self.value.text()
        if text != "—":
            clipboard.setText(text)
