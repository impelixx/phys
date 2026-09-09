"""Trajectory chart: amber flight path, fading area, apex marker, animated stone."""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen

from ..physics import FlightResult
from .plot_canvas import PlotArea, PlotCanvas
from .theme import ACCENT, ACCENT_SOFT, BACKGROUND, MUTED, TEXT, VELOCITY

TRAIL_POINTS = 14


class TrajectoryCanvas(PlotCanvas):
    """Flight path over the ground line, with the flying stone on demand."""

    def __init__(self) -> None:
        super().__init__("Траектория полёта", "x, м", "y, м")
        self._result: FlightResult | None = None
        self._flight_index: int | None = None

    def set_result(self, result: FlightResult) -> None:
        self._result = result
        self._flight_index = None
        self.set_data(result.x, result.y)

    def set_flight_index(self, index: int) -> None:
        self._flight_index = index
        self.update()

    def _limits(self) -> tuple[tuple[float, float], tuple[float, float]]:
        if self._result is None:
            return super()._limits()
        x_high = max(self._result.flight_distance * 1.04, 1.0)
        y_high = max(self._result.max_height * 1.15, 0.5)
        return (0.0, x_high), (0.0, y_high)

    def _draw_series(self, painter: QPainter, area: PlotArea) -> None:
        if self._result is None:
            return
        x, y = self._result.x, self._result.y

        ground_y = area.py(0.0)
        painter.setPen(QPen(QColor(MUTED), 1, Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(area.rect.left(), ground_y), QPointF(area.rect.right(), ground_y))

        fill = QPainterPath(QPointF(area.px(x[0]), ground_y))
        for xi, yi in zip(x, y, strict=True):
            fill.lineTo(area.px(xi), area.py(yi))
        fill.lineTo(area.px(x[-1]), ground_y)
        fill.closeSubpath()
        gradient = QLinearGradient(0, ground_y, 0, area.rect.top())
        gradient.setColorAt(0.0, QColor(ACCENT_SOFT))
        transparent = QColor(ACCENT)
        transparent.setAlpha(0)
        gradient.setColorAt(1.0, transparent)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.drawPath(fill)

        path = QPainterPath(QPointF(area.px(x[0]), area.py(y[0])))
        for xi, yi in zip(x[1:], y[1:], strict=True):
            path.lineTo(area.px(xi), area.py(yi))
        painter.setPen(QPen(QColor(ACCENT), 2.4))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

        apex = self._result.apex_index
        apex_point = QPointF(area.px(x[apex]), area.py(y[apex]))
        painter.setPen(QPen(QColor(ACCENT), 1))
        painter.setBrush(QBrush(QColor(ACCENT)))
        painter.drawEllipse(apex_point, 3.5, 3.5)
        painter.setPen(QColor(MUTED))
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        painter.drawText(apex_point + QPointF(8, -7), f"h = {self._result.max_height:.1f} м")

        painter.setPen(QPen(QColor(MUTED), 1.4))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(area.px(0.0), ground_y), 3.5, 3.5)

        self._draw_stone(painter, area)

    def _draw_stone(self, painter: QPainter, area: PlotArea) -> None:
        """The stone in flight, its recent trail and current velocity vector."""
        if self._result is None or self._flight_index is None:
            return
        index = min(self._flight_index, self._result.x.size - 1)
        x, y = self._result.x, self._result.y

        trail_start = max(0, index - TRAIL_POINTS)
        painter.setPen(QPen(QColor(TEXT), 1.6))
        for i in range(trail_start, index):
            painter.drawLine(
                QPointF(area.px(x[i]), area.py(y[i])),
                QPointF(area.px(x[i + 1]), area.py(y[i + 1])),
            )

        point = QPointF(area.px(x[index]), area.py(y[index]))
        painter.setPen(QPen(QColor(BACKGROUND), 1.6))
        painter.setBrush(QBrush(QColor(ACCENT)))
        painter.drawEllipse(point, 5.5, 5.5)

        speed = self._result.speed[index]
        if speed > 0:
            unit_x = self._result.vx[index] / speed
            unit_y = self._result.vy[index] / speed
            length = 24.0
            tip = QPointF(point.x() + unit_x * length, point.y() - unit_y * length)
            painter.setPen(QPen(QColor(VELOCITY), 1.8))
            painter.drawLine(point, tip)
            painter.drawEllipse(tip, 1.6, 1.6)
            painter.setPen(QColor(VELOCITY))
            painter.drawText(tip + QPointF(6, -4), f"{speed:.0f} м/с")

    def _hover_lines(self, index: int) -> list[str]:
        if self._result is None:
            return []
        return [
            f"t = {self._result.times[index]:.2f} с",
            f"x = {self._result.x[index]:.1f} м",
            f"y = {self._result.y[index]:.1f} м",
            f"|v| = {self._result.speed[index]:.1f} м/с",
        ]
