# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "rich>=13.7",
#     "numpy>=1.26",
#     "matplotlib>=3.8",
# ]
# ///
"""
Обработка лабораторной работы «Измерение скорости пули с помощью
баллистического маятника».

Рабочая формула (методичка, ф-ла 5):

        u = (M / m) * (d / L) * sqrt(g * L)

    M — масса маятника, m — масса пули, d — горизонтальное отклонение
    маятника, L — длина подвеса, g = 9.82 м/с².

Запуск:
    uv run bullet_speed.py                 # интерактивный ввод
    uv run bullet_speed.py data.json       # пересчёт по сохранённым данным
    uv run bullet_speed.py --demo          # демонстрация на примере
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

import numpy as np
from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

console = Console()

G_DEFAULT = 9.82  # м/с², из справочных таблиц (методичка)

# Цвета серий: тёмная тема окна и печатный вариант отчёта
SERIES_COLORS_DARK = ["#6ea8fe", "#ffa26b", "#4ade9a", "#c99bff", "#ffd166"]
SERIES_COLORS_PRINT = ["#3b6fd4", "#e2701f", "#25a06a", "#8b53c9", "#c9a227"]

# Коэффициенты Стьюдента для доверительной вероятности 0.95
STUDENT_95 = {
    1: 12.71, 2: 4.30, 3: 3.18, 4: 2.78, 5: 2.57, 6: 2.45, 7: 2.36,
    8: 2.31, 9: 2.26, 10: 2.23, 11: 2.20, 12: 2.18, 13: 2.16, 14: 2.14,
    15: 2.13, 16: 2.12, 17: 2.11, 18: 2.10, 19: 2.09, 20: 2.09,
    25: 2.06, 30: 2.04, 40: 2.02, 60: 2.00,
}


def student_t(dof: int) -> float:
    """Коэффициент Стьюдента t(0.95, dof) с интерполяцией по таблице."""
    if dof <= 0:
        return float("nan")
    if dof in STUDENT_95:
        return STUDENT_95[dof]
    keys = sorted(STUDENT_95)
    if dof > keys[-1]:
        return 1.96
    lo = max(k for k in keys if k < dof)
    hi = min(k for k in keys if k > dof)
    w = (dof - lo) / (hi - lo)
    return STUDENT_95[lo] + w * (STUDENT_95[hi] - STUDENT_95[lo])


# --------------------------------------------------------------------------
# Модель данных
# --------------------------------------------------------------------------


@dataclass
class Shot:
    """Один выстрел: масса пули (г) и отклонение маятника (мм)."""

    m_g: float
    d_mm: float
    series: str = "основная"
    note: str = ""


@dataclass
class Setup:
    """Параметры установки и приборные погрешности."""

    M_g: float                 # масса маятника, г
    L_cm: float                # длина подвеса, см
    dM_g: float = 1.0          # погрешность массы маятника, г
    dL_cm: float = 0.2         # погрешность длины подвеса, см
    dm_g: float = 0.001        # погрешность электронных весов, г
    dd_mm: float = 1.0         # погрешность отсчёта отклонения, мм
    g: float = G_DEFAULT       # ускорение свободного падения, м/с²
    d_blank_mm: float = 0.0    # отклонение при холостом выстреле, мм
    title: str = "Измерение скорости пули (баллистический маятник)"
    shots: list[Shot] = field(default_factory=list)

    # -- производные величины в СИ --
    @property
    def M(self) -> float:
        return self.M_g / 1000.0

    @property
    def L(self) -> float:
        return self.L_cm / 100.0

    @property
    def dM(self) -> float:
        return self.dM_g / 1000.0

    @property
    def dL(self) -> float:
        return self.dL_cm / 100.0


@dataclass
class ShotResult:
    idx: int
    shot: Shot
    d_corr_mm: float   # отклонение с учётом холостого выстрела
    u: float           # скорость пули, м/с
    du_syst: float     # приборная (систематическая) погрешность, м/с


# --------------------------------------------------------------------------
# Расчёт
# --------------------------------------------------------------------------


def velocity(setup: Setup, m_g: float, d_mm: float) -> float:
    """u = (M/m) * (d/L) * sqrt(g*L), всё в СИ."""
    m = m_g / 1000.0
    d = d_mm / 1000.0
    return (setup.M / m) * (d / setup.L) * math.sqrt(setup.g * setup.L)


def systematic_error(setup: Setup, m_g: float, d_mm: float, u: float) -> float:
    """
    Погрешность косвенного измерения.

    u ~ M^1 * m^-1 * d^1 * L^(-1/2)  =>
        (du/u)^2 = (dM/M)^2 + (dm/m)^2 + (dd/d)^2 + (1/2)^2 * (dL/L)^2
    """
    if d_mm <= 0 or m_g <= 0:
        return float("nan")
    rel = math.sqrt(
        (setup.dM_g / setup.M_g) ** 2
        + (setup.dm_g / m_g) ** 2
        + (setup.dd_mm / d_mm) ** 2
        + 0.25 * (setup.dL_cm / setup.L_cm) ** 2
    )
    return abs(u) * rel


def analyse(setup: Setup) -> list[ShotResult]:
    results: list[ShotResult] = []
    for i, shot in enumerate(setup.shots, start=1):
        d_corr = shot.d_mm - setup.d_blank_mm
        u = velocity(setup, shot.m_g, d_corr)
        du = systematic_error(setup, shot.m_g, d_corr, u)
        results.append(ShotResult(i, shot, d_corr, u, du))
    return results


@dataclass
class SeriesStats:
    name: str
    n: int
    mean: float
    std: float          # выборочное СКО отдельного измерения (ddof=1)
    sem: float          # стандартная ошибка среднего
    t: float            # коэффициент Стьюдента
    rand: float         # случайная погрешность среднего, t*sem
    syst: float         # приборная погрешность среднего
    total: float        # полная погрешность


@dataclass
class Comparison:
    """Сравнение двух серий: расхождение средних против их погрешностей."""

    a: str
    b: str
    diff: float
    sigma: float
    ratio: float

    @property
    def verdict(self) -> str:
        if self.ratio > 2:
            return "различие достоверно"
        if self.ratio > 1:
            return "на грани значимости"
        return "совпадают в пределах погрешности"


def compare_pairs(all_stats: list["SeriesStats"]) -> list[Comparison]:
    """Попарное сравнение серий (задание 8 методички)."""
    pairs: list[Comparison] = []
    for i, a in enumerate(all_stats):
        for b in all_stats[i + 1:]:
            diff = abs(a.mean - b.mean)
            sigma = math.hypot(a.total, b.total)
            ratio = diff / sigma if sigma else float("nan")
            pairs.append(Comparison(a.name, b.name, diff, sigma, ratio))
    return pairs


def series_stats(name: str, results: list[ShotResult]) -> SeriesStats:
    u = np.array([r.u for r in results], dtype=float)
    e = np.array([r.du_syst for r in results], dtype=float)
    n = len(u)
    mean = float(u.mean())
    std = float(u.std(ddof=1)) if n > 1 else 0.0
    sem = std / math.sqrt(n) if n > 1 else 0.0
    t = student_t(n - 1) if n > 1 else float("nan")
    rand = t * sem if n > 1 else 0.0
    # приборная (систематическая) погрешность не убывает с ростом n
    syst = float(np.nanmean(e)) if n else 0.0
    total = math.hypot(rand, syst)
    return SeriesStats(name=name, n=n, mean=mean, std=std, sem=sem, t=t,
                       rand=rand, syst=syst, total=total)


# --------------------------------------------------------------------------
# Форматирование результата с правильными значащими цифрами
# --------------------------------------------------------------------------


def _round_err(err: float) -> tuple[float, int]:
    """Округляет погрешность до 1-2 значащих цифр, возвращает (err, знаков)."""
    if not math.isfinite(err) or err <= 0:
        return err, 2
    exp = math.floor(math.log10(err))
    first = err / 10 ** exp
    sig = 2 if first < 3 else 1          # 1.x и 2.x оставляем с двумя цифрами
    decimals = max(0, -(exp - (sig - 1)))
    factor = 10 ** (exp - (sig - 1))
    return round(err / factor) * factor, decimals


def fmt_pm(value: float, err: float, unit: str = "м/с") -> str:
    if not math.isfinite(err) or err <= 0:
        return f"{value:.2f} {unit}".strip()
    err_r, dec = _round_err(err)
    return f"{value:.{dec}f} ± {err_r:.{dec}f} {unit}".strip()


# --------------------------------------------------------------------------
# Вывод
# --------------------------------------------------------------------------


def show_setup(setup: Setup) -> None:
    t = Table(box=box.SIMPLE_HEAD, show_header=False, pad_edge=False)
    t.add_column(style="bold cyan", no_wrap=True)
    t.add_column(style="white")
    t.add_row("Масса маятника M", f"{setup.M_g:.1f} ± {setup.dM_g:g} г")
    t.add_row("Длина подвеса L", f"{setup.L_cm:.1f} ± {setup.dL_cm:g} см")
    t.add_row("Погрешность весов Δm", f"{setup.dm_g:g} г")
    t.add_row("Погрешность отсчёта Δd", f"{setup.dd_mm:g} мм")
    t.add_row("g", f"{setup.g:g} м/с²")
    if setup.d_blank_mm:
        t.add_row("Холостой выстрел d₀", f"{setup.d_blank_mm:g} мм (вычитается)")
    t.add_row("Число выстрелов", str(len(setup.shots)))
    console.print(Panel(t, title="[bold]Параметры установки[/]",
                        border_style="cyan", box=box.ROUNDED))


def show_shots(results: list[ShotResult]) -> None:
    t = Table(box=box.ROUNDED, header_style="bold magenta",
              title="[bold]Результаты по выстрелам[/]", title_style="")
    t.add_column("№", justify="right", style="dim")
    t.add_column("Серия", style="yellow")
    t.add_column("m, г", justify="right")
    t.add_column("d, мм", justify="right")
    t.add_column("d испр., мм", justify="right")
    t.add_column("u, м/с", justify="right", style="bold green")
    t.add_column("Δu приб., м/с", justify="right", style="dim")
    for r in results:
        t.add_row(
            str(r.idx), r.shot.series,
            f"{r.shot.m_g:.4f}", f"{r.shot.d_mm:.1f}", f"{r.d_corr_mm:.1f}",
            f"{r.u:.1f}", f"{r.du_syst:.1f}",
        )
    console.print(t)


def show_stats(stats: SeriesStats) -> None:
    t = Table(box=box.SIMPLE, show_header=False)
    t.add_column(style="bold cyan", no_wrap=True)
    t.add_column(justify="right")
    t.add_row("Число выстрелов n", str(stats.n))
    t.add_row("Среднее ⟨u⟩", f"{stats.mean:.2f} м/с")
    t.add_row("СКО σ_u (разброс)", f"{stats.std:.2f} м/с")
    t.add_row("Ошибка среднего σ/√n", f"{stats.sem:.2f} м/с")
    t.add_row("Коэффициент Стьюдента t₀.₉₅", f"{stats.t:.2f}" if stats.n > 1 else "—")
    t.add_row("Случайная погрешность", f"{stats.rand:.2f} м/с")
    t.add_row("Приборная погрешность", f"{stats.syst:.2f} м/с")
    t.add_row("Полная погрешность Δu", f"{stats.total:.2f} м/с")
    rel = 100 * stats.total / stats.mean if stats.mean else float("nan")
    t.add_row("Относительная погрешность", f"{rel:.1f} %")

    answer = Text(f"u = {fmt_pm(stats.mean, stats.total)}", style="bold white on dark_green")
    body = Group(t, Text(""), Rule(style="green"), Text(""),
                 Text.assemble("  ", answer, "   (P = 0.95)\n"))
    console.print(Panel(body, title=f"[bold]Серия «{stats.name}»[/]",
                        border_style="green", box=box.ROUNDED))


def compare_series(all_stats: list[SeriesStats]) -> None:
    if len(all_stats) < 2:
        return
    t = Table(box=box.ROUNDED, header_style="bold magenta",
              title="[bold]Сравнение серий[/]", title_style="")
    t.add_column("Пара")
    t.add_column("Δ⟨u⟩, м/с", justify="right")
    t.add_column("σ_Δ, м/с", justify="right")
    t.add_column("Δ/σ_Δ", justify="right")
    t.add_column("Вывод")
    styles = {"различие достоверно": "bold red",
              "на грани значимости": "yellow",
              "совпадают в пределах погрешности": "green"}
    for c in compare_pairs(all_stats):
        t.add_row(f"{c.a} ↔ {c.b}", f"{c.diff:.1f}", f"{c.sigma:.1f}",
                  f"{c.ratio:.2f}", Text(c.verdict, style=styles[c.verdict]))
    console.print(t)


def show_error_budget(setup: Setup, results: list[ShotResult]) -> None:
    """Какая величина вносит основной вклад в погрешность (вопрос 7)."""
    contrib = error_budget(setup, results)
    total_sq = sum(v ** 2 for v in contrib.values())
    t = Table(box=box.ROUNDED, header_style="bold magenta",
              title="[bold]Бюджет приборной погрешности[/]", title_style="")
    t.add_column("Величина")
    t.add_column("Относит. вклад", justify="right")
    t.add_column("Доля в Δu², %", justify="right")
    t.add_column("", width=22)
    for name, v in sorted(contrib.items(), key=lambda kv: -kv[1]):
        share = 100 * v ** 2 / total_sq if total_sq else 0
        bar = "█" * int(round(share / 5))
        t.add_row(name, f"{100 * v:.2f} %", f"{share:.1f}",
                  Text(bar, style="cyan"))
    console.print(t)


# --------------------------------------------------------------------------
# График
# --------------------------------------------------------------------------


def error_budget(setup: Setup, results: list[ShotResult]) -> dict[str, float]:
    """Относительные вклады величин в приборную погрешность скорости."""
    m_mean = float(np.mean([r.shot.m_g for r in results])) or 1.0
    d_mean = float(np.mean([r.d_corr_mm for r in results])) or 1.0
    return {
        "Δd / d": setup.dd_mm / d_mean,
        "Δm / m": setup.dm_g / m_mean,
        "ΔL / 2L": 0.5 * setup.dL_cm / setup.L_cm,
        "ΔM / M": setup.dM_g / setup.M_g,
    }


def draw_error_budget(ax, setup: Setup, results: list[ShotResult],
                      color: str = "#3b6fd4", fg: str = "#222222") -> None:
    contrib = error_budget(setup, results)
    total_sq = sum(v ** 2 for v in contrib.values()) or 1.0
    names = list(contrib)
    shares = [100 * contrib[n] ** 2 / total_sq for n in names]
    bars = ax.barh(names[::-1], shares[::-1], color=color, alpha=0.85)
    ax.bar_label(bars, fmt="%.1f %%", fontsize=8, padding=3, color=fg)
    ax.set_xlim(0, 118)
    ax.set_xlabel("доля в Δu², %")
    ax.set_title("Что определяет погрешность")


def build_plot_figure(all_results: dict[str, list[ShotResult]],
                      all_stats: list[SeriesStats], setup: Setup,
                      dark: bool = False, fig=None):
    """Два графика: скорость по выстрелам и вклад величин в погрешность.

    fig — рисовать в готовую фигуру (нужно для окна GUI).
    """
    import matplotlib
    if fig is None and matplotlib.get_backend().lower() not in ("agg", "qtagg"):
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fg = "#e6e9ef" if dark else "#222222"
    bg = "#191d26" if dark else "#ffffff"
    grid = "#2b3240" if dark else "#cccccc"

    if fig is None:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5), facecolor=bg)
    else:
        fig.clear()
        fig.set_facecolor(bg)
        ax1, ax2 = fig.subplots(1, 2)
    colors = SERIES_COLORS_DARK if dark else SERIES_COLORS_PRINT

    offset = 0
    for k, (name, results) in enumerate(all_results.items()):
        c = colors[k % len(colors)]
        xs = [offset + i for i in range(1, len(results) + 1)]
        ys = [r.u for r in results]
        es = [r.du_syst for r in results]
        ax1.errorbar(xs, ys, yerr=es, fmt="o", capsize=4, color=c, label=name)
        st = next(s for s in all_stats if s.name == name)
        ax1.hlines(st.mean, xs[0] - 0.4, xs[-1] + 0.4, color=c,
                   linestyle="--", linewidth=1.4)
        ax1.fill_between([xs[0] - 0.4, xs[-1] + 0.4],
                         st.mean - st.std, st.mean + st.std, color=c, alpha=0.15)
        offset = xs[-1]

    ax1.set_xlabel("номер выстрела")
    ax1.set_ylabel("скорость пули u, м/с")
    ax1.set_title("Скорость по выстрелам (± приборная погрешность)")
    if len(all_results) > 1:
        ax1.legend()

    results = [r for rs in all_results.values() for r in rs]
    draw_error_budget(ax2, setup, results, color=colors[0], fg=fg)

    for ax in (ax1, ax2):
        ax.set_facecolor(bg)
        ax.grid(alpha=0.5, color=grid, linewidth=0.7)
        ax.set_axisbelow(True)
        ax.tick_params(colors=fg, labelsize=9)
        ax.title.set_fontsize(11)
        ax.xaxis.label.set_color(fg)
        ax.yaxis.label.set_color(fg)
        ax.title.set_color(fg)
        for spine in ax.spines.values():
            spine.set_color(grid)

    fig.tight_layout()
    return fig


def make_plot(all_results: dict[str, list[ShotResult]],
              all_stats: list[SeriesStats], path: Path,
              setup: Setup) -> Path | None:
    try:
        fig = build_plot_figure(all_results, all_stats, setup)
    except Exception as exc:  # pragma: no cover
        console.print(f"[yellow]График не построен: {exc}[/]")
        return None
    fig.savefig(path, dpi=150)
    import matplotlib.pyplot as plt
    plt.close(fig)
    return path


# --------------------------------------------------------------------------
# PDF-отчёт
# --------------------------------------------------------------------------


def _pdf_table(ax, col_labels, rows, col_widths=None, fontsize=8.5,
               title: str | None = None):
    ax.axis("off")
    if title:
        ax.set_title(title, fontsize=11, fontweight="bold", loc="left", pad=10)
    if not rows:
        return
    tbl = ax.table(cellText=rows, colLabels=col_labels, loc="upper center",
                   cellLoc="center", colWidths=col_widths)
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(fontsize)
    tbl.scale(1, 1.45)
    for (row, _col), cell in tbl.get_celld().items():
        cell.set_edgecolor("#b9c0cc")
        cell.set_linewidth(0.5)
        if row == 0:
            cell.set_facecolor("#e8edf7")
            cell.set_text_props(fontweight="bold")
        elif row % 2 == 0:
            cell.set_facecolor("#f6f8fc")


def build_report_plots(fig, setup: Setup, results: list[ShotResult],
                       by_series: dict[str, list[ShotResult]],
                       all_stats: list[SeriesStats]) -> None:
    """Четыре графика отчёта: по выстрелам, распределение, u(d), бюджет Δu."""
    colors = SERIES_COLORS_PRINT
    gs = fig.add_gridspec(2, 2, height_ratios=[1.05, 1])
    ax1 = fig.add_subplot(gs[0, :])
    ax3 = fig.add_subplot(gs[1, 0])
    ax4 = fig.add_subplot(gs[1, 1])
    fig.suptitle("Графики", fontsize=12, fontweight="bold", x=0.08, ha="left",
                 color="#2c3140")

    # 1) скорость по выстрелам
    offset = 0
    for k, (name, rs) in enumerate(by_series.items()):
        c = colors[k % len(colors)]
        xs = [offset + i for i in range(1, len(rs) + 1)]
        st = next(s for s in all_stats if s.name == name)
        ax1.errorbar(xs, [r.u for r in rs], yerr=[r.du_syst for r in rs],
                     fmt="o", capsize=3, color=c, label=name, markersize=4)
        ax1.hlines(st.mean, xs[0] - 0.4, xs[-1] + 0.4, color=c, ls="--", lw=1.2)
        ax1.fill_between([xs[0] - 0.4, xs[-1] + 0.4], st.mean - st.std,
                         st.mean + st.std, color=c, alpha=0.15)
        offset = xs[-1]
    ax1.set_xlabel("номер выстрела")
    ax1.set_ylabel("u, м/с")
    ax1.set_title("Скорость по выстрелам", fontsize=10)
    if len(by_series) > 1:
        ax1.legend(fontsize=8)

    # 2) проверка модели: u должна быть пропорциональна d
    for k, (name, rs) in enumerate(by_series.items()):
        c = colors[k % len(colors)]
        ax3.errorbar([r.d_corr_mm for r in rs], [r.u for r in rs],
                     yerr=[r.du_syst for r in rs], xerr=setup.dd_mm,
                     fmt="o", capsize=3, color=c, label=name, markersize=4)
    d_all = np.array([r.d_corr_mm for r in results], dtype=float)
    u_all = np.array([r.u for r in results], dtype=float)
    if len(d_all) > 1 and d_all.max() > d_all.min():
        k_fit = float((d_all * u_all).sum() / (d_all ** 2).sum())  # u = k*d
        xx = np.linspace(0, d_all.max() * 1.1, 50)
        ax3.plot(xx, k_fit * xx, color="#6b7280", ls=":", lw=1.4,
                 label=f"u = {k_fit:.1f}·d")
        ax3.set_xlim(left=0)
        ax3.set_ylim(bottom=0)
    ax3.set_xlabel("отклонение d, мм")
    ax3.set_ylabel("u, м/с")
    ax3.set_title("Линейность модели: u ∝ d", fontsize=10)
    ax3.legend(fontsize=8)

    # 3) бюджет приборной погрешности
    draw_error_budget(ax4, setup, results)
    ax4.set_title("Что определяет погрешность", fontsize=10)

    for ax in (ax1, ax3, ax4):
        ax.grid(alpha=0.3)
        ax.tick_params(labelsize=8)
        ax.xaxis.label.set_size(9)
        ax.yaxis.label.set_size(9)
    fig.tight_layout(rect=(0.02, 0.02, 0.98, 0.955))


def export_pdf(setup: Setup, results: list[ShotResult],
               all_stats: list[SeriesStats], path: Path) -> Path:
    """Собирает готовый PDF-отчёт: титул, данные, расчёт, графики."""
    import matplotlib
    if matplotlib.get_backend().lower() not in ("agg", "qtagg"):
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    A4 = (8.27, 11.69)
    by_series: dict[str, list[ShotResult]] = {}
    for r in results:
        by_series.setdefault(r.shot.series, []).append(r)

    with PdfPages(path) as pdf:
        # --- страница 1: установка и измерения ---
        fig = plt.figure(figsize=A4, facecolor="white")
        fig.text(0.08, 0.962, setup.title, fontsize=11, fontweight="bold",
                 color="#2c3140")
        fig.text(0.92, 0.962, f"{datetime.now():%d.%m.%Y}", fontsize=9,
                 color="#8a90a0", ha="right")
        fig.add_artist(plt.Line2D([0.08, 0.92], [0.951, 0.951],
                                  color="#c8cedb", linewidth=0.8))

        ax = fig.add_axes([0.08, 0.63, 0.84, 0.28])
        params = [
            ["Масса маятника M", f"{setup.M_g:.1f} ± {setup.dM_g:g} г"],
            ["Длина подвеса L", f"{setup.L_cm:.1f} ± {setup.dL_cm:g} см"],
            ["Погрешность весов Δm", f"{setup.dm_g:g} г"],
            ["Погрешность отсчёта Δd", f"{setup.dd_mm:g} мм"],
            ["Ускорение свободного падения g", f"{setup.g:g} м/с²"],
        ]
        if setup.d_blank_mm:
            params.append(["Холостой выстрел d₀ (вычитается)",
                           f"{setup.d_blank_mm:g} мм"])
        params.append(["Число выстрелов", str(len(results))])
        _pdf_table(ax, ["Величина", "Значение"], params, [0.55, 0.45],
                   title="Параметры установки")

        head = ["№", "Серия", "m, г", "d, мм", "d испр., мм", "u, м/с", "Δu, м/с"]
        widths = [0.06, 0.20, 0.14, 0.13, 0.16, 0.15, 0.16]
        first = [[str(r.idx), r.shot.series, f"{r.shot.m_g:.4f}",
                  f"{r.shot.d_mm:.1f}", f"{r.d_corr_mm:.1f}",
                  f"{r.u:.1f}", f"{r.du_syst:.1f}"] for r in results[:16]]
        ax2 = fig.add_axes([0.08, 0.06, 0.84, 0.52])
        _pdf_table(ax2, head, first, widths, title="Таблица измерений")
        pdf.savefig(fig)
        plt.close(fig)

        # --- продолжение таблицы, если выстрелов много ---
        rest = results[16:]
        while rest:
            chunk, rest = rest[:34], rest[34:]
            fig = plt.figure(figsize=A4, facecolor="white")
            ax = fig.add_axes([0.08, 0.06, 0.84, 0.86])
            _pdf_table(ax, head,
                       [[str(r.idx), r.shot.series, f"{r.shot.m_g:.4f}",
                         f"{r.shot.d_mm:.1f}", f"{r.d_corr_mm:.1f}",
                         f"{r.u:.1f}", f"{r.du_syst:.1f}"] for r in chunk],
                       widths, title="Таблица измерений (продолжение)")
            pdf.savefig(fig)
            plt.close(fig)

        # --- страница результатов ---
        fig = plt.figure(figsize=A4, facecolor="white")
        fig.text(0.08, 0.962, "Результаты", fontsize=12, fontweight="bold",
                 color="#2c3140")
        fig.add_artist(plt.Line2D([0.08, 0.92], [0.951, 0.951],
                                  color="#c8cedb", linewidth=0.8))
        fig.text(0.08, 0.918, r"$u=\dfrac{M}{m}\cdot\dfrac{d}{L}\cdot\sqrt{gL}$",
                 fontsize=12)
        fig.text(0.42, 0.918,
                 r"$\dfrac{\Delta u}{u}=\sqrt{\left(\dfrac{\Delta M}{M}\right)^2"
                 r"+\left(\dfrac{\Delta m}{m}\right)^2"
                 r"+\left(\dfrac{\Delta d}{d}\right)^2"
                 r"+\dfrac{1}{4}\left(\dfrac{\Delta L}{L}\right)^2}$",
                 fontsize=10)
        y = 0.865
        for st in all_stats:
            fig.text(0.08, y, f"Серия «{st.name}»", fontsize=11,
                     fontweight="bold", color="#2c3140")
            y -= 0.021
            rel = 100 * st.total / st.mean if st.mean else float("nan")
            for line in (
                f"n = {st.n};   ⟨u⟩ = {st.mean:.2f} м/с;   σ_u = {st.std:.2f} м/с;"
                f"   σ/√n = {st.sem:.2f} м/с",
                f"случайная погрешность t·σ/√n (t = {st.t:.2f}, P = 0.95): "
                f"{st.rand:.2f} м/с;   приборная: {st.syst:.2f} м/с",
            ):
                fig.text(0.10, y, line, fontsize=9, color="#3a4050")
                y -= 0.019
            fig.text(0.10, y - 0.006,
                     f"u = {fmt_pm(st.mean, st.total)}   (P = 0.95),"
                     f"  относительная погрешность {rel:.1f} %",
                     fontsize=12, fontweight="bold", color="#12492f")
            y -= 0.045

        if len(all_stats) > 1:
            rows = [[f"{c.a} ↔ {c.b}", f"{c.diff:.1f}", f"{c.sigma:.1f}",
                     f"{c.ratio:.2f}", c.verdict]
                    for c in compare_pairs(all_stats)]
            ax = fig.add_axes([0.08, y - 0.14, 0.84, 0.13])
            _pdf_table(ax, ["Пара серий", "Δ⟨u⟩, м/с", "σ_Δ, м/с", "Δ/σ_Δ", "Вывод"],
                       rows, [0.24, 0.14, 0.13, 0.11, 0.38],
                       title="Сравнение серий")
            y -= 0.17

        m_mean = float(np.mean([r.shot.m_g for r in results]))
        d_mean = float(np.mean([r.d_corr_mm for r in results]))
        contrib = {
            "масса маятника M": setup.dM_g / setup.M_g,
            "масса пули m": setup.dm_g / m_mean,
            "отклонение d": setup.dd_mm / d_mean,
            "длина подвеса L": 0.5 * setup.dL_cm / setup.L_cm,
        }
        total_sq = sum(v ** 2 for v in contrib.values())
        rows = [[k, f"{100 * v:.2f} %", f"{100 * v ** 2 / total_sq:.1f} %"]
                for k, v in sorted(contrib.items(), key=lambda kv: -kv[1])]
        ax = fig.add_axes([0.08, max(0.06, y - 0.16), 0.60, 0.15])
        _pdf_table(ax, ["Величина", "Относит. вклад", "Доля в Δu²"], rows,
                   [0.42, 0.30, 0.28], title="Бюджет приборной погрешности")
        pdf.savefig(fig)
        plt.close(fig)

        # --- страница с графиками ---
        gfig = plt.figure(figsize=A4, facecolor="white")
        build_report_plots(gfig, setup, results, by_series, all_stats)
        pdf.savefig(gfig)
        plt.close(gfig)

        meta = pdf.infodict()
        meta["Title"] = setup.title
        meta["Subject"] = "Измерение скорости пули с помощью баллистического маятника"
    return path


# --------------------------------------------------------------------------
# Отчёт
# --------------------------------------------------------------------------


def write_report(setup: Setup, results: list[ShotResult],
                 all_stats: list[SeriesStats], path: Path,
                 plot: Path | None) -> Path:
    lines: list[str] = []
    add = lines.append
    add(f"# {setup.title}")
    add("")
    add(f"_Обработка выполнена {datetime.now():%d.%m.%Y %H:%M}_")
    add("")
    add("## Расчётная формула")
    add("")
    add("$$u = \\frac{M}{m}\\,\\frac{d}{L}\\,\\sqrt{gL}$$")
    add("")
    add("$$\\frac{\\Delta u}{u} = \\sqrt{\\left(\\frac{\\Delta M}{M}\\right)^2 + "
        "\\left(\\frac{\\Delta m}{m}\\right)^2 + \\left(\\frac{\\Delta d}{d}\\right)^2 + "
        "\\frac{1}{4}\\left(\\frac{\\Delta L}{L}\\right)^2}$$")
    add("")
    add("## Параметры установки")
    add("")
    add("| Величина | Значение |")
    add("|---|---|")
    add(f"| Масса маятника M | {setup.M_g:.1f} ± {setup.dM_g:g} г |")
    add(f"| Длина подвеса L | {setup.L_cm:.1f} ± {setup.dL_cm:g} см |")
    add(f"| Погрешность весов Δm | {setup.dm_g:g} г |")
    add(f"| Погрешность отсчёта Δd | {setup.dd_mm:g} мм |")
    add(f"| g | {setup.g:g} м/с² |")
    if setup.d_blank_mm:
        add(f"| Холостой выстрел d₀ | {setup.d_blank_mm:g} мм |")
    add("")
    add("## Таблица измерений")
    add("")
    add("| № | Серия | m, г | d, мм | d испр., мм | u, м/с | Δu приб., м/с |")
    add("|---|---|---|---|---|---|---|")
    for r in results:
        add(f"| {r.idx} | {r.shot.series} | {r.shot.m_g:.4f} | {r.shot.d_mm:.1f} | "
            f"{r.d_corr_mm:.1f} | {r.u:.1f} | {r.du_syst:.1f} |")
    add("")
    add("## Результаты")
    add("")
    for st in all_stats:
        add(f"### Серия «{st.name}»")
        add("")
        add(f"- Число выстрелов n = {st.n}")
        add(f"- Среднее ⟨u⟩ = {st.mean:.2f} м/с")
        add(f"- Разброс (СКО) σ_u = {st.std:.2f} м/с")
        add(f"- Случайная погрешность (t = {st.t:.2f}, P = 0.95): {st.rand:.2f} м/с")
        add(f"- Приборная погрешность: {st.syst:.2f} м/с")
        add("")
        add(f"**u = {fmt_pm(st.mean, st.total)} (P = 0.95), "
            f"относительная погрешность {100 * st.total / st.mean:.1f} %**")
        add("")
    if len(all_stats) > 1:
        add("## Сравнение серий")
        add("")
        add("| Пара | Δ⟨u⟩, м/с | σ_Δ, м/с | Δ/σ_Δ | Вывод |")
        add("|---|---|---|---|---|")
        for c in compare_pairs(all_stats):
            add(f"| {c.a} ↔ {c.b} | {c.diff:.1f} | {c.sigma:.1f} | "
                f"{c.ratio:.2f} | {c.verdict} |")
        add("")
    if plot is not None:
        add(f"![График]({plot.name})")
        add("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# Ввод данных
# --------------------------------------------------------------------------


def ask_float(label: str, default: float | None = None,
              unit: str = "", positive: bool = True) -> float:
    suffix = f" [{unit}]" if unit else ""
    while True:
        raw = Prompt.ask(f"[cyan]{label}[/]{suffix}",
                         default=None if default is None else f"{default:g}")
        try:
            value = float(str(raw).replace(",", "."))
        except (TypeError, ValueError):
            console.print("[red]Нужно число, например 12.34[/]")
            continue
        if positive and value <= 0:
            console.print("[red]Значение должно быть положительным[/]")
            continue
        return value


def interactive_setup() -> Setup:
    console.print(Panel(
        Text.assemble(
            ("Баллистический маятник — обработка измерений\n", "bold"),
            ("u = (M/m)·(d/L)·√(gL)\n\n", "green"),
            ("Вводите числа с точкой или запятой. Enter — принять значение по умолчанию.",
             "dim"),
        ),
        border_style="cyan", box=box.DOUBLE))

    title = Prompt.ask("[cyan]Название работы[/]",
                       default="Измерение скорости пули (баллистический маятник)")
    console.print(Rule("[bold]Установка[/]", style="cyan"))
    M_g = ask_float("Масса маятника M", unit="г")
    dM_g = ask_float("Погрешность массы маятника ΔM", 1.0, unit="г")
    L_cm = ask_float("Длина подвеса L", unit="см")
    dL_cm = ask_float("Погрешность длины ΔL", 0.2, unit="см")
    dm_g = ask_float("Погрешность электронных весов Δm", 0.001, unit="г")
    dd_mm = ask_float("Погрешность отсчёта отклонения Δd", 1.0, unit="мм")
    g = ask_float("Ускорение свободного падения g", G_DEFAULT, unit="м/с²")
    d_blank = 0.0
    if Confirm.ask("[cyan]Был холостой выстрел (поправка на струю воздуха)?[/]",
                   default=False):
        d_blank = ask_float("Отклонение при холостом выстреле d₀", 0.0,
                            unit="мм", positive=False)

    setup = Setup(M_g=M_g, L_cm=L_cm, dM_g=dM_g, dL_cm=dL_cm, dm_g=dm_g,
                  dd_mm=dd_mm, g=g, d_blank_mm=d_blank, title=title)

    while True:
        console.print(Rule("[bold]Серия выстрелов[/]", style="cyan"))
        series = Prompt.ask("[cyan]Название серии (напр. винтовка / пистолет)[/]",
                            default="основная")
        console.print("[dim]Для каждого выстрела введите массу пули и отклонение "
                      "через пробел: «0.5123 47». Пустая строка — конец серии.[/]")
        n = 0
        while True:
            raw = Prompt.ask(f"  [green]выстрел #{n + 1}[/] (m г, d мм)", default="")
            if not raw.strip():
                if n == 0:
                    console.print("[red]Нужен хотя бы один выстрел[/]")
                    continue
                break
            parts = raw.replace(",", ".").split()
            if len(parts) != 2:
                console.print("[red]Введите ровно два числа через пробел[/]")
                continue
            try:
                m_g, d_mm = float(parts[0]), float(parts[1])
            except ValueError:
                console.print("[red]Не удалось разобрать числа[/]")
                continue
            if m_g <= 0 or d_mm <= 0:
                console.print("[red]Масса и отклонение должны быть > 0[/]")
                continue
            setup.shots.append(Shot(m_g=m_g, d_mm=d_mm, series=series))
            n += 1
            u_preview = velocity(setup, m_g, d_mm - setup.d_blank_mm)
            console.print(f"     [dim]→ u = {u_preview:.1f} м/с[/]")
        if not Confirm.ask("[cyan]Добавить ещё одну серию?[/]", default=False):
            break
    return setup


# --------------------------------------------------------------------------
# Сериализация
# --------------------------------------------------------------------------


def save_data(setup: Setup, path: Path) -> Path:
    data = asdict(setup)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_data(path: Path) -> Setup:
    raw = json.loads(path.read_text(encoding="utf-8"))
    shots = [Shot(**s) for s in raw.pop("shots", [])]
    return Setup(shots=shots, **raw)


DEMO = Setup(
    M_g=2900.0, dM_g=1.0, L_cm=52.0, dL_cm=0.2, dm_g=0.001, dd_mm=0.5,
    d_blank_mm=0.4, title="Демонстрационный расчёт",
    shots=[
        Shot(0.5121, 10.4, "винтовка"), Shot(0.5098, 10.0, "винтовка"),
        Shot(0.5134, 10.7, "винтовка"), Shot(0.5110, 10.2, "винтовка"),
        Shot(0.5087, 7.1, "пистолет"), Shot(0.5142, 6.8, "пистолет"),
        Shot(0.5099, 7.4, "пистолет"), Shot(0.5126, 6.9, "пистолет"),
    ],
)


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------


def run(setup: Setup, outdir: Path, make_files: bool = True) -> None:
    results = analyse(setup)
    console.print()
    show_setup(setup)
    show_shots(results)

    by_series: dict[str, list[ShotResult]] = {}
    for r in results:
        by_series.setdefault(r.shot.series, []).append(r)

    all_stats = [series_stats(name, rs) for name, rs in by_series.items()]
    for st in all_stats:
        show_stats(st)
    if len(all_stats) > 1:
        compare_series(all_stats)
        overall = series_stats("все выстрелы", results)
        console.print(Panel(
            Text(f"По всем выстрелам: u = {fmt_pm(overall.mean, overall.total)}"),
            border_style="dim", box=box.ROUNDED))
    show_error_budget(setup, results)

    if not make_files:
        return

    outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    data_path = save_data(setup, outdir / f"data-{stamp}.json")
    plot_path = make_plot(by_series, all_stats,
                          outdir / f"plot-{stamp}.png", setup=setup)
    report_path = write_report(setup, results, all_stats,
                               outdir / f"report-{stamp}.md", plot_path)
    pdf_path: Path | None
    try:
        pdf_path = export_pdf(setup, results, all_stats,
                              outdir / f"report-{stamp}.pdf")
    except Exception as exc:  # pragma: no cover
        console.print(f"[yellow]PDF не собран: {exc}[/]")
        pdf_path = None

    files = Table(box=box.SIMPLE, show_header=False)
    files.add_column(style="bold cyan")
    files.add_column()
    files.add_row("Данные", str(data_path))
    files.add_row("Отчёт (md)", str(report_path))
    if pdf_path:
        files.add_row("Отчёт (pdf)", str(pdf_path))
    if plot_path:
        files.add_row("График", str(plot_path))
    console.print(Panel(files, title="[bold]Сохранено[/]", border_style="blue",
                        box=box.ROUNDED))
    console.print("[dim]Пересчитать без повторного ввода: "
                  f"uv run bullet_speed.py {data_path.name}[/]")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Обработка лабораторной «Скорость пули» (баллистический маятник)")
    parser.add_argument("data", nargs="?", type=Path,
                        help="JSON с ранее введёнными данными")
    parser.add_argument("--demo", action="store_true", help="демонстрационный пример")
    parser.add_argument("--outdir", type=Path, default=Path("results"),
                        help="куда класть отчёт, график и данные (по умолчанию ./results)")
    parser.add_argument("--no-files", action="store_true",
                        help="только вывод в терминал, ничего не сохранять")
    args = parser.parse_args(argv)

    try:
        if args.demo:
            setup = DEMO
        elif args.data:
            setup = load_data(args.data)
        else:
            setup = interactive_setup()
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Прервано пользователем[/]")
        return 130
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        console.print(f"[red]Не удалось прочитать данные: {exc}[/]")
        return 1

    if not setup.shots:
        console.print("[red]Нет ни одного выстрела — нечего считать[/]")
        return 1

    run(setup, args.outdir, make_files=not args.no_files)
    return 0


if __name__ == "__main__":
    sys.exit(main())
