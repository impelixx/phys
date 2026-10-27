"""Collision parameter controls."""

from __future__ import annotations

import math

import numpy as np
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

from ..physics import CollisionSetup, ContactModel, HertzContact, HookeContact
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
QSlider::sub-page:horizontal:disabled {{ background: {BORDER}; }}
QSlider::handle:horizontal:disabled {{ background: {MUTED}; }}
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


_SUPERSCRIPTS = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")


def scientific(value: float) -> str:
    """4.47·10⁸ style rendering for values spanning many decades."""
    exponent = math.floor(math.log10(value))
    mantissa = value / 10**exponent
    return f"{mantissa:.2f}·10{str(exponent).translate(_SUPERSCRIPTS)}"


class LogParamSlider(ParamSlider):
    """The same slider over lg of the value, for parameters spanning many decades."""

    def value(self) -> float:
        return 10 ** super().value()

    def set_unit(self, unit: str) -> None:
        self._unit = unit
        self._render_value(self.value())

    def _render_value(self, value: float) -> None:
        suffix = f" {self._unit}" if self._unit else ""
        self._value_label.setText(f"{scientific(value)}{suffix}")


class ControlsPanel(QWidget):
    """Left panel: target, contact law, balls, incoming motion, launch button."""

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

        title = QLabel("Параметры столкновения")
        title.setStyleSheet("font-size: 15px; font-weight: 600;")

        self._target_combo = QComboBox()
        self._target_combo.addItems(["Удар о второй шар", "Удар о неподвижную стенку"])
        self._target_combo.currentIndexChanged.connect(self._on_target_changed)

        self._model_combo = QComboBox()
        self._model_combo.addItems([HookeContact.label(), HertzContact.label()])
        self._model_combo.setCurrentIndex(1)
        self._model_combo.currentIndexChanged.connect(self._on_model_changed)

        self._stiffness = LogParamSlider(
            "Жёсткость контакта k",
            2.0,
            12.0,
            8.65,
            0.01,
            HertzContact.stiffness_unit(),
            tooltip="Логарифмическая шкала. Для настоящих бильярдных шаров по Герцу "
            "k ≈ 4.5·10⁸ Н/м³ᐟ². Слишком мягкий контакт (сжатие больше половины "
            "радиуса) отбрасывается — модель упругого шара там неприменима.",
        )
        self._mass1 = ParamSlider(
            "Масса шара 1, m₁",
            0.01,
            5.0,
            0.17,
            0.01,
            "кг",
            tooltip="Бильярдный шар — около 0.17 кг.",
        )
        self._mass2 = ParamSlider(
            "Масса шара 2, m₂",
            0.01,
            5.0,
            0.17,
            0.01,
            "кг",
            tooltip="Разные массы — разные правила разлёта.",
        )
        self._radius = ParamSlider(
            "Радиус шаров R",
            0.01,
            0.15,
            0.0286,
            0.0001,
            "м",
            tooltip="Общий для обоих шаров; стандартный шар пула — 28.6 мм.",
        )
        self._speed1 = ParamSlider(
            "Скорость шара 1, v₁",
            0.1,
            20.0,
            2.0,
            0.1,
            "м/с",
            tooltip="Шар 1 катится вдоль оси x. Сильный разбивающий удар — около 10 м/с.",
        )
        self._speed2 = ParamSlider(
            "Скорость шара 2, v₂",
            0.0,
            20.0,
            0.0,
            0.1,
            "м/с",
            tooltip="Ноль — шар 2 покоится.",
        )
        self._direction2 = ParamSlider(
            "Направление v₂",
            0.0,
            359.0,
            180.0,
            1.0,
            "°",
            tooltip="Угол от оси x против часовой стрелки; 180° — навстречу шару 1.",
        )
        self._impact = ParamSlider(
            "Прицельный параметр b / 2R",
            0.0,
            0.99,
            0.5,
            0.01,
            "",
            tooltip="Смещение линии относительного движения от центра в долях 2R: "
            "0 — лобовой удар, ближе к 1 — касательный. Для стенки — sin угла падения.",
        )

        sliders = (
            self._stiffness,
            self._mass1,
            self._mass2,
            self._radius,
            self._speed1,
            self._speed2,
            self._direction2,
            self._impact,
        )
        for slider in sliders:
            slider.value_changed.connect(lambda _: self.changed.emit())

        self._launch_button = QPushButton("Запустить шары")
        self._launch_button.setObjectName("launch")
        self._launch_button.setStyleSheet(_LAUNCH_STYLESHEET)
        self._launch_button.setDefault(True)
        self._launch_button.clicked.connect(self.launched.emit)

        note = QLabel("Гладкий стол и гладкие шары: ни трения, ни вращения")
        note.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        note.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(self._target_combo)
        layout.addWidget(self._model_combo)
        for slider in sliders:
            layout.addWidget(slider)
        layout.addStretch()
        layout.addWidget(self._launch_button)
        layout.addWidget(note)

    def _on_target_changed(self) -> None:
        for slider in (self._mass2, self._speed2, self._direction2):
            slider.setEnabled(not self.is_wall())
        self.changed.emit()

    def is_wall(self) -> bool:
        return self._target_combo.currentIndex() == 1

    def _on_model_changed(self) -> None:
        model = HertzContact if self._model_combo.currentIndex() == 1 else HookeContact
        self._stiffness.set_unit(model.stiffness_unit())
        self.changed.emit()

    def contact(self) -> ContactModel:
        """Build the selected contact law for the current stiffness."""
        if self._model_combo.currentIndex() == 1:
            return HertzContact(self._stiffness.value())
        return HookeContact(self._stiffness.value())

    def setup(self) -> CollisionSetup:
        direction = math.radians(self._direction2.value())
        speed2 = 0.0 if self.is_wall() else self._speed2.value()
        return CollisionSetup(
            mass1=self._mass1.value(),
            mass2=self._mass2.value(),
            radius=self._radius.value(),
            velocity1=np.array([self._speed1.value(), 0.0]),
            velocity2=speed2 * np.array([math.cos(direction), math.sin(direction)]),
            impact=self._impact.value(),
            wall=self.is_wall(),
        )
