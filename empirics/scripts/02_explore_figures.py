"""
02_explore_figures.py
Stage:      analysis (descriptive figures)
Purpose:    Figures for the 2006 cross-section: (1) s3 coefficients with 95% CIs; (2) the
            mix of j223 answers by 1990s history group; (3) the two histories over time
            (households privatized; employed people holding employer shares).
Reproduces: n/a: original analysis
Reads:      empirics/results/analyze_longrun_2006.csv, data/processed/longrun_2006/longrun_2006.csv,
            data/clean/rlms/rlms_ind.csv, data/clean/rlms/rlms_hh.csv
Writes:     empirics/results/figures/fig1_coefficients.png, fig2_answer_mix.png, fig3_histories.png,
            fig4_indices.png,
            empirics/results/explore_figures.csv (numbers plotted in fig2 and fig3),
            empirics/results/logs/explore_figures.log
Colors:     dataviz reference palette; diverging blue (keep) / red (revise) / gray (DK),
            validated with validate_palette.js (light mode); segment labels give relief for the
            one slot under 3:1 contrast.
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis_config import EXPECTED_N, WORKFILE, script_name  # noqa: E402
from pipeline import check, get_logger, project_root, write_table  # noqa: E402

EXERCISE = script_name(__file__)
log = get_logger(EXERCISE, log_dir="empirics/results/logs")
root = project_root()
FIG = root / "empirics/results/figures"
FIG.mkdir(parents=True, exist_ok=True)

SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
BLUE = "#2a78d6"
ANSWERS = [  # j223 code -> label, colour (diverging: keep = blue, revise = red, DK = neutral gray)
    (1, "Leave with owners", "#184f95"),
    (2, "Leave, owners pay extra", "#5598e7"),
    (4, "Re-privatize another way", "#e66767"),
    (3, "Return to the state", "#b52f2e"),
    (7, "Don't know", "#c3c2b7"),
]
plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Helvetica Neue", "Arial", "DejaVu Sans"],
    "font.size": 10, "text.color": INK, "axes.labelcolor": INK2, "axes.edgecolor": AXIS,
    "xtick.color": MUTED, "ytick.color": INK2, "axes.facecolor": SURFACE, "figure.facecolor": SURFACE,
    "axes.spines.top": False, "axes.spines.right": False, "savefig.dpi": 200,
})
plotted = []

# == FIGURE 1: COEFFICIENTS (s3: controls + region FE) =======================
res = pd.read_csv(root / "empirics/results/analyze_longrun_2006.csv")
s3 = res[res.spec == "s3"]
ROWS = [("share_owner_early", "Owned employer shares, 1994–96"), ("lost_shares", "Lost those shares by 1998–2005"),
        ("became_privatized", "Household privatized flat, 1995–2002"),
        ("privatized_at_first_obs", "Flat already privatized when first seen"), ("coop_1980s", "Ran a cooperative in the 1980s")]
PANELS = [("revise", "Supports revising privatization"), ("dont_know", "Answers “don't know”")]
fig, axes = plt.subplots(1, 2, figsize=(9, 3.6), sharey=True)
for ax, (outcome, title) in zip(axes, PANELS):
    d = s3[s3.outcome == outcome].set_index("term")
    check(all(t in d.index for t, _ in ROWS), f"fig1: missing terms for {outcome}")
    for i, (term, _) in enumerate(ROWS):
        b, se, n = d.loc[term, "estimate"], d.loc[term, "std_error"], int(d.loc[term, "nobs"])
        ax.plot([b - 1.96 * se, b + 1.96 * se], [i, i], color=BLUE, lw=2, solid_capstyle="round")
        ax.plot(b, i, "o", ms=7, color=BLUE, mec=SURFACE, mew=2)
        ax.annotate(f"N={n:,}", (1, i), xycoords=("axes fraction", "data"), xytext=(4, 0),
                    textcoords="offset points", va="center", fontsize=8, color=MUTED)
    ax.axvline(0, color=AXIS, lw=1, zorder=0)
    ax.set_xlim(-0.15, 0.15)
    ax.set_xticks([-0.1, -0.05, 0, 0.05, 0.1], ["\u221210", "\u22125", "0", "+5", "+10"])
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_title(title, loc="left", fontsize=10, color=INK)
    ax.set_xlabel("Difference, percentage points")
axes[0].set_yticks(range(len(ROWS)), [lbl for _, lbl in ROWS])
axes[0].invert_yaxis()
axes[0].tick_params(axis="y", length=0)
fig.suptitle("1990s privatization histories barely shift 2006 views on revising privatization",
             x=0.01, ha="left", fontsize=11, fontweight="bold")
fig.text(0.01, -0.09, "Linear probability models with age, sex, education, settlement type, income and region "
         "fixed effects; 95% CIs, SEs clustered by sampling unit. Comparisons: share rows vs employed non-owners\n"
         "and vs owners who kept shares; housing rows vs households never privatized; cooperative vs everyone else. RLMS 2006.", fontsize=8, color=MUTED)
fig.tight_layout(rect=(0, 0, 0.95, 1))
fig.savefig(FIG / "fig1_coefficients.png", bbox_inches="tight")
plt.close(fig)

# == FIGURE 2: ANSWER MIX BY HISTORY GROUP ===================================
w = pd.read_csv(root / WORKFILE)
check(len(w) == EXPECTED_N, f"expected N={EXPECTED_N}, workfile has {len(w)}")
groups = [
    ("All adults", w),
    ("Owned shares 1994–96, kept them", w[w.lost_shares == 0]),
    ("Owned shares 1994–96, lost them", w[w.lost_shares == 1]),
    ("Household privatized flat 1995–2002", w[w.housing_path == "became_privatized"]),
    ("Household never privatized", w[w.housing_path == "never_privatized"]),
    ("Ran a cooperative in the 1980s", w[w.coop_1980s == 1]),
    ("Asked, did not run one (age 35+)", w[w.coop_1980s == 0]),  # j224 asked only of adults 35+ in 2006
]
fig, ax = plt.subplots(figsize=(9, 3.8))
for i, (name, g) in enumerate(groups):
    shares = g.j223.value_counts(normalize=True)
    left = 0.0
    for code, label, color in ANSWERS:
        v = float(shares.get(code, 0.0))
        plotted.append({"figure": "fig2", "group": name, "series": label, "x": "", "value": round(v, 4), "n": len(g)})
        ax.barh(i, v, left=left, height=0.62, color=color, edgecolor=SURFACE, linewidth=2)
        if v >= 0.07:
            ink = "#ffffff" if code in (1, 3) else INK
            ax.text(left + v / 2, i, f"{v:.0%}", ha="center", va="center", fontsize=8, color=ink)
        left += v
    ax.annotate(f"N={len(g):,}", (1, i), xycoords=("axes fraction", "data"), xytext=(4, 0),
                textcoords="offset points", va="center", fontsize=8, color=MUTED)
ax.set_yticks(range(len(groups)), [g for g, _ in groups])
ax.invert_yaxis()
ax.set_xlim(0, 1)
ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
ax.tick_params(axis="y", length=0)
ax.spines["left"].set_visible(False)
handles = [matplotlib.patches.Patch(color=c, label=l) for _, l, c in ANSWERS]
ax.legend(handles=handles, ncol=5, loc="lower left", bbox_to_anchor=(0, 1.0), frameon=False, fontsize=8,
          handlelength=1, columnspacing=1.2)
fig.suptitle("“What should be done with enterprises privatized earlier?” (RLMS 2006)",
             x=0.01, ha="left", fontsize=11, fontweight="bold")
fig.tight_layout(rect=(0, 0, 0.95, 1))
fig.savefig(FIG / "fig2_answer_mix.png", bbox_inches="tight")
plt.close(fig)

# == FIGURE 3: THE TWO HISTORIES OVER TIME ===================================
ind = pd.read_csv(root / "data/clean/rlms/rlms_ind.csv", usecols=["year", "j26"])
hh = pd.read_csv(root / "data/clean/rlms/rlms_hh.csv", usecols=["id_w", "c2"])
yr = dict(zip(range(5, 35), [1994, 1995, 1996, 1998] + list(range(2000, 2026))))  # RLMS round -> year
check(set(hh.id_w.unique()) <= set(yr), "unexpected RLMS round in household file")
hh["year"] = hh.id_w.map(yr)
priv = hh[hh.c2.isin([1, 2])].groupby("year").c2.apply(lambda s: (s == 1).mean())
own = ind[ind.j26.isin([1, 2])].groupby("year").j26.apply(lambda s: (s == 1).mean())
for s, name in [(priv, "households in privatized flats"), (own, "employed who co-own their employer")]:
    plotted += [{"figure": "fig3", "group": "", "series": name, "x": int(k), "value": round(float(v), 4), "n": ""}
                for k, v in s.items()]
fig, axes = plt.subplots(1, 2, figsize=(9, 3.2))
for ax, s, title, lim in [(axes[0], priv, "Households living in a privatized flat", (0, 0.8)),
                          (axes[1], own, "Employed who co-own their employer", (0, 0.3))]:
    dense = len(s) > 12
    ax.plot(s.index, s.values, color=BLUE, lw=2, marker=None if dense else "o", ms=6, mec=SURFACE, mew=1.5)
    ax.set_ylim(*lim)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_title(title, loc="left", fontsize=10)
    for x in (s.index[0], s.index[-1]):
        ax.annotate(f"{s[x]:.0%}", (x, s[x]), xytext=(0, 8), textcoords="offset points", ha="center",
                    fontsize=8, color=INK2)
axes[1].axvline(2006, color=AXIS, lw=1, ls="--", zorder=0)
axes[1].annotate("attitudes measured", (2006, 0.27), xytext=(4, 0), textcoords="offset points", fontsize=8, color=MUTED)
fig.text(0.01, -0.04, "RLMS 1994–2025. The housing question is asked only through 2002. "
         "Left: share of households answering. Right: share of employed respondents answering.", fontsize=8, color=MUTED)
fig.tight_layout()
fig.savefig(FIG / "fig3_histories.png", bbox_inches="tight")
plt.close(fig)

# == FIGURE 4: HISTORIES AND THE FOUR ATTITUDE INDICES (s3) ==================
IDX = [("idx_market_legit", "Market legitimacy"), ("idx_democracy", "Democratic values"),
       ("idx_trust_state", "Trust in state institutions"), ("idx_state_approval", "Approval of the state")]
fig, axes = plt.subplots(2, 2, figsize=(9, 6), sharex=True, sharey=True)
for ax, (outcome, title) in zip(axes.flat, IDX):
    d = s3[s3.outcome == outcome].set_index("term")
    check(all(t in d.index for t, _ in ROWS), f"fig4: missing terms for {outcome}")
    for i, (term, _) in enumerate(ROWS):
        b, se, q = d.loc[term, "estimate"], d.loc[term, "std_error"], d.loc[term, "q_value_bh"]
        ax.plot([b - 1.96 * se, b + 1.96 * se], [i, i], color=BLUE, lw=2, solid_capstyle="round")
        ax.plot(b, i, "o", ms=7, color=BLUE, mec=SURFACE, mew=2)
        ax.annotate(f"q={q:.2f}", (1, i), xycoords=("axes fraction", "data"), xytext=(4, 0),
                    textcoords="offset points", va="center", fontsize=7.5, color=MUTED)
    ax.axvline(0, color=AXIS, lw=1, zorder=0)
    ax.set_xlim(-0.55, 0.55)
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_title(title, loc="left", fontsize=10)
    ax.tick_params(axis="y", length=0)
axes[0, 0].set_yticks(range(len(ROWS)), [lbl for _, lbl in ROWS])
axes[0, 0].invert_yaxis()
for ax in axes[1]:
    ax.set_xlabel("Difference, standard deviations")
fig.suptitle("Housing histories lean positive on every index, but nothing survives multiple-testing correction",
             x=0.01, ha="left", fontsize=11, fontweight="bold")
fig.text(0.01, -0.03, "Same models as figure 1 (controls + region FE), outcomes standardized indices "
         "(mean of z-scored items). q = Benjamini-Hochberg across the 20 tests shown. RLMS 2006.",
         fontsize=8, color=MUTED)
fig.tight_layout(rect=(0, 0, 0.96, 1))
fig.savefig(FIG / "fig4_indices.png", bbox_inches="tight")
plt.close(fig)

write_table(log, pd.DataFrame(plotted), f"empirics/results/{EXERCISE}.csv", sort_by=["figure", "group", "series", "x"])
log.info("end", figures=sorted(p.name for p in FIG.glob("*.png")))
