"""
QPainter plot canvas shared by the trajectory and velocity charts.

The base class owns the frame, grid, tick labels, title and the hover
crosshair; subclasses only draw their series into the plot area.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from PySide6.QtCore import QEvent, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from .theme import BORDER, CANVAS, GRID, MUTED, PANEL, TEXT


def nice_ticks(low: float, high: float, target: int = 5) -> list[float]:
    """Round tick positions roughly `target` in number, covering [low, high]."""
    span = high - low
    if span <= 0:
        return [low]
    raw_step = span / target
    power = 10.0 ** math.floor(math.log10(raw_step))
    step = next(
        multiplier * power
        for multiplier in (1.0, 2.0, 2.5, 5.0, 10.0)
        if raw_step <= multiplier * power
    )
    first = math.ceil(low / step) * step
    return [first + index * step for index in range(math.floor((high - first) / step) + 1)]


@dataclass(frozen=True, slots=True)
class PlotArea:
    """Plot rectangle plus data limits, with data-to-pixel mapping."""

    rect: QRectF
    x_limits: tuple[float, float]
    y_limits: tuple[float, float]

    def px(self, x: float) -> float:
        low, high = self.x_limits
        return self.rect.left() + (x - low) / (high - low) * self.rect.width()

    def py(self, y: float) -> float:
        low, high = self.y_limits
        return self.rect.bottom() - (y - low) / (high - low) * self.rect.height()


class PlotCanvas(QWidget):
    """Dark plot panel with grid, axis labels and a hover readout."""

    MARGIN_LEFT = 58.0
    MARGIN_RIGHT = 18.0
    MARGIN_TOP = 36.0
    MARGIN_BOTTOM = 40.0

    def __init__(self, title: str, x_label: str, y_label: str) -> None:
        super().__init__()
        self.setMinimumHeight(200)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._title = title
        self._x_label = x_label
        self._y_label = y_label
        self._x = np.asarray([])
        self._y = np.asarray([])
        self._hover_index: int | None = None

    def set_data(self, x: np.ndarray, y: np.ndarray) -> None:
        self._x = np.asarray(x, dtype=float)
        self._y = np.asarray(y, dtype=float)
        self._hover_index = None
        self.update()

    def _limits(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """Data limits of both axes; subclasses pad them."""
        if self._x.size < 2:
            return (0.0, 1.0), (0.0, 1.0)
        return (0.0, float(self._x.max())), (0.0, float(self._y.max()))

    def _draw_series(self, painter: QPainter, area: PlotArea) -> None:
        """Draw the series body inside the plot rectangle."""

    def _hover_lines(self, _index: int) -> list[str]:
        """Readout text lines for the sample under the cursor."""
        return []

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802, ARG002 (Qt naming)
        painter = QPainter(self)
        painter.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing
        )
        frame = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.setPen(QPen(QColor(BORDER), 1))
        painter.setBrush(QColor(CANVAS))
        painter.drawRoundedRect(frame, 10, 10)

        if self._x.size < 2:
            return

        (x_low, x_high), (y_low, y_high) = self._limits()
        plot = PlotArea(
            frame.adjusted(
                self.MARGIN_LEFT, self.MARGIN_TOP, -self.MARGIN_RIGHT, -self.MARGIN_BOTTOM
            ),
            (x_low, x_high),
            (y_low, y_high),
        )

        painter.save()
        painter.setClipRect(plot.rect.adjusted(-1, -1, 1, 1))
        self._draw_grid(painter, plot)
        self._draw_series(painter, plot)
        painter.restore()

        self._draw_axes(painter, plot)
        self._draw_hover(painter, plot)

    def _draw_grid(self, painter: QPainter, area: PlotArea) -> None:
        painter.setPen(QPen(QColor(GRID), 1))
        for tick in nice_ticks(*area.x_limits):
            x = area.px(tick)
            painter.drawLine(QPointF(x, area.rect.top()), QPointF(x, area.rect.bottom()))
        for tick in nice_ticks(*area.y_limits):
            y = area.py(tick)
            painter.drawLine(QPointF(area.rect.left(), y), QPointF(area.rect.right(), y))

    def _draw_axes(self, painter: QPainter, area: PlotArea) -> None:
        painter.setPen(QColor(MUTED))
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)

        for tick in nice_ticks(*area.x_limits):
            painter.drawText(QPointF(area.px(tick) - 8, area.rect.bottom() + 16), f"{tick:g}")
        painter.drawText(QPointF(area.rect.right() - 24, area.rect.bottom() + 32), self._x_label)

        for tick in nice_ticks(*area.y_limits):
            painter.drawText(QPointF(area.rect.left() - 40, area.py(tick) + 4), f"{tick:g}")
        painter.drawText(QPointF(self.MARGIN_LEFT, area.rect.top() - 8), self._y_label)

        painter.setPen(QColor(TEXT))
        font.setPointSize(11)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.drawText(QPointF(self.MARGIN_LEFT, area.rect.top() - 24), self._title)

    def _draw_hover(self, painter: QPainter, area: PlotArea) -> None:
        if self._hover_index is None or self._x.size < 2:
            return
        index = min(self._hover_index, self._x.size - 1)
        position = QPointF(area.px(self._x[index]), area.py(self._y[index]))

        pen = QPen(QColor(MUTED), 1, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawLine(
            QPointF(position.x(), area.rect.top()), QPointF(position.x(), area.rect.bottom())
        )
        painter.setPen(QPen(QColor(TEXT), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(position, 3.5, 3.5)

        lines = self._hover_lines(index)
        if not lines:
            return
        line_height = 14.0
        box_width = max(len(line) for line in lines) * 6.2 + 16
        box_height = len(lines) * line_height + 10
        box = QRectF(
            area.rect.right() - box_width,
            area.rect.top() + 8,
            box_width,
            box_height,
        )
        painter.setPen(QPen(QColor(BORDER), 1))
        painter.setBrush(QColor(PANEL))
        painter.drawRoundedRect(box, 6, 6)
        painter.setPen(QColor(TEXT))
        font = painter.font()
        font.setWeight(QFont.Weight.Normal)
        painter.setFont(font)
        for offset, line in enumerate(lines):
            painter.drawText(QPointF(box.left() + 8, box.top() + 15 + offset * line_height), line)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802 (Qt naming)
        if self._x.size < 2:
            return
        (x_low, x_high), _ = self._limits()
        width = self.width() - self.MARGIN_LEFT - self.MARGIN_RIGHT
        x_data = x_low + (event.position().x() - self.MARGIN_LEFT) / width * (x_high - x_low)
        self._hover_index = int(np.argmin(np.abs(self._x - x_data)))
        self.update()

    def leaveEvent(self, event: QEvent) -> None:  # noqa: N802, ARG002 (Qt naming)
        self._hover_index = None
        self.update()
