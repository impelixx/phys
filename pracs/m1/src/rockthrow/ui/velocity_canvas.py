"""Velocity chart: speed magnitude over time."""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen

from ..physics import FlightResult
from .plot_canvas import PlotArea, PlotCanvas
from .theme import VELOCITY, VELOCITY_SOFT


class VelocityCanvas(PlotCanvas):
    """Speed |v| of the stone as a function of time."""

    def __init__(self) -> None:
        super().__init__("Скорость", "t, с", "|v|, м/с")
        self._result: FlightResult | None = None

    def set_result(self, result: FlightResult) -> None:
        self._result = result
        self.set_data(result.times, result.speed)

    def _limits(self) -> tuple[tuple[float, float], tuple[float, float]]:
        if self._result is None:
            return super()._limits()
        speed = self._result.speed
        return (
            (0.0, max(float(self._x.max()) * 1.04, 0.5)),
            (0.0, max(float(speed.max()) * 1.15, 1.0)),
        )

    def _draw_series(self, painter: QPainter, area: PlotArea) -> None:
        if self._result is None:
            return
        t, v = self._result.times, self._result.speed

        fill = QPainterPath(QPointF(area.px(t[0]), area.rect.bottom()))
        for ti, vi in zip(t, v, strict=True):
            fill.lineTo(area.px(ti), area.py(vi))
        fill.lineTo(area.px(t[-1]), area.rect.bottom())
        fill.closeSubpath()
        gradient = QLinearGradient(0, area.rect.bottom(), 0, area.rect.top())
        gradient.setColorAt(0.0, QColor(VELOCITY_SOFT))
        transparent = QColor(VELOCITY)
        transparent.setAlpha(0)
        gradient.setColorAt(1.0, transparent)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.drawPath(fill)

        path = QPainterPath(QPointF(area.px(t[0]), area.py(v[0])))
        for ti, vi in zip(t[1:], v[1:], strict=True):
            path.lineTo(area.px(ti), area.py(vi))
        painter.setPen(QPen(QColor(VELOCITY), 2.2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

    def _hover_lines(self, index: int) -> list[str]:
        if self._result is None:
            return []
        return [
            f"t = {self._result.times[index]:.2f} с",
            f"|v| = {self._result.speed[index]:.1f} м/с",
        ]
