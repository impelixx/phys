"""Main window: control panel, metric tiles, pendulum view and charts."""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QMainWindow, QVBoxLayout, QWidget

from ..physics import (
    SwingResult,
    damped_period,
    exact_period,
    simulate_swing,
    small_angle_period,
)
from .canvases import AngleCanvas, EnergyCanvas, PendulumCanvas, PeriodCanvas
from .controls import ControlsPanel
from .metrics import MetricTile

TICK_MS = 16


class MainWindow(QMainWindow):
    """Recomputes the swing on any parameter change; the launch animates it in real time."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Физический маятник")
        self.resize(1280, 840)

        self._result: SwingResult | None = None
        self._animation_time = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._advance_swing)

        self._controls = ControlsPanel()
        self._controls.changed.connect(self._recalculate)
        self._controls.launched.connect(self._launch)

        self._period_tile = MetricTile("Период (расчёт)")
        self._theory_tile = MetricTile("Период (теория)")
        self._small_tile = MetricTile("T₀ малых колебаний")
        self._energy_tile = MetricTile("Энергия")
        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(12)
        for tile in (self._period_tile, self._theory_tile, self._small_tile, self._energy_tile):
            metrics_row.addWidget(tile)
        metrics_row.addStretch()

        self._pendulum = PendulumCanvas()
        self._angle = AngleCanvas()
        self._energy = EnergyCanvas()
        self._period = PeriodCanvas()

        charts = QGridLayout()
        charts.setSpacing(12)
        charts.addWidget(self._pendulum, 0, 0)
        charts.addWidget(self._angle, 0, 1)
        charts.addWidget(self._period, 1, 0)
        charts.addWidget(self._energy, 1, 1)
        charts.setColumnStretch(0, 2)
        charts.setColumnStretch(1, 3)

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
        rod = self._controls.rod()
        amplitude = self._controls.amplitude()
        self._result = simulate_swing(rod, amplitude, self._controls.duration())

        self._pendulum.set_result(self._result)
        self._angle.set_result(self._result)
        self._energy.set_result(self._result)
        self._period.set_rod(rod, amplitude)

        period = self._result.period
        self._period_tile.set_value("—" if period is None else f"{period:.4f} с")
        self._small_tile.set_value(f"{small_angle_period(rod):.4f} с")
        if rod.friction == 0:
            self._theory_tile.set_value(f"{exact_period(rod, amplitude):.4f} с")
            self._energy_tile.set_value(f"ΔE/E₀ = {self._result.energy_drift:.1e}")
        else:
            theory = damped_period(rod)
            self._theory_tile.set_value(
                f"γ = {rod.damping_ratio:.2f} ≥ 1" if theory is None else f"{theory:.4f} с (лин.)"
            )
            energy = self._result.total_energy
            loss = 1 - energy[-1] / energy[0]
            self._energy_tile.set_value(f"потеряно {loss:.1%}")

    def _launch(self) -> None:
        if self._result is None:
            return
        self._animation_time = 0.0
        self._show_time()
        self._timer.start()

    def _advance_swing(self) -> None:
        if self._result is None:
            self._timer.stop()
            return
        self._animation_time += TICK_MS / 1000
        if self._animation_time >= self._result.times[-1]:
            self._animation_time = float(self._result.times[-1])
            self._timer.stop()
        self._show_time()

    def _show_time(self) -> None:
        if self._result is None:
            return
        index = int(self._result.times.searchsorted(self._animation_time))
        index = min(index, self._result.times.size - 1)
        self._pendulum.set_index(index)
        self._angle.set_cursor(index)
