"""App icon drawn at runtime so no binary assets are needed."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QIcon, QPainter, QPixmap, QPolygonF


def app_icon(size: int = 64) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor("#7c5cff")))
    radius = size * 0.22
    painter.drawRoundedRect(QRectF(0, 0, size, size), radius, radius)
    painter.setBrush(QBrush(QColor("#ffffff")))
    s = float(size)
    triangle = QPolygonF(
        [QPointF(s * 0.38, s * 0.28), QPointF(s * 0.38, s * 0.72), QPointF(s * 0.74, s * 0.5)]
    )
    painter.drawPolygon(triangle)
    painter.end()
    return QIcon(pixmap)
