"""
05_analyze_event_study.py
Stage:      analysis (D1-D4)
Purpose:    Annual-outcome tests of the housing-wealth design.
            (B) event study around the 2008-09 regional price bust: owner_2006 x (regional log price
                change 2008->2009) x year dummies, 2003-2013, 2007 omitted; pre-period coefficients
                test pre-trends; pooled post (2009-2013) vs pre version;
            (A) annual version of the main design, owner_2006 x log regional price, 2005-2018;
            (C) (A) plus owner x local income (separates housing from a general regional boom).
Reproduces: n/a: original analysis
SEs:        clustered by region (32), wild cluster bootstrap p-values on FWL-residualized data (D12)
Reads:      data/processed/annual_panel/annual_panel.csv
Writes:     empirics/results/analyze_event_study.csv, empirics/results/analyze_event_study_pretrends.csv,
            empirics/results/warnings/analyze_event_study.md, empirics/results/logs/analyze_event_study.log
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pyfixest as pf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis_config import SEED, demean, script_name  # noqa: E402
from pipeline import check, check_sample_consistency, get_logger, project_root, tidy_model, write_table  # noqa: E402

EXERCISE = script_name(__file__)
WORKFILE = Path("data/processed/annual_panel/annual_panel.csv")
EVENT_YEARS = [y for y in range(2003, 2014) if y != 2007]
ES = [f"es_{y}" for y in EVENT_YEARS]
PRE = [f"es_{y}" for y in EVENT_YEARS if y < 2007]
FE = "idind + psu_year + age_year"
CL = "okato11"
log = get_logger(EXERCISE, log_dir="empirics/results/logs")
root = project_root()
df = pd.read_csv(root / WORKFILE, dtype={"okato11": str})

# == INPUT ASSERTIONS ========================================================
check(not df.duplicated(["idind", "year"]).any(), "idind x year not unique")
check(df.okato11.nunique() == 32, f"expected 32 regions, found {df.okato11.nunique()}")
check(all(c in df for c in ES + ["post_bust", "treat_region", "owner_x_local_inc"]), "missing regressors")

results, pretests, caught = [], [], []


def fit(fml, data, spec, label, outcome, boot=None):
    with warnings.catch_warnings(record=True) as wr:
        warnings.simplefilter("always")
        res = pf.feols(fml, data=data, vcov={"CRV1": CL})
    caught.extend(f"{label} {spec}: {x.message}" for x in wr)
    t = tidy_model(res, spec, sample=label)
    t["outcome"], t["mean_dep"], t["wild_p"] = outcome, float(data[outcome].mean()), np.nan
    for param in boot or []:  # wild cluster bootstrap via FWL (D12); other regressors partialled out
        try:
            others = [x for x in fml.split("~")[1].split("|")[0].replace(" ", "").split("+") if x != param]
            d = data.dropna(subset=[outcome, param] + others)
            r = demean(d, [outcome, param] + others, [f.strip() for f in FE.split("+")])
            if others:  # partial out the other regressors too
                b = np.linalg.lstsq(r[others].to_numpy(), r[[outcome, param]].to_numpy(), rcond=None)[0]
                r[[outcome, param]] = r[[outcome, param]].to_numpy() - r[others].to_numpy() @ b
            r = r[[outcome, param]].rename(columns={outcome: "ry", param: "rx"})
            r[CL] = pd.factorize(d[CL])[0]  # integer cluster codes: the bootstrap cannot take strings
            fw = pf.feols("ry ~ rx", data=r, vcov={"CRV1": CL})
            check(abs(float(fw.coef()["rx"]) - float(res.coef()[param])) < 1e-6, f"FWL mismatch {label} {spec} {param}")
            wb = fw.wildboottest(param="rx", reps=9999, seed=SEED)
            check(np.isfinite(float(wb["t value"])), f"non-finite bootstrap t {label} {spec}")
            t.loc[t.term == param, "wild_p"] = float(wb["Pr(>|t|)"])
        except Exception as e:
            caught.append(f"{label} {spec}: wild bootstrap failed for {param}: {e}")
    results.append(t)
    return res


# == (B) EVENT STUDY AROUND THE 2008-09 BUST =================================
es_data = df[df.year.between(2003, 2013)]
for outcome in ["life_sat", "econ_sat"]:
    d = es_data.dropna(subset=[outcome])
    res = fit(f"{outcome} ~ {' + '.join(ES)} | {FE}", d, "es", "event_study", outcome)
    wt = res.wald_test(R=np.eye(len(ES))[[ES.index(c) for c in PRE]])  # joint test: pre-period coefs = 0
    pretests.append({"outcome": outcome, "test": "pre-2007 coefficients jointly zero", "df": len(PRE),
                     "statistic": float(wt.stat), "distribution": wt.distribution, "p_value": float(wt.pvalue)})
    fit(f"{outcome} ~ post_bust | {FE}", d[~d.year.between(2008, 2008)], "dd", "event_study_pooled", outcome,
        boot=["post_bust"])

# == (A) ANNUAL MAIN DESIGN AND (C) WITH LOCAL INCOME ========================
ann = df[df.year.between(2005, 2018) & df.log_p_region.notna()]
for outcome in ["life_sat", "econ_sat", "trust_people"]:
    d = ann.dropna(subset=[outcome])
    fit(f"{outcome} ~ treat_region | {FE}", d, "a1", "annual_main", outcome, boot=["treat_region"])
    fit(f"{outcome} ~ treat_region + owner_x_local_inc | {FE}", d.dropna(subset=["owner_x_local_inc"]), "a2",
        "annual_main_income", outcome, boot=["treat_region"])

out = pd.concat(results, ignore_index=True)
out = out[out.term.isin(ES + ["post_bust", "treat_region", "owner_x_local_inc"])]
check_sample_consistency(log, out.assign(sample=out["sample"] + "|" + out.outcome), EXERCISE, caught)
write_table(log, out, f"empirics/results/{EXERCISE}.csv", sort_by=["sample", "outcome", "spec", "term"])
write_table(log, pd.DataFrame(pretests), f"empirics/results/{EXERCISE}_pretrends.csv", sort_by=["outcome"])
log.info("end")
