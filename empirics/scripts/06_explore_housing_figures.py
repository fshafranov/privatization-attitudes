"""
06_explore_housing_figures.py
Stage:      analysis (descriptive figures for the housing-wealth trial)
Purpose:    fig5: local price paths by PSU, 2006-2018; fig6: first stage as a binned scatter
            (owners' own log value per m2 vs the leave-out local index, both net of person and
            year FE); fig7: reduced-form coefficients across specifications.
Reproduces: n/a: original analysis
Reads:      data/processed/housing_wealth/housing_wealth.csv, data/processed/housing_wealth/price_index.csv,
            empirics/results/analyze_housing_wealth.csv, empirics/results/analyze_event_study.csv,
            empirics/results/analyze_event_study_pretrends.csv
Writes:     empirics/results/figures/fig5_local_prices.png, fig6_first_stage.png, fig7_housing_reduced_form.png,
            fig8_event_study.png,
            empirics/results/explore_housing_figures.csv, empirics/results/logs/explore_housing_figures.log
"""
import sys
from pathlib import Path

import matplotlib
import matplotlib.lines  # noqa: F401

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis_config import demean, script_name  # noqa: E402
from pipeline import check, get_logger, project_root, write_table  # noqa: E402

EXERCISE = script_name(__file__)
log = get_logger(EXERCISE, log_dir="empirics/results/logs")
root = project_root()
FIG = root / "empirics/results/figures"
FIG.mkdir(parents=True, exist_ok=True)
SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"  # categorical slots 1-3 (validated all-pairs)
plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Helvetica Neue", "Arial", "DejaVu Sans"],
    "font.size": 10, "text.color": INK, "axes.labelcolor": INK2, "axes.edgecolor": AXIS,
    "xtick.color": MUTED, "ytick.color": INK2, "axes.facecolor": SURFACE, "figure.facecolor": SURFACE,
    "axes.spines.top": False, "axes.spines.right": False, "savefig.dpi": 200,
})
YEAR = {15: 2006, 21: 2012, 26: 2017, 27: 2018}
plotted = []

# == FIGURE 5: LOCAL PRICE PATHS BY PSU ======================================
pi = pd.read_csv(root / "data/processed/housing_wealth/price_index.csv")
check(set(pi.id_w) == set(YEAR), f"unexpected rounds in price index: {sorted(set(pi.id_w))}")
pi["year"] = pi.id_w.map(YEAR)
w = pi.pivot(index="psu", columns="year", values="log_p")
idx = w.sub(w[2006], axis=0)  # change in log price since 2006
fig, ax = plt.subplots(figsize=(8, 4.2))
for psu, row in idx.iterrows():
    hi = psu in (1, 2)
    ax.plot(row.index, row.values, color=ORANGE if hi else "#b9b8b0", lw=1.6 if hi else 0.9, zorder=3 if hi else 1)
med = idx.median()
ax.plot(med.index, med.values, color=BLUE, lw=2.5, marker="o", ms=6, mec=SURFACE, mew=1.5, zorder=4)
ax.annotate("median of 38 sampling units", (2018, med[2018]), xytext=(6, 0), textcoords="offset points",
            va="center", fontsize=8, color=BLUE)
for psu, name in [(2, "Moscow City"), (1, "St Petersburg")]:
    ax.annotate(name, (2018, idx.loc[psu, 2018]), xytext=(6, 0), textcoords="offset points", va="center",
                fontsize=8, color=ORANGE)
ax.set_xticks([2006, 2012, 2017, 2018])
ax.set_xlim(2005.5, 2021.5)
ax.axhline(0, color=AXIS, lw=1, zorder=0)
ax.grid(axis="y", color=GRID, lw=0.6)
ax.set_ylabel("Change in log price per m² since 2006")
fig.suptitle("Local house prices rose unevenly across RLMS sampling units", x=0.01, ha="left",
             fontsize=11, fontweight="bold")
fig.text(0.01, -0.03, "Mean log of owners' self-reported market value per m², by sampling unit and round. "
         "A change of 1.0 = prices × 2.7. RLMS.", fontsize=8, color=MUTED)
fig.tight_layout()
fig.savefig(FIG / "fig5_local_prices.png", bbox_inches="tight")
plt.close(fig)
plotted += [{"figure": "fig5", "series": f"psu_{p}", "x": int(y), "y": round(float(v), 4)}
            for p, r in idx.iterrows() for y, v in r.items()]

