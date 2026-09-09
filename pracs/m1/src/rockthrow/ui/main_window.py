"""Main window: control panel, metric tiles, trajectory and velocity canvases."""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QVBoxLayout, QWidget

from ..physics import FlightResult, simulate_flight
from .canvases import TrajectoryCanvas, VelocityCanvas
from .controls import ControlsPanel
from .metrics import MetricTile

ANIMATION_SECONDS = 2.2
TICK_MS = 16


class MainWindow(QMainWindow):
    """Recomputes the flight on any parameter change; the launch animates it."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Полёт камня")
        self.resize(1280, 840)

        self._result: FlightResult | None = None
        self._animation_position = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._advance_flight)

        self._controls = ControlsPanel()
        self._controls.changed.connect(self._recalculate)
        self._controls.launched.connect(self._launch)

        self._flight_time_tile = MetricTile("Время полёта")
        self._distance_tile = MetricTile("Дальность")
        self._height_tile = MetricTile("Максимальная высота")
        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(12)
        for tile in (self._flight_time_tile, self._distance_tile, self._height_tile):
            metrics_row.addWidget(tile)
        metrics_row.addStretch()

        self._trajectory = TrajectoryCanvas()
        self._velocity = VelocityCanvas()
        self._velocity.setFixedHeight(230)

        results = QVBoxLayout()
        results.setSpacing(12)
        results.addLayout(metrics_row)
        results.addWidget(self._trajectory, stretch=1)
        results.addWidget(self._velocity)

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
        self._result = simulate_flight(
            self._controls.velocity(),
            self._controls.angle(),
            self._controls.drag_model(),
        )
        self._trajectory.set_result(self._result)
        self._velocity.set_result(self._result)
        self._flight_time_tile.set_value(f"{self._result.flight_time:.2f} с")
        self._distance_tile.set_value(f"{self._result.flight_distance:.1f} м")
        self._height_tile.set_value(f"{self._result.max_height:.2f} м")

    def _launch(self) -> None:
        if self._result is None:
            return
        self._animation_position = 0.0
        self._trajectory.set_flight_index(0)
        self._timer.start()

    def _advance_flight(self) -> None:
        if self._result is None:
            self._timer.stop()
            return
        frames = ANIMATION_SECONDS * 1000 / TICK_MS
        self._animation_position += self._result.times.size / frames
        last_index = self._result.times.size - 1
        if self._animation_position >= last_index:
            self._timer.stop()
        self._trajectory.set_flight_index(min(int(self._animation_position), last_index))
