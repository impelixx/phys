"""Energy chart: kinetic energy turns into elastic energy and back during the contact."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen

from ..physics import CollisionResult
from .contact_canvas import MILLISECONDS, polyline
from .plot_canvas import PlotArea, PlotCanvas
from .theme import ACCENT, BALL2, ELASTIC


class EnergyCanvas(PlotCanvas):
    """E_k + U = E stays flat: the impact is perfectly elastic."""

    def __init__(self) -> None:
        super().__init__("Энергия во время контакта", "t, мс", "E, Дж")
        self._result: CollisionResult | None = None

    def set_result(self, result: CollisionResult | None) -> None:
        self._result = result
        if result is None:
            self.set_data(np.asarray([]), np.asarray([]))
            return
        self.set_data(result.contact_times * MILLISECONDS, result.total_energy)

    def _limits(self) -> tuple[tuple[float, float], tuple[float, float]]:
        if self._result is None:
            return super()._limits()
        return (0.0, float(self._x.max()) * 1.04), (0.0, float(self._y.max()) * 1.2)

    def _draw_series(self, painter: QPainter, area: PlotArea) -> None:
        if self._result is None:
            return
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(ELASTIC), 1.8))
        painter.drawPath(polyline(area, self._x, self._result.elastic_energy))
        painter.setPen(QPen(QColor(BALL2), 1.8))
        painter.drawPath(polyline(area, self._x, self._result.kinetic_energy))
        painter.setPen(QPen(QColor(ACCENT), 2.4))
        painter.drawPath(polyline(area, self._x, self._y))

        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        x = area.rect.left() + 8
        y = area.rect.top() + 16
        for label, color in (("E", ACCENT), ("Eк", BALL2), ("U упр", ELASTIC)):
            painter.setPen(QColor(color))
            painter.drawText(QPointF(x, y), f"— {label}")
            x += 56

    def _hover_lines(self, index: int) -> list[str]:
        if self._result is None:
            return []
        return [
            f"t = {self._x[index]:.4f} мс",
            f"E = {self._y[index]:.8g} Дж",
            f"Eк = {self._result.kinetic_energy[index]:.5g} Дж",
            f"U = {self._result.elastic_energy[index]:.5g} Дж",
        ]
