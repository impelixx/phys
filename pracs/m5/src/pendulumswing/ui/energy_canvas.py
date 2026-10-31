"""Energy chart: kinetic, potential and total energy over time."""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen

from ..physics import SwingResult
from .angle_canvas import polyline
from .plot_canvas import PlotArea, PlotCanvas
from .theme import ACCENT, KINETIC, POTENTIAL


class EnergyCanvas(PlotCanvas):
    """E_k + E_p = E: flat without friction, decaying with it."""

    def __init__(self) -> None:
        super().__init__("Энергия", "t, с", "E, Дж")
        self._result: SwingResult | None = None

    def set_result(self, result: SwingResult) -> None:
        self._result = result
        self.set_data(result.times, result.total_energy)

    def _limits(self) -> tuple[tuple[float, float], tuple[float, float]]:
        if self._result is None:
            return super()._limits()
        top = float(self._result.total_energy.max())
        return (0.0, float(self._x.max())), (0.0, max(top * 1.15, 10 ** (-9)))

    def _draw_series(self, painter: QPainter, area: PlotArea) -> None:
        if self._result is None:
            return
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(POTENTIAL), 1.6))
        painter.drawPath(polyline(area, self._x, self._result.potential_energy))
        painter.setPen(QPen(QColor(KINETIC), 1.6))
        painter.drawPath(polyline(area, self._x, self._result.kinetic_energy))
        painter.setPen(QPen(QColor(ACCENT), 2.4))
        painter.drawPath(polyline(area, self._x, self._y))

        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        x = area.rect.left() + 8
        y = area.rect.top() + 16
        for label, color in (("E", ACCENT), ("Eк", KINETIC), ("Eп", POTENTIAL)):
            painter.setPen(QColor(color))
            painter.drawText(QPointF(x, y), f"— {label}")
            x += 44

    def _hover_lines(self, index: int) -> list[str]:
        if self._result is None:
            return []
        return [
            f"t = {self._x[index]:.3f} с",
            f"E = {self._result.total_energy[index]:.6g} Дж",
            f"Eк = {self._result.kinetic_energy[index]:.4g} Дж",
            f"Eп = {self._result.potential_energy[index]:.4g} Дж",
        ]
