"""Pendulum view: the swinging rod, its turning points and the release angle."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from ..physics import SwingResult
from .theme import ACCENT, BACKGROUND, BORDER, CANVAS, GRID, MUTED, TEXT

GHOST_TURNS = 12


class PendulumCanvas(QWidget):
    """Rod hanging from a pivot in the middle; φ is measured from the downward vertical."""

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(260, 260)
        self._result: SwingResult | None = None
        self._index = 0

    def set_result(self, result: SwingResult) -> None:
        self._result = result
        self._index = 0
        self.update()

    def set_index(self, index: int) -> None:
        self._index = index
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802, ARG002 (Qt naming)
        painter = QPainter(self)
        painter.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing
        )
        frame = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.setPen(QPen(QColor(BORDER), 1))
        painter.setBrush(QColor(CANVAS))
        painter.drawRoundedRect(frame, 10, 10)

        painter.setPen(QColor(TEXT))
        font = painter.font()
        font.setPointSize(11)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.drawText(QPointF(18, 24), "Маятник")

        if self._result is None:
            return
        result = self._result
        index = min(self._index, result.times.size - 1)

        pivot = QPointF(frame.center().x(), frame.center().y() + 8)
        radius = 0.4 * min(frame.width(), frame.height() - 40)

        def tip(angle: float) -> QPointF:
            return QPointF(
                pivot.x() + radius * math.sin(angle),
                pivot.y() + radius * math.cos(angle),
            )

        painter.setPen(QPen(QColor(GRID), 1, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(pivot, radius, radius)
        painter.drawLine(pivot, QPointF(pivot.x(), pivot.y() + radius))

        amplitude = result.amplitude
        painter.setPen(QPen(QColor(MUTED), 1))
        arc_radius = radius * 0.28
        arc_box = QRectF(
            pivot.x() - arc_radius, pivot.y() - arc_radius, 2 * arc_radius, 2 * arc_radius
        )
        # Qt angles: degrees * 16, counter-clockwise from 3 o'clock; down is -90°.
        painter.drawArc(arc_box, -90 * 16, round(math.degrees(amplitude) * 16))

        ghost = QColor(ACCENT)
        for turn_angle in result.turning_angles[:GHOST_TURNS]:
            ghost.setAlpha(55)
            painter.setPen(QPen(ghost, 2))
            painter.drawLine(pivot, tip(float(turn_angle)))

        angle = float(result.angle[index])
        end = tip(angle)
        painter.setPen(QPen(QColor(ACCENT), 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(pivot, end)
        centre = QPointF((pivot.x() + end.x()) / 2, (pivot.y() + end.y()) / 2)
        painter.setPen(QPen(QColor(BACKGROUND), 1.4))
        painter.setBrush(QColor(TEXT))
        painter.drawEllipse(centre, 3.5, 3.5)

        painter.setPen(QPen(QColor(BACKGROUND), 1.6))
        painter.setBrush(QColor(TEXT))
        painter.drawEllipse(pivot, 5.5, 5.5)

        font.setPointSize(10)
        font.setWeight(QFont.Weight.Normal)
        painter.setFont(font)
        painter.setPen(QColor(MUTED))
        painter.drawText(
            QPointF(18, frame.bottom() - 14),
            f"φ₀ = {math.degrees(amplitude):.1f}°   t = {result.times[index]:.2f} с"
            f"   φ = {math.degrees(angle):+.2f}°",
        )