# == FIGURE 6: FIRST STAGE (BINNED, NET OF PERSON AND YEAR FE) ===============
df = pd.read_csv(root / "data/processed/housing_wealth/housing_wealth.csv")
fs = df[(df.owner_2006 == 1) & df.log_value_m2_own.notna()].copy()
fs = fs[fs.groupby("idind").year.transform("size") >= 2]
r = demean(fs, ["log_value_m2_own", "log_p_local"], ["idind", "year"])
r["bin"] = pd.qcut(r.log_p_local, 20, labels=False, duplicates="drop")
b = r.groupby("bin").agg(x=("log_p_local", "mean"), y=("log_value_m2_own", "mean"), n=("bin", "size"))
slope = float(np.polyfit(r.log_p_local, r.log_value_m2_own, 1)[0])
res = pd.read_csv(root / "empirics/results/analyze_housing_wealth.csv")
fs_row = res[(res.spec == "fs")].iloc[0]
check(abs(slope - fs_row.estimate) < 1e-4, f"binned-scatter slope {slope} != first-stage estimate {fs_row.estimate}")
fig, ax = plt.subplots(figsize=(6, 4.2))
xs = np.linspace(b.x.min(), b.x.max(), 2)
ax.plot(xs, slope * xs, color=AXIS, lw=1.5, zorder=1)
ax.plot(b.x, b.y, "o", ms=8, color=BLUE, mec=SURFACE, mew=2, zorder=2)
ax.annotate(f"slope {fs_row.estimate:.2f} (SE {fs_row.std_error:.2f})", (0.03, 0.92), xycoords="axes fraction",
            fontsize=9, color=INK2)
ax.grid(color=GRID, lw=0.6)
ax.set_xlabel("Local price index (others in the sampling unit), net of FE")
ax.set_ylabel("Own reported value per m², net of FE")
fig.suptitle("Owners' own valuations track local prices", x=0.01, ha="left", fontsize=11, fontweight="bold")
fig.text(0.01, -0.03, f"Owners in 2006, {len(fs):,} person-rounds; 20 equal-sized bins of the residualized "
         "index; person and year fixed effects removed. Log scales.", fontsize=8, color=MUTED)
fig.tight_layout()
fig.savefig(FIG / "fig6_first_stage.png", bbox_inches="tight")
plt.close(fig)
plotted += [{"figure": "fig6", "series": "bin", "x": round(float(x), 4), "y": round(float(y), 4)}
            for x, y in zip(b.x, b.y)]

# == FIGURE 7: REDUCED FORM ACROSS SPECIFICATIONS AND PRICE INDICES =========
SPECS = [("Person + unit-by-year FE", "s2", "r2"), ("+ age-group-by-year FE", "s3", "r3"),
         ("+ age FE, without Moscow / St Petersburg", "s5", "r5"), ("+ owner-by-year FE (preferred, D19)", "s7", "r7")]
INDICES = [("Survey-based local index (38 units)", "treat", 0, BLUE, -0.14),
           ("Rosstat regional prices (32 regions)", "treat_region", 1, ORANGE, 0.14)]
OUTS = [("idx_trust_state", "Trust in state institutions"), ("idx_democracy", "Democratic values")]
fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.6), sharey=True)
for ax, (outcome, title) in zip(axes, OUTS):
    for k, (lbl, s_int, s_reg) in enumerate(SPECS):
        for name, term, j, col, off in INDICES:
            row = res[(res.outcome == outcome) & (res.spec == (s_int, s_reg)[j]) & (res.term == term)]
            check(len(row) == 1, f"fig7: expected one row for {outcome} {(s_int, s_reg)[j]}")
            row = row.iloc[0]
            y = k + off
            ax.plot([row.estimate - 1.96 * row.std_error, row.estimate + 1.96 * row.std_error], [y, y], color=col,
                    lw=2, solid_capstyle="round")
            ax.plot(row.estimate, y, "o", ms=7, color=col, mec=SURFACE, mew=2)
            ax.annotate(f"p={row.wild_p:.2f}", (1, y), xycoords=("axes fraction", "data"), xytext=(4, 0),
                        textcoords="offset points", va="center", fontsize=7.5, color=MUTED)
            plotted.append({"figure": "fig7", "series": f"{outcome}|{(s_int, s_reg)[j]}", "x": k,
                            "y": round(float(row.estimate), 4)})
    ax.axvline(0, color=AXIS, lw=1, zorder=0)
    ax.set_xlim(-0.55, 0.4)
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_title(title, loc="left", fontsize=10)
    ax.set_xlabel("SD change per log point of price")
    ax.tick_params(axis="y", length=0)
