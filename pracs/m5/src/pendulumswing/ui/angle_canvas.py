"""Angle chart: simulated φ(t) against the linearised theory."""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen

from ..physics import SwingResult, linear_angle
from .plot_canvas import PlotArea, PlotCanvas
from .theme import ACCENT, MUTED, TEXT, THEORY


def polyline(area: PlotArea, x: np.ndarray, y: np.ndarray) -> QPainterPath:
    path = QPainterPath(QPointF(area.px(x[0]), area.py(y[0])))
    for xi, yi in zip(x[1:], y[1:], strict=True):
        path.lineTo(area.px(xi), area.py(yi))
    return path


class AngleCanvas(PlotCanvas):
    """Deflection angle in degrees over time, with turning points and the animation cursor."""

    def __init__(self) -> None:
        super().__init__("Угол отклонения", "t, с", "φ, °")
        self._result: SwingResult | None = None
        self._theory = np.asarray([])
        self._cursor: int | None = None

    def set_result(self, result: SwingResult) -> None:
        self._result = result
        self._cursor = None
        self._theory = np.degrees(
            linear_angle(result.rod, math.degrees(result.amplitude), result.times)
        )
        self.set_data(result.times, np.degrees(result.angle))

    def set_cursor(self, index: int) -> None:
        self._cursor = index
        self.update()

    def _limits(self) -> tuple[tuple[float, float], tuple[float, float]]:
        if self._result is None:
            return super()._limits()
        span = max(math.degrees(self._result.amplitude) * 1.15, 0.1)
        return (0.0, float(self._x.max())), (-span, span)

    def _draw_series(self, painter: QPainter, area: PlotArea) -> None:
        if self._result is None:
            return

        zero = area.py(0.0)
        painter.setPen(QPen(QColor(MUTED), 1, Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(area.rect.left(), zero), QPointF(area.rect.right(), zero))

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(THEORY), 1.2, Qt.PenStyle.DashLine))
        painter.drawPath(polyline(area, self._x, self._theory))

        painter.setPen(QPen(QColor(ACCENT), 2.2))
        painter.drawPath(polyline(area, self._x, self._y))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(ACCENT)))
        for time, angle in zip(
            self._result.turning_times, self._result.turning_angles, strict=True
        ):
            painter.drawEllipse(QPointF(area.px(time), area.py(math.degrees(angle))), 2.6, 2.6)

        if self._cursor is not None:
            index = min(self._cursor, self._x.size - 1)
            x = area.px(self._x[index])
            painter.setPen(QPen(QColor(TEXT), 1))
            painter.drawLine(QPointF(x, area.rect.top()), QPointF(x, area.rect.bottom()))

        painter.setPen(QColor(MUTED))
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        painter.drawText(
            QPointF(area.rect.left() + 8, area.rect.bottom() - 8),
            "— расчёт   - - линейная теория (sin φ ≈ φ)",
        )

    def _hover_lines(self, index: int) -> list[str]:
        if self._result is None:
            return []
        return [
            f"t = {self._x[index]:.3f} с",
            f"φ = {self._y[index]:+.3f}°",
            f"φ теор = {self._theory[index]:+.3f}°",
            f"ω = {self._result.angular_velocity[index]:+.3f} рад/с",
        ]
