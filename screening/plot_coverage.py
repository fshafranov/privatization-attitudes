"""plot_coverage.py — screening figure (not part of run_all.py).

Purpose: show which RLMS rounds ask each political / attitude item, i.e. why within-person
designs fail. Reads screening/results/ind_item_coverage.csv (from screen_individual.py).
Writes screening/results/fig_item_coverage.png.
Run: uv run python -I screening/plot_coverage.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

HERE = Path(__file__).resolve().parent / "results"
SURFACE, INK, INK2, MUTED, GRID, BLUE, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#2a78d6", "#c3c2b7"
ITEMS = [  # (variable, label), grouped by theme
    ("j91", "Voted in 1996 presidential election"), ("j104", "Opinion of market reform"),
    ("j102_3", "Can democrats save Russia?"), ("j107", "Best political system for Russia"),
    ("j110", "Opinion of Putin as president"), ("j118_5", "Close to democrats?"),
    ("j137", "Attended political meetings"), ("j182", "Voted in Duma election"),
    ("j223", "What to do with privatized firms"), ("j207_1", "Trust in government"),
    ("j208_1", "Free elections important?"), ("j485_2", "Took part in protests"),
    ("j69_7", "Government should limit incomes of the rich"), ("j69_5", "Private employer better than state?"),
]
cov = pd.read_csv(HERE / "ind_item_coverage.csv", index_col=0)
cov.columns = [int(float(c)) for c in cov.columns]
plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Helvetica Neue", "Arial", "DejaVu Sans"],
                     "font.size": 9, "axes.facecolor": SURFACE, "figure.facecolor": SURFACE,
                     "axes.edgecolor": AXIS, "xtick.color": MUTED, "ytick.color": INK2, "savefig.dpi": 200})
fig, ax = plt.subplots(figsize=(9, 4.4))
ax.axvspan(1993.5, 2002.5, color="#f0efec", zorder=0)
ax.text(1998, -0.75, "housing question asked", ha="center", fontsize=8, color=MUTED)
for i, (var, label) in enumerate(ITEMS):
    yrs = [y for y, n in cov.loc[var].items() if n >= 100]
    ax.plot(yrs, [i] * len(yrs), "o", ms=8, color=BLUE, mec=SURFACE, mew=2)
ax.set_yticks(range(len(ITEMS)), [lbl for _, lbl in ITEMS])
ax.invert_yaxis()
ax.set_ylim(len(ITEMS) - 0.1, -1)
ax.set_xlim(1993, 2026)
ax.grid(axis="x", color=GRID, lw=0.6)
ax.tick_params(axis="y", length=0)
for side in ("top", "right", "left"):
    ax.spines[side].set_visible(False)
fig.suptitle("Most RLMS political questions were asked in a single round", x=0.01, ha="left",
             fontsize=11, fontweight="bold")
fig.text(0.01, -0.02, "Dot = round with at least 100 valid answers. RLMS individual file, 1994–2025.",
         fontsize=8, color=MUTED)
fig.tight_layout()
fig.savefig(HERE / "fig_item_coverage.png", bbox_inches="tight")
