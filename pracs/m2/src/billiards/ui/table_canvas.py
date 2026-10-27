"""Table view: ball paths, the balls themselves and outgoing velocities, to scale."""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from ..physics import CollisionResult
from .theme import ACCENT, BACKGROUND, BALL2, BORDER, MUTED, TABLE, TEXT, THEORY

MARGIN = 28.0
ARROW_SECONDS_SHARE = 0.35


class TableCanvas(QWidget):
    """Top view of the table with equal axis scales; t = 0 is the first touch."""

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(320, 280)
        self._result: CollisionResult | None = None
        self._message = ""
        self._index: int | None = None

    def set_result(self, result: CollisionResult) -> None:
        self._result = result
        self._message = ""
        self._index = None
        self.update()

    def set_message(self, message: str) -> None:
        self._result = None
        self._message = message
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
        painter.setBrush(QColor(TABLE))
        painter.drawRoundedRect(frame, 10, 10)

        font = painter.font()
        font.setPointSize(11)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(QColor(TEXT))
        painter.drawText(QPointF(18, 24), "Стол (вид сверху)")
        font.setPointSize(10)
        font.setWeight(QFont.Weight.Normal)
        painter.setFont(font)

        if self._result is None:
            painter.setPen(QColor(MUTED))
            painter.drawText(frame, Qt.AlignmentFlag.AlignCenter, self._message)
            return

        result = self._result
        radius = result.setup.radius
        setup = result.setup
        first, second = setup.conservation_velocities()
        last = result.times.size - 1
        arrow_time = ARROW_SECONDS_SHARE * (result.times[-1] - result.contact_duration)
        arrows = [
            (result.position1[last], result.velocity1_after * arrow_time, first * arrow_time),
        ]
        bodies = [(result.position1, ACCENT)]
        if not setup.wall:
            arrows.append(
                (result.position2[last], result.velocity2_after * arrow_time, second * arrow_time)
            )
            bodies.append((result.position2, BALL2))
        tips = [
            start + shift for start, simulated, theory in arrows for shift in (simulated, theory)
        ]
        points = np.concatenate((result.position1, result.position2, tips))
        low = points.min(axis=0) - radius
        high = points.max(axis=0) + radius
        area = frame.adjusted(MARGIN, MARGIN + 16, -MARGIN, -MARGIN - 18)
        scale = min(area.width() / (high[0] - low[0]), area.height() / (high[1] - low[1]))
        centre = (low + high) / 2

        def to_screen(point: np.ndarray) -> QPointF:
            return QPointF(
                area.center().x() + (point[0] - centre[0]) * scale,
                area.center().y() - (point[1] - centre[1]) * scale,
            )

        touch = int(result.times.searchsorted(0.0))
        if setup.wall:
            self._draw_wall(painter, setup.touch_normal, to_screen, area)
        for positions, color in bodies:
            self._draw_path(painter, positions[: touch + 1], color, to_screen, dashed=True)
            self._draw_path(painter, positions[touch:], color, to_screen, dashed=False)

        # Ghost balls at the first touch, line of centres between them.
        ghost_pen = QPen(QColor(MUTED), 1, Qt.PenStyle.DotLine)
        painter.setPen(ghost_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for positions, _ in bodies:
            painter.drawEllipse(to_screen(positions[touch]), radius * scale, radius * scale)
        painter.drawLine(to_screen(result.position1[touch]), to_screen(result.position2[touch]))

        index = last if self._index is None else min(self._index, last)
        for positions, color in bodies:
            painter.setPen(QPen(QColor(BACKGROUND), 1.4))
            painter.setBrush(QColor(color))
            painter.drawEllipse(to_screen(positions[index]), radius * scale, radius * scale)

        for (start, simulated, theory), (_, color) in zip(arrows, bodies, strict=True):
            tail = to_screen(start)
            self._draw_arrow(painter, tail, to_screen(start + theory), THEORY, dashed=True)
            self._draw_arrow(painter, tail, to_screen(start + simulated), color, dashed=False)

        painter.setPen(QColor(MUTED))
        painter.drawText(
            QPointF(18, frame.bottom() - 12),
            f"t = {result.times[index] * 1000:+.1f} мс   - - до удара, — после;"
            "  стрелки: расчёт и теория (пунктир)",
        )

    @staticmethod
    def _draw_wall(
        painter: QPainter,
        normal: np.ndarray,
        to_screen,  # noqa: ANN001 (local mapping closure)
        clip: QRectF,
    ) -> None:
        """The wall plane through the origin, hatched on its far side."""
        origin = to_screen(np.zeros(2))
        tangent = to_screen(np.array([-normal[1], normal[0]]))
        inward = to_screen(-normal)
        along = QPointF(tangent.x() - origin.x(), tangent.y() - origin.y())
        behind = QPointF(inward.x() - origin.x(), inward.y() - origin.y())
        along_length = math.hypot(along.x(), along.y())
        behind_length = math.hypot(behind.x(), behind.y())
        if along_length == 0 or behind_length == 0:
            return
        along /= along_length
        behind /= behind_length
        reach = clip.width() + clip.height()
        painter.save()
        painter.setClipRect(clip)
        painter.setPen(QPen(QColor(TEXT), 2.4))
        painter.drawLine(origin - along * reach, origin + along * reach)
        painter.setPen(QPen(QColor(MUTED), 1))
        for step in range(-60, 61):
            foot = origin + along * (step * 14.0)
            painter.drawLine(foot, foot + behind * 10 + along * 6)
        painter.restore()

    @staticmethod
    def _draw_path(
        painter: QPainter,
        positions: np.ndarray,
        color: str,
        to_screen,  # noqa: ANN001 (local mapping closure)
        *,
        dashed: bool,
    ) -> None:
        path = QPainterPath(to_screen(positions[0]))
        for point in positions[1:]:
            path.lineTo(to_screen(point))
        style = Qt.PenStyle.DashLine if dashed else Qt.PenStyle.SolidLine
        painter.setPen(QPen(QColor(color), 1.4, style))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

    @staticmethod
    def _draw_arrow(
        painter: QPainter, start: QPointF, end: QPointF, color: str, *, dashed: bool
    ) -> None:
        dx, dy = end.x() - start.x(), end.y() - start.y()
        length = math.hypot(dx, dy)
        if length < 2:
            return
        style = Qt.PenStyle.DashLine if dashed else Qt.PenStyle.SolidLine
        painter.setPen(QPen(QColor(color), 2.0, style))
        painter.drawLine(start, end)
        ux, uy = dx / length, dy / length
        head = 9.0
        painter.setPen(QPen(QColor(color), 2.0))
        for side in (1, -1):
            painter.drawLine(
                end,
                QPointF(
                    end.x() - head * (ux * 0.87 - side * uy * 0.5),
                    end.y() - head * (uy * 0.87 + side * ux * 0.5),
                ),
            )
