# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "PySide6>=6.7",
#     "numpy>=1.26",
#     "matplotlib>=3.8",
#     "rich>=13.7",
# ]
# ///
"""
Графический интерфейс к обработке лабораторной работы
«Измерение скорости пули с помощью баллистического маятника».

Запуск:
    uv run bullet_speed_gui.py

Вся физика берётся из соседнего bullet_speed.py — здесь только окно.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("QtAgg")

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import (QColor, QDesktopServices, QFont, QKeySequence,
                           QShortcut)
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QFileDialog, QFrame, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton, QSizeGrip,
    QSizePolicy, QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

# --- подключаем расчётное ядро из соседнего файла --------------------------
_CORE_PATH = Path(__file__).resolve().parent / "bullet_speed.py"
_spec = importlib.util.spec_from_file_location("bullet_speed_core", _CORE_PATH)
core = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
sys.modules["bullet_speed_core"] = core   # нужно dataclasses при exec_module
_spec.loader.exec_module(core)


# --------------------------------------------------------------------------
# Оформление
# --------------------------------------------------------------------------

BG = "#0f1218"       # фон окна
CARD = "#191d26"     # поверхность карточки
CARD2 = "#212734"    # поля ввода, шапки таблицы
LINE = "#2b3240"     # границы
ROW = "#1d222c"      # чередование строк таблицы
TEXT = "#e6e9ef"
MUTED = "#8b93a7"
ACCENT = "#6ea8fe"
MONO = '"SF Mono", "JetBrains Mono", Menlo, Consolas, monospace'

# шаг сетки отступов: 4 / 8 / 12 / 16 / 24

QSS = f"""
QWidget {{
    background: {BG};
    color: {TEXT};
    font-size: 13px;
}}
QLabel {{ background: transparent; }}
QLabel#h1 {{ font-size: 19px; font-weight: 700; letter-spacing: 0.2px; }}
QLabel#sub {{ color: {MUTED}; font-size: 12px; }}
QLabel#cardTitle {{
    font-size: 11px; font-weight: 700; color: {MUTED};
    letter-spacing: 1.2px;
}}
QLabel#groupTitle {{
    font-size: 11px; font-weight: 600; color: {MUTED}; letter-spacing: 0.8px;
}}
QLabel#fieldLabel {{ color: {MUTED}; font-size: 12px; }}
QLabel#unit {{ color: {MUTED}; font-size: 11px; }}
QLabel#hint {{ color: #6f7789; font-size: 11px; }}
QLabel#value {{ font-size: 24px; font-weight: 700; font-family: {MONO}; }}
QLabel#status {{ color: #6f7789; font-size: 11px; }}
QFrame#card, QFrame#result {{
    background: {CARD};
    border: 1px solid {LINE};
    border-radius: 0px;
}}
QFrame#sep {{ background: {LINE}; max-height: 1px; border: none; }}
QLineEdit {{
    background: {CARD2};
    border: 1px solid {LINE};
    border-radius: 0px;
    padding: 6px 8px;
    font-family: {MONO};
    selection-background-color: {ACCENT};
    selection-color: #0b1020;
}}
QLineEdit#title {{ font-family: inherit; }}
QLineEdit:focus {{ border: 1px solid {ACCENT}; }}
QPushButton {{
    background: transparent;
    border: 1px solid {LINE};
    border-radius: 0px;
    padding: 7px 14px;
    color: {TEXT};
}}
QPushButton:hover {{ background: {CARD2}; border-color: #3c465c; }}
QPushButton:pressed {{ background: #171c25; }}
QPushButton#primary {{
    background: {ACCENT}; border: 1px solid {ACCENT}; color: #0b1020;
    font-weight: 600;
}}
QPushButton#primary:hover {{ background: #8bbaff; border-color: #8bbaff; }}
QWidget#header {{ background: {CARD}; border-bottom: 1px solid {LINE}; }}
QPushButton#winbtn, QPushButton#winclose {{
    background: transparent; border: none; color: {MUTED};
    padding: 4px 12px; font-size: 14px;
}}
QPushButton#winbtn:hover {{ background: {CARD2}; color: {TEXT}; }}
QPushButton#winclose:hover {{ background: #b23b3b; color: #ffffff; }}
QTableWidget {{
    background: {CARD};
    alternate-background-color: {ROW};
    border: 1px solid {LINE};
    border-radius: 0px;
    gridline-color: transparent;
    selection-background-color: #27354f;
    selection-color: {TEXT};
    font-family: {MONO};
}}
QTableWidget QLineEdit {{
    background: #0d1017;
    border: 1px solid {ACCENT};
    border-radius: 0px;
    padding: 0px 6px;
    margin: 0px;
    color: {TEXT};
}}
QHeaderView {{ background: {CARD2}; }}
QHeaderView::section {{
    background: {CARD2};
    color: {MUTED};
    border: none;
    border-bottom: 1px solid {LINE};
    padding: 7px 10px;
    font-family: inherit;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.4px;
}}
QHeaderView::section:first {{ padding-left: 12px; }}
QTableCornerButton::section {{ background: {CARD2}; border: none; }}
QTableWidget::item {{ padding: 4px 10px; }}
QSplitter::handle {{ background: transparent; height: 12px; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: #333b4a; border-radius: 0px; }}
QScrollBar::handle:vertical:hover {{ background: #414b5e; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
"""


class HeaderBar(QWidget):
    """Своя шапка окна: перетаскивание и разворот двойным щелчком."""

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.window().windowHandle()
            if handle is not None:
                handle.startSystemMove()
                return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        win = self.window()
        win.showNormal() if win.isMaximized() else win.showMaximized()


def card(title: str | None = None) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("card")
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(16, 14, 16, 16)
    lay.setSpacing(8)
    if title:
        lbl = QLabel(title.upper())
        lbl.setObjectName("cardTitle")
        lay.addWidget(lbl)
    return frame, lay


class NumberField(QWidget):
    """Поле ввода числа с подписью и единицей измерения."""

    def __init__(self, label: str, value: float, unit: str = "", parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.label = QLabel(label)
        self.label.setObjectName("fieldLabel")
        self.label.setMinimumWidth(150)
        self.edit = QLineEdit(f"{value:g}")
        self.edit.setMinimumWidth(96)
        self.edit.setMaximumWidth(104)
        self.edit.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.unit = QLabel(unit)
        self.unit.setObjectName("unit")
        self.unit.setMinimumWidth(34)
        lay.addWidget(self.label, 1)
        lay.addWidget(self.edit)
        lay.addWidget(self.unit)

    def value(self, default: float = 0.0) -> float:
        try:
            return float(self.edit.text().replace(",", ".").strip())
        except ValueError:
            return default

    def set_value(self, v: float) -> None:
        self.edit.setText(f"{v:g}")


class ShotTable(QTableWidget):
    """Таблица выстрелов с поддержкой вставки из буфера обмена."""

    HEADERS = ["Серия", "m, г", "d, мм", "u, м/с", "Δu, м/с"]

    def __init__(self, on_change):
        super().__init__(0, len(self.HEADERS))
        self.on_change = on_change
        self.setHorizontalHeaderLabels(self.HEADERS)
        self.verticalHeader().setDefaultSectionSize(30)
        self.verticalHeader().setVisible(True)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        hdr = self.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setMinimumSectionSize(96)
        for c in (1, 2, 3, 4):
            hdr.setSectionResizeMode(c, QHeaderView.ResizeMode.Fixed)
            self.setColumnWidth(c, 118)
        hdr.setDefaultAlignment(Qt.AlignmentFlag.AlignRight
                                | Qt.AlignmentFlag.AlignVCenter)
        self.horizontalHeaderItem(0).setTextAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.verticalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.cellChanged.connect(lambda *_: self.on_change())
        QShortcut(QKeySequence.StandardKey.Paste, self, self.paste_clipboard)

    def add_shot(self, series: str = "основная", m_g: float | str = "",
                 d_mm: float | str = "") -> None:
        self._append_row(series, m_g, d_mm)
        self.on_change()

    def _append_row(self, series: str = "основная", m_g: float | str = "",
                    d_mm: float | str = "") -> None:
        row = self.rowCount()
        blocked = self.signalsBlocked()
        self.blockSignals(True)
        self.insertRow(row)
        for col, val in enumerate((series, m_g, d_mm)):
            text = f"{val:g}" if isinstance(val, float) else str(val)
            item = QTableWidgetItem(text)
            if col:
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight
                                      | Qt.AlignmentFlag.AlignVCenter)
            self.setItem(row, col, item)
        for col in (3, 4):
            item = QTableWidgetItem("—")
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row, col, item)
        self.blockSignals(blocked)

    def remove_selected(self) -> None:
        rows = sorted({i.row() for i in self.selectedIndexes()}, reverse=True)
        if not rows and self.rowCount():
            rows = [self.rowCount() - 1]
        self.blockSignals(True)
        for r in rows:
            self.removeRow(r)
        self.blockSignals(False)
        self.on_change()

    def clear_shots(self) -> None:
        self.blockSignals(True)
        self.setRowCount(0)
        self.blockSignals(False)
        self.on_change()

    def paste_clipboard(self) -> None:
        """Вставка строк вида «0.5121 10.4» (пробел/таб/точка с запятой)."""
        text = QApplication.clipboard().text()
        series = "основная"
        cur = self.currentRow()
        if cur >= 0 and self.item(cur, 0):
            series = self.item(cur, 0).text() or series
        added = 0
        self.blockSignals(True)
        for line in text.splitlines():
            parts = line.replace(",", ".").replace(";", " ").replace("\t", " ").split()
            if len(parts) < 2:
                continue
            try:
                m_g, d_mm = float(parts[-2]), float(parts[-1])
            except ValueError:
                continue
            self._append_row(series, m_g, d_mm)
            added += 1
        self.blockSignals(False)
        if added:
            self.on_change()

    def cell(self, row: int, col: int) -> str:
        item = self.item(row, col)
        return item.text().strip() if item else ""

    def read_shots(self) -> list[core.Shot]:
        shots: list[core.Shot] = []
        for row in range(self.rowCount()):
            try:
                m_g = float(self.cell(row, 1).replace(",", "."))
                d_mm = float(self.cell(row, 2).replace(",", "."))
            except ValueError:
                continue
            if m_g <= 0 or d_mm <= 0:
                continue
            series = self.cell(row, 0) or "основная"
            shots.append(core.Shot(m_g=m_g, d_mm=d_mm, series=series))
        return shots

    def show_computed(self, results: list) -> None:
        """Проставляет вычисленные u и Δu напротив корректных строк."""
        self.blockSignals(True)
        idx = 0
        for row in range(self.rowCount()):
            ok = True
            try:
                m_g = float(self.cell(row, 1).replace(",", "."))
                d_mm = float(self.cell(row, 2).replace(",", "."))
                ok = m_g > 0 and d_mm > 0
            except ValueError:
                ok = False
            u_text, e_text = "—", "—"
            if ok and idx < len(results):
                r = results[idx]
                u_text, e_text = f"{r.u:.1f}", f"±{r.du_syst:.1f}"
                idx += 1
            for col, text in ((3, u_text), (4, e_text)):
                item = self.item(row, col)
                fresh = item is None
                if fresh:
                    item = QTableWidgetItem()
                item.setText(text)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight
                                      | Qt.AlignmentFlag.AlignVCenter)
                item.setForeground(QColor(TEXT if col == 3 else MUTED))
                if fresh:
                    self.setItem(row, col, item)
        self.blockSignals(False)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Скорость пули · баллистический маятник")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.resize(1240, 820)
        self.setStyleSheet(QSS)
        self._last_state: tuple | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())

        body = QHBoxLayout()
        body.setContentsMargins(20, 16, 20, 12)
        body.setSpacing(12)
        params_col = QVBoxLayout()
        params_col.setContentsMargins(0, 0, 0, 0)
        params_col.setSpacing(0)
        params_col.addWidget(self._build_params())
        params_col.addStretch(1)
        body.addLayout(params_col, 0)

        right = QSplitter(Qt.Orientation.Vertical)
        right.setChildrenCollapsible(False)
        right.addWidget(self._build_shots())
        right.addWidget(self._build_output())
        right.setSizes([330, 430])
        body.addWidget(right, 1)
        root.addLayout(body, 1)

        self.status = QLabel("")
        self.status.setObjectName("status")
        status_row = QHBoxLayout()
        status_row.setContentsMargins(20, 0, 8, 8)
        status_row.addWidget(self.status)
        status_row.addStretch(1)
        grip = QSizeGrip(self)
        grip.setFixedSize(16, 16)
        status_row.addWidget(grip, 0, Qt.AlignmentFlag.AlignBottom)
        root.addLayout(status_row)

        self.load_demo()

    # -- построение интерфейса --------------------------------------------

    def _build_header(self) -> QWidget:
        bar = HeaderBar()
        bar.setObjectName("header")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(18, 10, 10, 10)
        left = QVBoxLayout()
        left.setSpacing(2)
        title = QLabel("Скорость пули")
        title.setObjectName("h1")
        sub = QLabel("баллистический маятник  ·  u = (M/m)·(d/L)·√(gL),  g = 9,82 м/с²")
        sub.setObjectName("sub")
        left.addWidget(title)
        left.addWidget(sub)
        lay.addLayout(left)
        lay.addStretch(1)

        for text, slot, name in (
            ("Демо", self.load_demo, ""),
            ("Открыть…", self.open_json, ""),
            ("Сохранить данные", self.save_json, ""),
            ("Собрать PDF-отчёт", self.export_pdf, "primary"),
        ):
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            if name:
                btn.setObjectName(name)
            lay.addWidget(btn)

        lay.addSpacing(10)
        for glyph, slot, obj in (
            ("−", self.showMinimized, "winbtn"),
            ("□", self._toggle_max, "winbtn"),
            ("✕", self.close, "winclose"),
        ):
            b = QPushButton(glyph)
            b.setObjectName(obj)
            b.setFixedWidth(38)
            b.setCursor(Qt.CursorShape.ArrowCursor)
            b.clicked.connect(slot)
            lay.addWidget(b)
        return bar

    def _toggle_max(self) -> None:
        self.showNormal() if self.isMaximized() else self.showMaximized()

    def _build_params(self) -> QFrame:
        frame, lay = card("Параметры установки")
        frame.setFixedWidth(360)
        self.f_M = NumberField("Масса маятника M", 2900, "г")
        self.f_dM = NumberField("Погрешность ΔM", 1, "г")
        self.f_L = NumberField("Длина подвеса L", 52, "см")
        self.f_dL = NumberField("Погрешность ΔL", 0.2, "см")
        self.f_dm = NumberField("Погрешность весов Δm", 0.001, "г")
        self.f_dd = NumberField("Погрешность отсчёта Δd", 0.5, "мм")
        self.f_blank = NumberField("Холостой выстрел d₀", 0, "мм")
        self.f_g = NumberField("Ускорение g", core.G_DEFAULT, "м/с²")
        self.fields = [self.f_M, self.f_dM, self.f_L, self.f_dL,
                       self.f_dm, self.f_dd, self.f_blank, self.f_g]
        for f in self.fields:
            f.edit.textChanged.connect(self.recompute)

        groups = (
            ("Маятник", [self.f_M, self.f_dM, self.f_L, self.f_dL]),
            ("Измерение", [self.f_dm, self.f_dd, self.f_blank]),
            ("Константа", [self.f_g]),
        )
        for gi, (title, fields) in enumerate(groups):
            if gi:
                lay.addSpacing(10)
            label = QLabel(title.upper())
            label.setObjectName("groupTitle")
            lay.addWidget(label)
            for f in fields:
                lay.addWidget(f)

        hint = QLabel("d₀ вычитается из каждого отклонения — поправка на струю "
                      "воздуха из ствола.")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        lay.addSpacing(4)
        lay.addWidget(hint)

        lay.addSpacing(14)
        title = QLabel("НАЗВАНИЕ РАБОТЫ")
        title.setObjectName("cardTitle")
        lay.addWidget(title)
        self.f_title = QLineEdit("Измерение скорости пули (баллистический маятник)")
        self.f_title.setObjectName("title")
        lay.addWidget(self.f_title)
        return frame

    def _build_shots(self) -> QFrame:
        frame, lay = card("Выстрелы")
        self.table = ShotTable(self.recompute)
        lay.addWidget(self.table, 1)

        row = QHBoxLayout()
        for text, slot in (("+ выстрел", lambda: self.table.add_shot(self._series())),
                           ("− удалить", self.table.remove_selected),
                           ("Очистить", self.table.clear_shots)):
            b = QPushButton(text)
            b.clicked.connect(slot)
            row.addWidget(b)
        row.addStretch(1)
        hint = QLabel("Ctrl+V вставляет строки «масса пули  отклонение» из "
                      "лабораторного журнала")
        hint.setObjectName("hint")
        row.addWidget(hint)
        lay.addLayout(row)
        return frame

    def _build_output(self) -> QWidget:
        wrap = QWidget()
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        self.results_box = QHBoxLayout()
        self.results_box.setSpacing(12)
        holder = QWidget()
        holder.setLayout(self.results_box)
        holder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        lay.addWidget(holder)

        plot_card, plot_lay = card("Графики")
        self.figure = Figure(figsize=(8, 3.6), facecolor="#161a21")
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background: transparent;")
        plot_lay.addWidget(self.canvas, 1)
        lay.addWidget(plot_card, 1)
        return wrap

    # -- данные ------------------------------------------------------------

    def _series(self) -> str:
        row = self.table.currentRow()
        if row >= 0:
            return self.table.cell(row, 0) or "основная"
        return "основная"

    def build_setup(self) -> core.Setup:
        return core.Setup(
            M_g=self.f_M.value(1), L_cm=self.f_L.value(1),
            dM_g=self.f_dM.value(), dL_cm=self.f_dL.value(),
            dm_g=self.f_dm.value(), dd_mm=self.f_dd.value(),
            g=self.f_g.value(core.G_DEFAULT), d_blank_mm=self.f_blank.value(),
            title=self.f_title.text() or "Измерение скорости пули",
            shots=self.table.read_shots(),
        )

    def load_setup(self, setup: core.Setup) -> None:
        self.f_M.set_value(setup.M_g)
        self.f_dM.set_value(setup.dM_g)
        self.f_L.set_value(setup.L_cm)
        self.f_dL.set_value(setup.dL_cm)
        self.f_dm.set_value(setup.dm_g)
        self.f_dd.set_value(setup.dd_mm)
        self.f_g.set_value(setup.g)
        self.f_blank.set_value(setup.d_blank_mm)
        self.f_title.setText(setup.title)
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        self.table.blockSignals(False)
        for s in setup.shots:
            self.table.add_shot(s.series, s.m_g, s.d_mm)
        self.recompute()

    def load_demo(self) -> None:
        self.load_setup(core.DEMO)
        self.status.setText("Загружены демонстрационные данные — замените своими.")

    # -- расчёт ------------------------------------------------------------

    def recompute(self) -> None:
        setup = self.build_setup()
        if not setup.shots or setup.M_g <= 0 or setup.L_cm <= 0:
            self.table.show_computed([])
            self._render_results([], warn="Заполните параметры установки и выстрелы")
            return
        results = core.analyse(setup)
        by_series: dict[str, list] = {}
        for r in results:
            by_series.setdefault(r.shot.series, []).append(r)
        stats = [core.series_stats(name, rs) for name, rs in by_series.items()]

        self.table.show_computed(results)
        self._render_results(stats)
        core.build_plot_figure(by_series, stats, setup, dark=True, fig=self.figure)
        self.figure.tight_layout()
        self.canvas.draw_idle()
        self.status.setText(
            f"Выстрелов: {len(results)} · серий: {len(stats)} · "
            f"пересчитано {datetime.now():%H:%M:%S}")

    def _render_results(self, stats: list, warn: str | None = None) -> None:
        while self.results_box.count():
            item = self.results_box.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        if warn:
            lbl = QLabel(warn)
            lbl.setObjectName("sub")
            self.results_box.addWidget(lbl)
            return
        for i, st in enumerate(stats):
            color = core.SERIES_COLORS_DARK[i % len(core.SERIES_COLORS_DARK)]
            frame = QFrame()
            frame.setObjectName("result")
            frame.setMinimumWidth(330)
            frame.setStyleSheet(
                f"QFrame#result {{ border-left: 3px solid {color}; }}")
            lay = QVBoxLayout(frame)
            lay.setContentsMargins(16, 12, 16, 14)
            lay.setSpacing(6)
            name = QLabel(f"{st.name.upper()}   ·   n = {st.n}")
            name.setObjectName("cardTitle")
            value = QLabel(core.fmt_pm(st.mean, st.total))
            value.setObjectName("value")
            rel = 100 * st.total / st.mean if st.mean else float("nan")
            detail = QLabel(
                f"σ = {st.std:.1f}  ·  случайная {st.rand:.1f}  ·  "
                f"приборная {st.syst:.1f}  ·  δ = {rel:.1f} %   (P = 0.95)")
            detail.setObjectName("sub")
            lay.addWidget(name)
            lay.addWidget(value)
            lay.addWidget(detail)
            self.results_box.addWidget(frame)
        for c in core.compare_pairs(stats):
            frame = QFrame()
            frame.setObjectName("result")
            frame.setMinimumWidth(260)
            frame.setStyleSheet(
                f"QFrame#result {{ border-left: 3px solid {MUTED}; }}")
            lay = QVBoxLayout(frame)
            lay.setContentsMargins(16, 12, 16, 14)
            lay.setSpacing(6)
            head = QLabel(f"{c.a} ↔ {c.b}".upper())
            head.setObjectName("cardTitle")
            body = QLabel(f"разность средних {c.diff:.1f} м/с   ·   "
                          f"Δ/σ = {c.ratio:.2f}\n"
                          f"{c.verdict}")
            lay.addWidget(head)
            lay.addWidget(body)
            self.results_box.addWidget(frame)
        self.results_box.addStretch(1)

    # -- файлы -------------------------------------------------------------

    def _default_dir(self) -> Path:
        d = Path(__file__).resolve().parent / "results"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def open_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Открыть данные", str(self._default_dir()), "JSON (*.json)")
        if not path:
            return
        try:
            self.load_setup(core.load_data(Path(path)))
            self.status.setText(f"Загружено: {path}")
        except Exception as exc:
            QMessageBox.warning(self, "Не удалось открыть", str(exc))

    def save_json(self) -> None:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить данные",
            str(self._default_dir() / f"data-{stamp}.json"), "JSON (*.json)")
        if not path:
            return
        core.save_data(self.build_setup(), Path(path))
        self.status.setText(f"Данные сохранены: {path}")

    def export_pdf(self) -> None:
        setup = self.build_setup()
        if not setup.shots:
            QMessageBox.information(self, "Нет данных",
                                    "Добавьте хотя бы один выстрел.")
            return
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить отчёт",
            str(self._default_dir() / f"report-{stamp}.pdf"), "PDF (*.pdf)")
        if not path:
            return
        try:
            results = core.analyse(setup)
            by_series: dict[str, list] = {}
            for r in results:
                by_series.setdefault(r.shot.series, []).append(r)
            stats = [core.series_stats(n, rs) for n, rs in by_series.items()]
            core.export_pdf(setup, results, stats, Path(path))
            core.save_data(setup, Path(path).with_suffix(".json"))
        except Exception as exc:
            QMessageBox.warning(self, "Не удалось собрать PDF", str(exc))
            return
        self.status.setText(f"Отчёт готов: {path}")
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))


def main() -> int:
    selftest = "--selftest" in sys.argv
    if selftest:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication(sys.argv[:1])
    app.setApplicationName("Скорость пули")
    win = MainWindow()
    win.show()
    if selftest:
        outdir = Path(os.environ.get("SELFTEST_OUT", "/tmp"))
        out = outdir / "selftest.pdf"

        # живой пересчёт: правка ячейки меняет колонку u
        before = win.table.item(0, 3).text()
        win.table.item(0, 2).setText("12")
        app.processEvents()
        after = win.table.item(0, 3).text()
        assert before != after, "живой пересчёт не сработал"
        win.table.item(0, 2).setText("10.4")

        # вставка из буфера обмена
        rows = win.table.rowCount()
        QApplication.clipboard().setText("0.5100 9.9\n0.5110 10.1")
        win.table.paste_clipboard()
        app.processEvents()
        assert win.table.rowCount() == rows + 2, "вставка из буфера не сработала"
        win.table.setRowCount(rows)
        win.recompute()

        app.processEvents()
        shot = outdir / "selftest.png"
        win.grab().save(str(shot))
        print(f"screenshot -> {shot}")

        # как выглядит редактор ячейки
        win.table.setCurrentCell(0, 1)
        win.table.editItem(win.table.item(0, 1))
        app.processEvents()
        shot2 = outdir / "selftest-edit.png"
        win.table.grab().save(str(shot2))
        win.table.closePersistentEditor(win.table.item(0, 1))
        print(f"screenshot(edit) -> {shot2}")

        setup = win.build_setup()
        results = core.analyse(setup)
        by = {}
        for r in results:
            by.setdefault(r.shot.series, []).append(r)
        stats = [core.series_stats(n, rs) for n, rs in by.items()]
        core.export_pdf(setup, results, stats, out)
        print(f"selftest ok: {len(results)} выстрелов, PDF -> {out}")
        return 0
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
