"""Contact force chart: F(t) during the impact, with the theoretical contact time."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen

from ..physics import CollisionResult, contact_duration
from .plot_canvas import PlotArea, PlotCanvas
from .theme import ACCENT, ACCENT_SOFT, MUTED, THEORY

MILLISECONDS = 1000


def polyline(area: PlotArea, x: np.ndarray, y: np.ndarray) -> QPainterPath:
    path = QPainterPath(QPointF(area.px(x[0]), area.py(y[0])))
    for xi, yi in zip(x[1:], y[1:], strict=True):
        path.lineTo(area.px(xi), area.py(yi))
    return path


class ContactCanvas(PlotCanvas):
    """Repulsion between the balls while they touch."""

    def __init__(self) -> None:
        super().__init__("Сила взаимодействия", "t, мс", "F, Н")
        self._result: CollisionResult | None = None
        self._theory_duration = 0.0

    def set_result(self, result: CollisionResult | None) -> None:
        self._result = result
        if result is None:
            self.set_data(np.asarray([]), np.asarray([]))
            return
        setup = result.setup
        self._theory_duration = contact_duration(
            result.contact, setup.effective_mass, setup.approach_speed
        )
        self.set_data(result.contact_times * MILLISECONDS, result.force)

    def _limits(self) -> tuple[tuple[float, float], tuple[float, float]]:
        if self._result is None:
            return super()._limits()
        right = max(float(self._x.max()), self._theory_duration * MILLISECONDS) * 1.04
        return (0.0, right), (0.0, float(self._y.max()) * 1.15)

    def _draw_series(self, painter: QPainter, area: PlotArea) -> None:
        if self._result is None:
            return
        fill = QPainterPath(QPointF(area.px(self._x[0]), area.rect.bottom()))
        for xi, yi in zip(self._x, self._y, strict=True):
            fill.lineTo(area.px(xi), area.py(yi))
        fill.lineTo(area.px(self._x[-1]), area.rect.bottom())
        fill.closeSubpath()
        gradient = QLinearGradient(0, area.rect.bottom(), 0, area.rect.top())
        gradient.setColorAt(0.0, QColor(ACCENT_SOFT))
        transparent = QColor(ACCENT)
        transparent.setAlpha(0)
        gradient.setColorAt(1.0, transparent)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.drawPath(fill)

        painter.setPen(QPen(QColor(ACCENT), 2.2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(polyline(area, self._x, self._y))

        theory = area.px(self._theory_duration * MILLISECONDS)
        painter.setPen(QPen(QColor(THEORY), 1.2, Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(theory, area.rect.top()), QPointF(theory, area.rect.bottom()))
        painter.setPen(QColor(MUTED))
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        painter.drawText(QPointF(theory - 52, area.rect.top() + 16), "τ теор")

    def _hover_lines(self, index: int) -> list[str]:
        if self._result is None:
            return []
        return [
            f"t = {self._x[index]:.4f} мс",
            f"F = {self._y[index]:.4g} Н",
            f"δ = {self._result.compression[index] * 1000:.4g} мм",
        ]
