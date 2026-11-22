"""
07_robust_flexible_controls.py
Stage:      analysis, robustness R2
Purpose:    Does the owner x regional price coefficient survive flexible controls for how owners and
            non-owners differ? Adds 2006 baseline characteristics x year dummies (education, income
            tercile, work status, state employer, marital status, settlement type, household size) to
            the preferred political specification r7 (r3 + owner-by-year FE, D19):
              f1 all interactions (OLS); f2 post-double-selection LASSO (Belloni, Chernozhukov & Hansen
              2014) on FE-residualized data, selection folds grouped by region; f3 = f1 + owner x local income.
Reproduces: n/a: original analysis
SEs:        clustered by region (32); wild cluster bootstrap p-values via FWL (D12)
Reads:      data/processed/housing_wealth/housing_wealth.csv
Writes:     empirics/results/robust_flexible_controls.csv, empirics/results/robust_flexible_controls_selected.csv,
            empirics/results/warnings/robust_flexible_controls.md, empirics/results/logs/robust_flexible_controls.log
Decisions:  ANALYSIS_PLAN.md D17
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pyfixest as pf
from sklearn.linear_model import LassoCV
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis_config import demean, script_name, wild_p_fwl  # noqa: E402
from pipeline import check, check_sample_consistency, get_logger, project_root, tidy_model, write_table  # noqa: E402

EXERCISE = script_name(__file__)
WORKFILE = Path("data/processed/housing_wealth/housing_wealth.csv")
BASE = ["b_educ", "b_inc", "b_work", "b_state_job", "b_marst", "b_settle", "b_hhsize"]
FES = ["idind", "psu_year", "age_year", "owner_year"]  # ANALYSIS_PLAN.md D19
CL = "okato11"
log = get_logger(EXERCISE, log_dir="empirics/results/logs")
root = project_root()
df = pd.read_csv(root / WORKFILE, dtype={b: str for b in BASE})

# == INPUT ASSERTIONS ========================================================
check(not df.duplicated(["idind", "year"]).any(), "idind x year not unique")
check(df[BASE].notna().all().all(), "baseline categories must have explicit missing levels")
panel = df[df.groupby("idind").year.transform("size") >= 2].copy()
panel["psu_year"] = panel.psu.astype(int) * 10000 + panel.year
panel["age_year"] = panel.age_bin + "_" + panel.year.astype(str)
panel["owner_year"] = panel.owner_2006.astype(int).astype(str) + "_" + panel.year.astype(str)

# baseline x year dummies (2006 is the reference year; levels relative to the first category)
cols = []
for v in BASE:
    dm = pd.get_dummies(panel[v], prefix=v, drop_first=True, dtype=float)
    for y in (2012, 2017, 2018):
        for c in dm.columns:
            name = f"x_{c}_{y}".replace(".", "_").replace("+", "plus").replace("-", "_")
            panel[name] = dm[c] * (panel.year == y)
            cols.append(name)
cols = [c for c in cols if panel[c].sum() >= 20]  # drop near-empty cells
log.info("candidate_controls", n=len(cols))

results, selected, caught = [], [], []
for outcome in ["idx_trust_state", "idx_democracy", "trust_government"]:
    d = panel.dropna(subset=[outcome, "treat_region", "owner_x_local_inc"])
    fe = " + ".join(FES)
    specs = {
        "r7": [],
        "f1": cols,
        "f3": cols + ["owner_x_local_inc"],
    }
    # == SPEC f2: POST-DOUBLE-SELECTION LASSO ================================
    r = demean(d, [outcome, "treat_region"] + cols, FES)
    X = r[cols].to_numpy()
    X = (X - X.mean(0)) / np.where(X.std(0) > 0, X.std(0), 1)
    groups = pd.factorize(d[CL])[0]
    keep = set()
    for target in [outcome, "treat_region"]:
        cv = list(GroupKFold(n_splits=5).split(X, groups=groups))
        las = LassoCV(cv=cv, alphas=np.logspace(-5, 0, 50), max_iter=5000, random_state=0).fit(X, r[target].to_numpy())
        keep |= {cols[j] for j in np.flatnonzero(las.coef_)}
    specs["f2"] = sorted(keep)
    selected += [{"outcome": outcome, "control": c} for c in sorted(keep)]
    log.info("pds_selected", outcome=outcome, n=len(keep))
    for spec, ctrl in specs.items():
        fml = f"{outcome} ~ treat_region" + ("" if not ctrl else " + " + " + ".join(ctrl)) + f" | {fe}"
        with warnings.catch_warnings(record=True) as wr:
            warnings.simplefilter("always")
            res = pf.feols(fml, data=d, vcov={"CRV1": CL})
        caught.extend(f"{outcome} {spec}: {x.message}" for x in wr)
        t = tidy_model(res, spec, sample=outcome)
        t = t[t.term == "treat_region"].copy()
        t["outcome"], t["n_controls"], t["wild_p"] = outcome, len(ctrl), np.nan
        try:
            b, pw = wild_p_fwl(d, outcome, "treat_region", ctrl, FES, CL)
            check(abs(b - float(res.coef()["treat_region"])) < 1e-6, f"FWL mismatch {outcome} {spec}")
            t["wild_p"] = pw
        except Exception as e:
            caught.append(f"{outcome} {spec}: wild bootstrap failed: {e}")
        results.append(t)

out = pd.concat(results, ignore_index=True)
check_sample_consistency(log, out, EXERCISE, caught)
write_table(log, out, f"empirics/results/{EXERCISE}.csv", sort_by=["outcome", "spec"])
write_table(log, pd.DataFrame(selected), f"empirics/results/{EXERCISE}_selected.csv", sort_by=["outcome", "control"])
log.info("end")
