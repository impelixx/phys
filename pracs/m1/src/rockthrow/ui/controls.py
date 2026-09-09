"""Launch parameter controls."""

from __future__ import annotations

import math

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ..physics import DragModel, LinearDrag, QuadraticDrag
from .theme import ACCENT, ACCENT_HOVER, ACCENT_PRESSED, BACKGROUND, BORDER, MUTED, PANEL

_SLIDER_STYLESHEET = f"""
QSlider::groove:horizontal {{
    height: 4px;
    background: {BORDER};
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {ACCENT};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
    background: {ACCENT};
}}
QSlider::handle:horizontal:hover {{ background: {ACCENT_HOVER}; }}
QSlider::handle:horizontal:pressed {{ background: {ACCENT_PRESSED}; }}
"""

_LAUNCH_STYLESHEET = f"""
QPushButton#launch {{
    background: {ACCENT};
    color: {BACKGROUND};
    font-size: 14px;
    font-weight: 600;
    border: none;
    border-radius: 8px;
    padding: 11px 12px;
}}
QPushButton#launch:hover {{ background: {ACCENT_HOVER}; }}
QPushButton#launch:pressed {{ background: {ACCENT_PRESSED}; }}
"""


class ParamSlider(QWidget):
    """Labeled float parameter: caption with live value above a slider."""

    value_changed = Signal(float)

    def __init__(
        self,
        title: str,
        minimum: float,
        maximum: float,
        value: float,
        step: float,
        unit: str,
        tooltip: str = "",
    ) -> None:
        super().__init__()
        self._minimum = minimum
        self._step = step
        self._decimals = max(0, -math.floor(math.log10(step)))
        self._unit = unit

        caption = QLabel(title)
        caption.setToolTip(tooltip)
        self._value_label = QLabel()
        caption_row = QHBoxLayout()
        caption_row.addWidget(caption)
        caption_row.addStretch()
        caption_row.addWidget(self._value_label)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, round((maximum - minimum) / step))
        self._slider.setValue(round((value - minimum) / step))
        self._slider.setStyleSheet(_SLIDER_STYLESHEET)
        self._slider.valueChanged.connect(self._on_slider_moved)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addLayout(caption_row)
        layout.addWidget(self._slider)

        self._render_value(self.value())

    def value(self) -> float:
        return self._minimum + self._slider.value() * self._step

    def _on_slider_moved(self) -> None:
        self._render_value(self.value())
        self.value_changed.emit(self.value())

    def _render_value(self, value: float) -> None:
        suffix = f" {self._unit}" if self._unit else ""
        self._value_label.setText(f"{value:.{self._decimals}f}{suffix}")


class ControlsPanel(QWidget):
    """Left panel: resistance model, launch parameters, launch button."""

    changed = Signal()
    launched = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setFixedWidth(300)
        self.setObjectName("panel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, on=True)
        self.setStyleSheet(
            f"QWidget#panel {{ background: {PANEL};"
            f" border: 1px solid {BORDER}; border-radius: 12px; }}"
        )

        title = QLabel("Параметры запуска")
        title.setStyleSheet("font-size: 15px; font-weight: 600;")

        self._model_combo = QComboBox()
        self._model_combo.addItems([LinearDrag.label(), QuadraticDrag.label()])
        self._model_combo.currentIndexChanged.connect(lambda _: self.changed.emit())

        self._velocity = ParamSlider(
            "Начальная скорость v₀",
            0.1,
            343.0,
            30.0,
            0.1,
            "м/с",
            tooltip="Ограничена скоростью звука в воздухе.",
        )
        self._angle = ParamSlider(
            "Угол броска α",
            0.01,
            90.0,
            30.0,
            0.01,
            "°",
            tooltip="Отсчитывается от горизонта.",
        )
        self._mass = ParamSlider(
            "Масса камня m",
            0.01,
            10.0,
            1.0,
            0.01,
            "кг",
            tooltip="От речной гальки до увесистого булыжника.",
        )
        self._rate = ParamSlider(
            "Коэффициент сопротивления k",
            0.0,
            2.0,
            0.5,
            0.01,
            "",
            tooltip="Делится на массу: линейная модель — 1/с, квадратичная — 1/м. "
            "Ноль отключает сопротивление.",
        )

        for slider in (self._velocity, self._angle, self._mass, self._rate):
            slider.value_changed.connect(lambda _: self.changed.emit())

        self._launch_button = QPushButton("Запустить полёт")
        self._launch_button.setObjectName("launch")
        self._launch_button.setStyleSheet(_LAUNCH_STYLESHEET)
        self._launch_button.setDefault(True)
        self._launch_button.clicked.connect(self.launched.emit)

        note = QLabel("g = 9.81 м/с² · бросок с уровня земли")
        note.setStyleSheet(f"color: {MUTED}; font-size: 11px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)
        layout.addWidget(title)
        layout.addWidget(self._model_combo)
        layout.addWidget(self._velocity)
        layout.addWidget(self._angle)
        layout.addWidget(self._mass)
        layout.addWidget(self._rate)
        layout.addStretch()
        layout.addWidget(self._launch_button)
        layout.addWidget(note)

    def drag_model(self) -> DragModel:
        """Build the selected resistance model for the current parameters."""
        ratio = self._rate.value() / self._mass.value()
        if self._model_combo.currentIndex() == 1:
            return QuadraticDrag(ratio)
        return LinearDrag(ratio)

    def velocity(self) -> float:
        return self._velocity.value()

    def angle(self) -> float:
        return self._angle.value()
