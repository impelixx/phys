"""Result metric tiles."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from .theme import BORDER, MUTED, PANEL


class MetricTile(QFrame):
    """A rounded tile with a muted caption and a large value."""

    def __init__(self, title: str) -> None:
        super().__init__()
        self.setObjectName("metric")
        self.setStyleSheet(
            f"QFrame#metric {{ background: {PANEL}; border: 1px solid {BORDER};"
            f" border-radius: 10px; }}"
        )
        self._caption = QLabel(title)
        self._caption.setStyleSheet(f"color: {MUTED}; font-size: 11px; border: none;")
        self._value = QLabel("—")
        self._value.setStyleSheet("font-size: 24px; font-weight: 600; border: none;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(2)
        layout.addWidget(self._caption)
        layout.addWidget(self._value, alignment=Qt.AlignmentFlag.AlignLeft)

    def set_caption(self, text: str) -> None:
        self._caption.setText(text)

    def set_value(self, text: str) -> None:
        self._value.setText(text)