axes[0].set_yticks(range(len(SPECS)), [lbl for lbl, _, _ in SPECS])
axes[0].invert_yaxis()
handles = [matplotlib.lines.Line2D([], [], color=c, marker="o", lw=2, label=n) for n, _, _, c, _ in INDICES]
fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.01, 0.93), ncol=2, frameon=False, fontsize=8)
fig.suptitle("Once owners' general trend is removed (bottom row), no positive effect of prices remains",
             x=0.01, ha="left", fontsize=11, fontweight="bold")
fig.text(0.01, -0.06, "Coefficient on owner-in-2006 × log price, relative to non-owners in the same sampling unit and "
         "year; 95% CIs; p = wild cluster bootstrap (units or regions). RLMS 2006, 2012, 2017, 2018.",
         fontsize=8, color=MUTED)
fig.tight_layout(rect=(0, 0, 0.93, 0.9))
fig.savefig(FIG / "fig7_housing_reduced_form.png", bbox_inches="tight")
plt.close(fig)

# == FIGURE 8: EVENT STUDY AROUND THE 2008-09 REGIONAL PRICE BUST ===========
es = pd.read_csv(root / "empirics/results/analyze_event_study.csv")
pt = pd.read_csv(root / "empirics/results/analyze_event_study_pretrends.csv").set_index("outcome")
OUTS8 = [("econ_sat", "Satisfaction with own economic situation"), ("life_sat", "Life satisfaction")]
fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.6), sharey=True)
for ax, (outcome, title) in zip(axes, OUTS8):
    d = es[(es.outcome == outcome) & (es.spec == "es")].copy()
    d["year"] = d.term.str[3:].astype(int)
    d = pd.concat([d, pd.DataFrame({"year": [2007], "estimate": [0.0], "std_error": [0.0]})]).sort_values("year")
    check(len(d) == 11, f"fig8: expected 11 years for {outcome}, found {len(d)}")
    ax.axvspan(2007.5, 2009.5, color="#f0efec", zorder=0)
    ax.fill_between(d.year, d.estimate - 1.96 * d.std_error, d.estimate + 1.96 * d.std_error, color=BLUE,
                    alpha=0.15, lw=0)
    ax.plot(d.year, d.estimate, color=BLUE, lw=2, marker="o", ms=6, mec=SURFACE, mew=1.5)
    ax.axhline(0, color=AXIS, lw=1, zorder=1)
    ax.set_title(title, loc="left", fontsize=10)
    ax.text(0.02, 0.95, f"pre-2007 joint test p = {pt.loc[outcome, 'p_value']:.2f}", transform=ax.transAxes,
            fontsize=8, color=MUTED, va="top")
    ax.set_xticks([2003, 2005, 2007, 2009, 2011, 2013])
    ax.grid(axis="y", color=GRID, lw=0.6)
    plotted.extend({"figure": "fig8", "series": outcome, "x": int(y), "y": round(float(v), 4)}
                   for y, v in zip(d.year, d.estimate))
axes[0].set_ylabel("Points on 1-5 scale per log point\nof regional price change 2008-09")
axes[0].text(2008.5, axes[0].get_ylim()[1] * 0.85, "bust", ha="center", fontsize=8, color=MUTED)
fig.suptitle("No clear break for owners in regions where prices fell more in 2008-09", x=0.01, ha="left",
             fontsize=11, fontweight="bold")
fig.text(0.01, -0.05, "Coefficient by year on owner-in-2006 × regional log price change 2008-2009 (2007 = 0; positive = owners do better where prices held up), with person, "
         "unit-by-year and age-group-by-year FE; 95% CIs clustered by region (32). RLMS 2003-2013.",
         fontsize=8, color=MUTED)
fig.tight_layout()
fig.savefig(FIG / "fig8_event_study.png", bbox_inches="tight")
plt.close(fig)

write_table(log, pd.DataFrame(plotted), f"empirics/results/{EXERCISE}.csv", sort_by=["figure", "series", "x"])
log.info("end")
