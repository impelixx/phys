"""Period chart: numeric period against the exact elliptic-integral theory."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen

from ..physics import Rod, exact_period, small_angle_period, swing_period
from .angle_canvas import polyline
from .plot_canvas import PlotArea, PlotCanvas
from .theme import ACCENT, KINETIC, MUTED, THEORY

SAMPLED_AMPLITUDES = np.arange(5.0, 180.0, 5.0)
THEORY_AMPLITUDES = np.linspace(0.0, 176.0, 300)


class PeriodCanvas(PlotCanvas):
    """Frictionless period as a function of the release angle."""

    def __init__(self) -> None:
        super().__init__("Период от амплитуды (без трения)", "φ₀, °", "T, с")
        self._rod: Rod | None = None
        self._amplitude = 0.0
        self._theory = np.asarray([])
        self._small_angle = 0.0

    def set_rod(self, rod: Rod, amplitude: float) -> None:
        """Recompute the curves only when the rod geometry actually changes."""
        self._amplitude = amplitude
        if self._rod is not None and self._rod.length == rod.length:
            self.update()
            return
        self._rod = rod
        self._small_angle = small_angle_period(rod)
        self._theory = np.array([exact_period(rod, value) for value in THEORY_AMPLITUDES])
        numeric = np.array([swing_period(rod, value) for value in SAMPLED_AMPLITUDES])
        self.set_data(SAMPLED_AMPLITUDES, numeric)

    def _limits(self) -> tuple[tuple[float, float], tuple[float, float]]:
        if self._rod is None:
            return super()._limits()
        return (0.0, 180.0), (0.0, float(self._y.max()) * 1.1)

    def _draw_series(self, painter: QPainter, area: PlotArea) -> None:
        if self._rod is None:
            return

        painter.setPen(QPen(QColor(MUTED), 1, Qt.PenStyle.DashLine))
        level = area.py(self._small_angle)
        painter.drawLine(QPointF(area.rect.left(), level), QPointF(area.rect.right(), level))

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(THEORY), 1.4))
        painter.drawPath(polyline(area, THEORY_AMPLITUDES, self._theory))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(KINETIC)))
        for amplitude, period in zip(self._x, self._y, strict=True):
            painter.drawEllipse(QPointF(area.px(amplitude), area.py(period)), 3.2, 3.2)

        current = QPointF(
            area.px(self._amplitude), area.py(exact_period(self._rod, self._amplitude))
        )
        painter.setPen(QPen(QColor(ACCENT), 1.6))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(current, 6, 6)

        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        painter.setPen(QColor(MUTED))
        painter.drawText(QPointF(area.rect.right() - 150, level + 16), "T₀ (малые колебания)")
        painter.drawText(
            QPointF(area.rect.left() + 8, area.rect.top() + 16),
            "● расчёт   — теория: T = 4K(sin²(φ₀/2)) / ω₀",
        )

    def _hover_lines(self, index: int) -> list[str]:
        if self._rod is None:
            return []
        amplitude = float(self._x[index])
        theory = exact_period(self._rod, amplitude)
        return [
            f"φ₀ = {amplitude:.0f}°",
            f"T расчёт = {self._y[index]:.5f} с",
            f"T теория = {theory:.5f} с",
            f"T / T₀ = {theory / self._small_angle:.4f}",
        ]
