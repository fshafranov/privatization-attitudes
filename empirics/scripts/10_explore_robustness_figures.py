"""
10_explore_robustness_figures.py
Stage:      analysis (descriptive figures for robustness checks R2, R3 and the second-flat split)
Purpose:    fig9: owner x regional price coefficient across control sets (r3, all baseline x year
            interactions, LASSO-selected, + local income) and the second-flat contrast; fig10:
            permutation distributions of the r3 coefficient with the actual estimate marked.
Reproduces: n/a: original analysis
Reads:      empirics/results/robust_flexible_controls.csv, empirics/results/analyze_second_flat.csv,
            empirics/results/robust_permutation.csv, empirics/results/robust_permutation_draws.csv
Writes:     empirics/results/figures/fig9_robustness.png, empirics/results/figures/fig10_permutation.png,
            empirics/results/logs/explore_robustness_figures.log
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis_config import script_name  # noqa: E402
from pipeline import check, get_logger, project_root  # noqa: E402

EXERCISE = script_name(__file__)
log = get_logger(EXERCISE, log_dir="empirics/results/logs")
root = project_root()
FIG = root / "empirics/results/figures"
SURFACE, INK, INK2, MUTED, GRID, AXIS, BLUE = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#2a78d6"
plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Helvetica Neue", "Arial", "DejaVu Sans"],
    "font.size": 10, "text.color": INK, "axes.labelcolor": INK2, "axes.edgecolor": AXIS,
    "xtick.color": MUTED, "ytick.color": INK2, "axes.facecolor": SURFACE, "figure.facecolor": SURFACE,
    "axes.spines.top": False, "axes.spines.right": False, "savefig.dpi": 200,
})
OUTS = [("idx_trust_state", "Trust in state institutions"), ("idx_democracy", "Democratic values")]

# == FIGURE 9: COEFFICIENT ACROSS CONTROL SETS AND THE SECOND-FLAT CONTRAST ==
fc = pd.read_csv(root / "empirics/results/robust_flexible_controls.csv")
sf = pd.read_csv(root / "empirics/results/analyze_second_flat.csv")
ROWS = [("r7", "Preferred (+ owner-by-year FE)"), ("f1", "+ 72 baseline × year controls"),
        ("f2", "+ LASSO-selected controls"), ("f3", "+ all controls and owner × local income"),
        ("h2", "Second-flat vs single-flat owners")]
fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.6), sharey=True)
for ax, (outcome, title) in zip(axes, OUTS):
    for k, (spec, _) in enumerate(ROWS):
        src = sf[(sf.spec == "h2") & (sf.term == "second_x_price")] if spec == "h2" else fc[fc.spec == spec]
        row = src[src.outcome == outcome]
        check(len(row) == 1, f"fig9: expected one row for {outcome} {spec}")
        row = row.iloc[0]
        col = MUTED if spec == "h2" else BLUE
        ax.plot([row.estimate - 1.96 * row.std_error, row.estimate + 1.96 * row.std_error], [k, k], color=col,
                lw=2, solid_capstyle="round")
        ax.plot(row.estimate, k, "o", ms=7, color=col, mec=SURFACE, mew=2)
        ax.annotate(f"p={row.wild_p:.2f}", (1, k), xycoords=("axes fraction", "data"), xytext=(4, 0),
                    textcoords="offset points", va="center", fontsize=8, color=MUTED)
    ax.axhline(3.5, color=GRID, lw=1)
    ax.axvline(0, color=AXIS, lw=1, zorder=0)
    ax.set_xlim(-0.45, 0.45)
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_title(title, loc="left", fontsize=10)
    ax.set_xlabel("SD change per log point of regional price")
    ax.tick_params(axis="y", length=0)
axes[0].set_yticks(range(len(ROWS)), [lbl for _, lbl in ROWS])
axes[0].invert_yaxis()
fig.suptitle("Flexible controls leave the estimate unchanged; second-flat owners respond no more",
             x=0.01, ha="left", fontsize=11, fontweight="bold")
fig.text(0.01, -0.06, "Owner-in-2006 × log Rosstat regional price, person + unit-by-year + age-group-by-year + owner-by-year FE; "
         "bottom row: extra response of second-flat owners. 95% CIs by region (32); p = wild bootstrap.",
         fontsize=8, color=MUTED)
fig.tight_layout(rect=(0, 0, 0.94, 1))
fig.savefig(FIG / "fig9_robustness.png", bbox_inches="tight")
plt.close(fig)

# == FIGURE 10: PERMUTATION DISTRIBUTIONS ====================================
pm = pd.read_csv(root / "empirics/results/robust_permutation.csv").set_index("outcome")
dr = pd.read_csv(root / "empirics/results/robust_permutation_draws.csv")
fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.2))
for ax, (outcome, title) in zip(axes, OUTS):
    ax.hist(dr[outcome], bins=40, color="#b9b8b0", edgecolor=SURFACE, linewidth=0.5)
    ax.axvline(pm.loc[outcome, "estimate"], color=BLUE, lw=2)
    ax.annotate(f"actual {pm.loc[outcome, 'estimate']:.3f}\npermutation p = {pm.loc[outcome, 'perm_p']:.2f}",
                (0.02, 0.95), xycoords="axes fraction", va="top", fontsize=8, color=INK2)
    ax.set_title(title, loc="left", fontsize=10)
    ax.set_xlabel("Coefficient with price paths reassigned across regions")
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
fig.suptitle("The actual estimate is typical of random reassignments of regional price paths", x=0.01, ha="left",
             fontsize=11, fontweight="bold")
fig.text(0.01, -0.06, f"{int(pm.n_perm.iloc[0]):,} random reassignments of the 32 regions' 2006/2012/2017/2018 price paths; "
         "common sample with all outcomes observed; owner-by-year FE included.", fontsize=8, color=MUTED)
fig.tight_layout()
fig.savefig(FIG / "fig10_permutation.png", bbox_inches="tight")
plt.close(fig)
log.info("end")
