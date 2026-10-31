"""Main window: control panel, metric tiles, table view and contact charts."""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QMainWindow, QVBoxLayout, QWidget

from ..physics import (
    CollisionResult,
    contact_duration,
    max_compression,
    simulate_collision,
)
from .canvases import ContactCanvas, EnergyCanvas, TableCanvas
from .controls import ControlsPanel
from .metrics import MetricTile

ANIMATION_SECONDS = 2.5
TICK_MS = 16


class MainWindow(QMainWindow):
    """Recomputes the impact on any parameter change; the launch animates the balls."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Бильярд на гладком столе")
        self.resize(1280, 840)

        self._result: CollisionResult | None = None
        self._animation_position = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._advance_balls)

        self._controls = ControlsPanel()
        self._controls.changed.connect(self._recalculate)
        self._controls.launched.connect(self._launch)

        self._speed1_tile = MetricTile("|v₁′| расчёт / теория, м/с")
        self._speed2_tile = MetricTile("|v₂′| расчёт / теория, м/с")
        self._angle_tile = MetricTile("Угол разлёта")
        self._duration_tile = MetricTile("Время контакта / теория")
        self._compression_tile = MetricTile("Макс. сжатие / теория")
        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(12)
        self._tiles = (
            self._speed1_tile,
            self._speed2_tile,
            self._angle_tile,
            self._duration_tile,
            self._compression_tile,
        )
        for tile in self._tiles:
            metrics_row.addWidget(tile)
        metrics_row.addStretch()

        self._table = TableCanvas()
        self._contact = ContactCanvas()
        self._energy = EnergyCanvas()

        charts = QGridLayout()
        charts.setSpacing(12)
        charts.addWidget(self._table, 0, 0, 2, 1)
        charts.addWidget(self._contact, 0, 1)
        charts.addWidget(self._energy, 1, 1)
        charts.setColumnStretch(0, 3)
        charts.setColumnStretch(1, 2)

        results = QVBoxLayout()
        results.setSpacing(12)
        results.addLayout(metrics_row)
        results.addLayout(charts, stretch=1)

        root = QHBoxLayout()
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)
        root.addWidget(self._controls)
        root.addLayout(results, stretch=1)
        central = QWidget()
        central.setLayout(root)
        self.setCentralWidget(central)

        self._recalculate()

    def _recalculate(self) -> None:
        self._timer.stop()
        setup = self._controls.setup()
        contact = self._controls.contact()
        try:
            self._result = simulate_collision(setup, contact)
        except ValueError as error:
            self._result = None
            self._show_failure(str(error))
            return

        self._table.set_result(self._result)
        self._contact.set_result(self._result)
        self._energy.set_result(self._result)

        first, second = setup.conservation_velocities()
        self._speed1_tile.set_value(
            f"{np.linalg.norm(self._result.velocity1_after):.3f} / {np.linalg.norm(first):.3f}"
        )
        if setup.wall:
            self._speed2_tile.set_value("—")
            self._angle_tile.set_caption("Угол отражения / падения")
            self._angle_tile.set_value(
                f"{self._reflection_angle():.2f}° / {self._incidence():.2f}°"
            )
        else:
            self._speed2_tile.set_value(
                f"{np.linalg.norm(self._result.velocity2_after):.3f} / {np.linalg.norm(second):.3f}"
            )
            angle = self._result.separation_angle
            self._angle_tile.set_caption("Угол разлёта")
            self._angle_tile.set_value("—" if angle is None else f"{angle:.2f}°")

        mass = setup.effective_mass
        speed = setup.approach_speed
        self._duration_tile.set_value(
            f"{self._result.contact_duration * 1000:.3f} / "
            f"{contact_duration(contact, mass, speed) * 1000:.3f} мс"
        )
        self._compression_tile.set_value(
            f"{self._result.max_compression * 1000:.3f} / "
            f"{max_compression(contact, mass, speed) * 1000:.3f} мм"
        )

    def _incidence(self) -> float:
        """Angle between the incoming velocity and the wall normal, degrees."""
        if self._result is None:
            return 0.0
        return math.degrees(math.asin(self._result.setup.impact))

    def _reflection_angle(self) -> float:
        """Angle between the outgoing velocity and the wall normal, degrees."""
        if self._result is None:
            return 0.0
        velocity = self._result.velocity1_after
        normal = self._result.setup.touch_normal
        cosine = float(np.dot(velocity, normal)) / float(np.linalg.norm(velocity))
        return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))

    def _show_failure(self, reason: str) -> None:
        messages = {
            "never": "Шары движутся одинаково и не встретятся",
            "too soft": "Контакт слишком мягкий: шары сплющились бы больше чем на R.\n"
            "Увеличьте жёсткость или уменьшите скорость.",
        }
        text = next((value for key, value in messages.items() if key in reason), reason)
        self._table.set_message(text)
        self._contact.set_result(None)
        self._energy.set_result(None)
        for tile in self._tiles:
            tile.set_value("—")

    def _launch(self) -> None:
        if self._result is None:
            return
        self._animation_position = 0.0
        self._show_position()
        self._timer.start()

    def _advance_balls(self) -> None:
        if self._result is None:
            self._timer.stop()
            return
        self._animation_position += TICK_MS / 1000 / ANIMATION_SECONDS
        if self._animation_position >= 1:
            self._animation_position = 1.0
            self._timer.stop()
        self._show_position()

    def _show_position(self) -> None:
        if self._result is None:
            return
        times = self._result.times
        moment = times[0] + self._animation_position * (times[-1] - times[0])
        index = min(int(times.searchsorted(moment)), times.size - 1)
        self._table.set_index(index)
