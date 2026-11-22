"""
09_robust_permutation.py
Stage:      analysis, robustness R3
Purpose:    Randomization inference for the preferred political specification (r7: owner_2006 x log
            regional price | person + unit-by-year + age-group-by-year + owner-by-year FE). Each of the 32 regions'
            price paths (2006, 2012, 2017, 2018) is reassigned to a random region; the permutation
            p-value is the share of permuted |coefficients| at least as large as the actual one.
            Complements the wild bootstrap with few clusters.
Reproduces: n/a: original analysis
Reads:      data/processed/housing_wealth/housing_wealth.csv
Writes:     empirics/results/robust_permutation.csv, empirics/results/robust_permutation_draws.csv,
            empirics/results/logs/robust_permutation.log
Decisions:  ANALYSIS_PLAN.md D19 (owner-by-year FE; this test revealed the need for them)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis_config import SEED, script_name  # noqa: E402
from pipeline import check, get_logger, project_root, write_table  # noqa: E402

EXERCISE = script_name(__file__)
WORKFILE = Path("data/processed/housing_wealth/housing_wealth.csv")
OUTCOMES = ["idx_trust_state", "idx_democracy", "trust_government"]
N_PERM = 1999
log = get_logger(EXERCISE, log_dir="empirics/results/logs")
root = project_root()
df = pd.read_csv(root / WORKFILE, dtype={"okato11": str})

# == SAMPLE (common to all outcomes so one permuted regressor serves all) =====
panel = df[df.groupby("idind").year.transform("size") >= 2].dropna(subset=OUTCOMES + ["log_p_region"]).copy()
panel["psu_year"] = panel.psu.astype(int) * 10000 + panel.year
panel["age_year"] = panel.age_bin + "_" + panel.year.astype(str)
panel["owner_year"] = panel.owner_2006.astype(int).astype(str) + "_" + panel.year.astype(str)
codes = [pd.factorize(panel[f])[0] for f in ["idind", "psu_year", "age_year", "owner_year"]]  # D19
log.info("sample", rows=len(panel), persons=int(panel.idind.nunique()), regions=int(panel.okato11.nunique()))


def demean(x, tol=1e-9, max_iter=2000):
    """Fast alternating projections on the fixed effects (numpy bincount)."""
    x = x.astype(float).copy()
    counts = [np.bincount(c) for c in codes]
    for _ in range(max_iter):
        prev = x.copy()
        for c, n in zip(codes, counts):
            x -= (np.bincount(c, weights=x) / n)[c]
        if np.abs(x - prev).max() < tol:
            return x
    raise RuntimeError("demeaning did not converge")


ry = {o: demean(panel[o].to_numpy()) for o in OUTCOMES}
owner = panel.owner_2006.to_numpy()
prices = panel.drop_duplicates(["okato11", "year"]).pivot(index="okato11", columns="year", values="log_p_region")
check(prices.notna().all().all(), "every region needs a price in every round")
regions = prices.index.to_numpy()
ridx = pd.Index(regions).get_indexer(panel.okato11)
yidx = pd.Index(prices.columns).get_indexer(panel.year)
P = prices.to_numpy()


def coefs(perm):
    rx = demean(owner * P[perm[ridx], yidx])
    return {o: float(ry[o] @ rx / (rx @ rx)) for o in OUTCOMES}


actual = coefs(np.arange(len(regions)))
rng = np.random.default_rng(SEED)
draws = [coefs(rng.permutation(len(regions))) for _ in range(N_PERM)]
dr = pd.DataFrame(draws)
rows = []
for o in OUTCOMES:
    p = (1 + int((dr[o].abs() >= abs(actual[o]) - 1e-12).sum())) / (N_PERM + 1)
    rows.append({"outcome": o, "spec": "r7", "estimate": actual[o], "perm_p": p, "n_perm": N_PERM,
                 "perm_sd": float(dr[o].std()), "perm_mean": float(dr[o].mean()), "nobs": len(panel)})
    log.info("permutation", outcome=o, estimate=round(actual[o], 4), perm_p=round(p, 4))
write_table(log, pd.DataFrame(rows), f"empirics/results/{EXERCISE}.csv", sort_by=["outcome"])
write_table(log, dr.assign(draw=range(N_PERM)), f"empirics/results/{EXERCISE}_draws.csv", sort_by=["draw"])
log.info("end")
