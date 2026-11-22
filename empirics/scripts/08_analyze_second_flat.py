"""
08_analyze_second_flat.py
Stage:      analysis (D1-D4)
Purpose:    Heterogeneity: households owning a second flat in 2006 hold housing wealth that can be
            sold or rented out, so price changes should matter more for them. Estimates the extra
            response of second-flat households to the regional price, on top of the owner response.
              h1: y ~ treat_region + second_x_price | person + unit-by-year + age-by-year FE (all)
              h2: y ~ second_x_price | same FE, owners in 2006 only (second-flat owners vs single-flat owners)
Reproduces: n/a: original analysis
SEs:        clustered by region (32); wild cluster bootstrap via FWL (D12)
Reads:      data/processed/housing_wealth/housing_wealth.csv
Writes:     empirics/results/analyze_second_flat.csv, empirics/results/warnings/analyze_second_flat.md,
            empirics/results/logs/analyze_second_flat.log
Decisions:  ANALYSIS_PLAN.md D18
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pyfixest as pf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis_config import script_name, wild_p_fwl  # noqa: E402
from pipeline import check, check_sample_consistency, get_logger, project_root, tidy_model, write_table  # noqa: E402

EXERCISE = script_name(__file__)
WORKFILE = Path("data/processed/housing_wealth/housing_wealth.csv")
FES = ["idind", "psu_year", "age_year", "owner_year"]  # ANALYSIS_PLAN.md D19
CL = "okato11"
log = get_logger(EXERCISE, log_dir="empirics/results/logs")
root = project_root()
df = pd.read_csv(root / WORKFILE)

# == INPUT ASSERTIONS ========================================================
check(not df.duplicated(["idind", "year"]).any(), "idind x year not unique")
panel = df[(df.groupby("idind").year.transform("size") >= 2) & df.second_flat_2006.notna()].copy()
panel["psu_year"] = panel.psu.astype(int) * 10000 + panel.year
panel["age_year"] = panel.age_bin + "_" + panel.year.astype(str)
panel["owner_year"] = panel.owner_2006.astype(int).astype(str) + "_" + panel.year.astype(str)
panel["second_x_price"] = panel.second_flat_2006 * panel.log_p_region
u = panel.drop_duplicates("idind")
log.info("groups", persons=len(u), second_flat=int(u.second_flat_2006.sum()),
         second_flat_owners=int(((u.second_flat_2006 == 1) & (u.owner_2006 == 1)).sum()))

results, caught = [], []
for outcome in ["idx_trust_state", "idx_democracy", "trust_government"]:
    for spec, data, terms in [("h1", panel, ["treat_region", "second_x_price"]),
                              ("h2", panel[panel.owner_2006 == 1], ["second_x_price"])]:
        d = data.dropna(subset=[outcome])
        with warnings.catch_warnings(record=True) as wr:
            warnings.simplefilter("always")
            res = pf.feols(f"{outcome} ~ {' + '.join(terms)} | {' + '.join(FES)}", data=d, vcov={"CRV1": CL})
        caught.extend(f"{outcome} {spec}: {x.message}" for x in wr)
        t = tidy_model(res, spec, sample=f"{outcome}|{spec}")
        t["outcome"], t["wild_p"] = outcome, np.nan
        for term in terms:
            try:
                b, pw = wild_p_fwl(d, outcome, term, [x for x in terms if x != term], FES, CL)
                check(abs(b - float(res.coef()[term])) < 1e-6, f"FWL mismatch {outcome} {spec} {term}")
                t.loc[t.term == term, "wild_p"] = pw
            except Exception as e:
                caught.append(f"{outcome} {spec}: wild bootstrap failed for {term}: {e}")
        results.append(t)

out = pd.concat(results, ignore_index=True)
check_sample_consistency(log, out, EXERCISE, caught)
write_table(log, out, f"empirics/results/{EXERCISE}.csv", sort_by=["outcome", "spec", "term"])
log.info("end")
