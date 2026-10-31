"""Pendulum parameter controls."""

from __future__ import annotations

import math

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ..physics import Rod
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
    """Left panel: rod and friction parameters, simulation span, launch button."""

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

        title = QLabel("Параметры маятника")
        title.setStyleSheet("font-size: 15px; font-weight: 600;")

        self._mass = ParamSlider(
            "Масса стержня m",
            0.1,
            100.0,
            1.0,
            0.1,
            "кг",
            tooltip="Меньше 0.1 кг — нереалистично лёгкий стержень; "
            "больше 100 кг — далеко за пределами лабораторных масштабов.",
        )
        self._length = ParamSlider(
            "Длина стержня L",
            0.1,
            10.0,
            1.0,
            0.01,
            "м",
            tooltip="T ∼ √L: от ~0.5 с у 10-сантиметрового стержня до ~5 с у 10-метрового.",
        )
        self._amplitude = ParamSlider(
            "Начальный угол φ₀",
            0.1,
            179.0,
            30.0,
            0.1,
            "°",
            tooltip="Отсчитывается от вертикали; маятник отпускают без начальной скорости. "
            "sin φ не линеаризуется, так что большие углы тоже корректны.",
        )
        self._friction = ParamSlider(
            "Коэффициент трения β",
            0.0,
            10.0,
            0.0,
            0.01,
            "Н·с/м²",
            tooltip="Вязкое сопротивление на единицу длины стержня, dF = −β ω r dr. "
            "Ноль — свободные колебания без трения.",
        )
        self._duration = ParamSlider(
            "Время моделирования",
            0.2,
            50.0,
            10.0,
            0.1,
            "с",
            tooltip="Хватает на несколько периодов даже у самого длинного стержня.",
        )

        for slider in (self._mass, self._length, self._amplitude, self._friction, self._duration):
            slider.value_changed.connect(lambda _: self.changed.emit())

        self._launch_button = QPushButton("Запустить маятник")
        self._launch_button.setObjectName("launch")
        self._launch_button.setStyleSheet(_LAUNCH_STYLESHEET)
        self._launch_button.setDefault(True)
        self._launch_button.clicked.connect(self.launched.emit)

        note = QLabel("g = 9.81 м/с² · стержень на оси через конец, I = mL²/3")
        note.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        note.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)
        layout.addWidget(title)
        layout.addWidget(self._mass)
        layout.addWidget(self._length)
        layout.addWidget(self._amplitude)
        layout.addWidget(self._friction)
        layout.addWidget(self._duration)
        layout.addStretch()
        layout.addWidget(self._launch_button)
        layout.addWidget(note)

    def rod(self) -> Rod:
        return Rod(
            mass=self._mass.value(),
            length=self._length.value(),
            friction=self._friction.value(),
        )

    def amplitude(self) -> float:
        return self._amplitude.value()

    def duration(self) -> float:
        return self._duration.value()
