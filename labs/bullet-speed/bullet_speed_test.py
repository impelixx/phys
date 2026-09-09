# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy>=1.26", "matplotlib>=3.8", "rich>=13.7"]
# ///
"""
Проверка расчётного ядра: uv run bullet_speed_test.py

Фиксирует поведение формул, погрешностей и экспорта, чтобы правки в
интерфейсе или оформлении не поменяли числа.
"""

from __future__ import annotations

import importlib.util
import math
import sys
import tempfile
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "bullet_speed_core", Path(__file__).resolve().parent / "bullet_speed.py")
core = importlib.util.module_from_spec(_spec)
sys.modules["bullet_speed_core"] = core
_spec.loader.exec_module(core)

failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ok   {name}")
    else:
        failures.append(f"{name}: {detail}")
        print(f"  FAIL {name} — {detail}")


setup = core.Setup(M_g=2900.0, L_cm=52.0, dM_g=1.0, dL_cm=0.2, dm_g=0.001,
                   dd_mm=0.5, d_blank_mm=0.4,
                   shots=[core.Shot(0.5, 10.4, "a"), core.Shot(0.5, 10.0, "a")])

print("формула u = (M/m)·(d/L)·√(gL)")
u = core.velocity(setup, 0.5, 10.0)
expected = (2.9 / 0.0005) * (0.010 / 0.52) * math.sqrt(9.82 * 0.52)
check("значение скорости", abs(u - expected) < 1e-9, f"{u} vs {expected}")
check("u линейна по d", abs(core.velocity(setup, 0.5, 20.0) - 2 * u) < 1e-9)
check("u обратно пропорциональна m",
      abs(core.velocity(setup, 1.0, 10.0) - u / 2) < 1e-9)

print("поправка на холостой выстрел")
res = core.analyse(setup)
check("d уменьшено на d₀", abs(res[0].d_corr_mm - 10.0) < 1e-12,
      f"{res[0].d_corr_mm}")

print("погрешности")
rel = res[0].du_syst / res[0].u
manual = math.sqrt((1.0 / 2900) ** 2 + (0.001 / 0.5) ** 2
                   + (0.5 / 10.0) ** 2 + 0.25 * (0.2 / 52) ** 2)
check("относительная приборная погрешность", abs(rel - manual) < 1e-12)
st = core.series_stats("a", res)
check("приборная погрешность не делится на √n",
      abs(st.syst - (res[0].du_syst + res[1].du_syst) / 2) < 1e-9)
check("полная = √(случайная² + приборная²)",
      abs(st.total - math.hypot(st.rand, st.syst)) < 1e-9)
check("коэффициент Стьюдента для n=2", abs(st.t - 12.71) < 1e-9, f"{st.t}")
check("t интерполируется между табличными 2.09 (df=20) и 2.06 (df=25)",
      2.09 > core.student_t(22) > 2.06, f"{core.student_t(22)}")

print("округление результата")
check("две значащие у погрешности с 1", core.fmt_pm(244.48, 16.22) == "244 ± 16 м/с",
      core.fmt_pm(244.48, 16.22))
check("одна значащая у погрешности с 3+",
      core.fmt_pm(163.91, 5.4) == "164 ± 5 м/с", core.fmt_pm(163.91, 5.4))
check("нулевая погрешность", core.fmt_pm(100.0, 0.0) == "100.00 м/с",
      core.fmt_pm(100.0, 0.0))

print("сравнение серий")
two = core.Setup(M_g=2900.0, L_cm=52.0, shots=[
    core.Shot(0.5, 10.0, "винтовка"), core.Shot(0.5, 10.2, "винтовка"),
    core.Shot(0.5, 7.0, "пистолет"), core.Shot(0.5, 7.2, "пистолет")])
res2 = core.analyse(two)
by: dict[str, list] = {}
for r in res2:
    by.setdefault(r.shot.series, []).append(r)
stats = [core.series_stats(n, rs) for n, rs in by.items()]
pairs = core.compare_pairs(stats)
check("одна пара для двух серий", len(pairs) == 1, str(len(pairs)))
check("вывод о достоверности", pairs[0].verdict in (
    "различие достоверно", "на грани значимости",
    "совпадают в пределах погрешности"))
check("три пары для трёх серий",
      len(core.compare_pairs(stats + [stats[0]])) == 3)

print("бюджет погрешности")
budget = core.error_budget(setup, res)
check("доминирует отсчёт d", max(budget, key=budget.get) == "Δd / d",
      str(budget))

print("сохранение и чтение данных")
with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "data.json"
    core.save_data(core.DEMO, path)
    loaded = core.load_data(path)
    check("параметры совпадают", loaded.M_g == core.DEMO.M_g
          and loaded.d_blank_mm == core.DEMO.d_blank_mm)
    check("выстрелы совпадают",
          [(s.m_g, s.d_mm, s.series) for s in loaded.shots]
          == [(s.m_g, s.d_mm, s.series) for s in core.DEMO.shots])

    demo_res = core.analyse(core.DEMO)
    demo_by: dict[str, list] = {}
    for r in demo_res:
        demo_by.setdefault(r.shot.series, []).append(r)
    demo_stats = [core.series_stats(n, rs) for n, rs in demo_by.items()]
    pdf = core.export_pdf(core.DEMO, demo_res, demo_stats, Path(tmp) / "r.pdf")
    check("PDF собирается", pdf.exists() and pdf.stat().st_size > 20_000,
          f"{pdf.stat().st_size} байт")
    md = core.write_report(core.DEMO, demo_res, demo_stats,
                           Path(tmp) / "r.md", None)
    check("markdown-отчёт содержит результат", "P = 0.95" in md.read_text())
    png = core.make_plot(demo_by, demo_stats, Path(tmp) / "p.png", core.DEMO)
    check("график сохраняется", png is not None and png.exists())

print()
if failures:
    print(f"ПРОВАЛЕНО: {len(failures)}")
    sys.exit(1)
print("Все проверки пройдены")
