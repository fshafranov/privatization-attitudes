"""
11_robust_sign_diagnostics.py
Stage:      analysis, robustness R4
Purpose:    Explain why owner x log price changes sign once owner-by-year FE are added (D19).
            (a) owners' general trend: owner x year coefficients with no price term (2006 = 0);
            (b) where the treatment variation comes from: the national price path vs cross-regional
                deviations from it;
            (c) leave-one-region-out estimates of the preferred specification r7.
Reproduces: n/a: original analysis
SEs:        clustered by region (32)
Reads:      data/processed/housing_wealth/housing_wealth.csv
Writes:     empirics/results/robust_sign_diagnostics_trend.csv, empirics/results/robust_sign_diagnostics_prices.csv,
            empirics/results/robust_sign_diagnostics_loo.csv, empirics/results/robust_sign_diagnostics.csv,
            empirics/results/warnings/robust_sign_diagnostics.md, empirics/results/logs/robust_sign_diagnostics.log
Decisions:  ANALYSIS_PLAN.md D19, R4
"""
import sys
import warnings
from pathlib import Path

import pandas as pd
import pyfixest as pf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis_config import script_name  # noqa: E402
from pipeline import check, check_sample_consistency, get_logger, project_root, tidy_model, write_table  # noqa: E402

EXERCISE = script_name(__file__)
WORKFILE = Path("data/processed/housing_wealth/housing_wealth.csv")
OUTCOMES = ["idx_trust_state", "idx_democracy", "trust_government"]
CL = "okato11"
log = get_logger(EXERCISE, log_dir="empirics/results/logs")
root = project_root()
df = pd.read_csv(root / WORKFILE, dtype={"okato11": str})

# == INPUT ASSERTIONS ========================================================
check(not df.duplicated(["idind", "year"]).any(), "idind x year not unique")
panel = df[df.groupby("idind").year.transform("size") >= 2].dropna(subset=["log_p_region"]).copy()
panel["psu_year"] = panel.psu.astype(int) * 10000 + panel.year
panel["age_year"] = panel.age_bin + "_" + panel.year.astype(str)
panel["owner_year"] = panel.owner_2006.astype(int).astype(str) + "_" + panel.year.astype(str)
YEARS = (2012, 2017, 2018)
for y in YEARS:
    panel[f"owner_{y}"] = panel.owner_2006 * (panel.year == y)
check(panel[CL].nunique() == 32, f"expected 32 regions, found {panel[CL].nunique()}")

caught, trend, loo, main = [], [], [], []


def fit(fml, data):
    with warnings.catch_warnings(record=True) as wr:
        warnings.simplefilter("always")
        res = pf.feols(fml, data=data, vcov={"CRV1": CL})
    caught.extend(f"{fml}: {x.message}" for x in wr)
    return res


for outcome in OUTCOMES:
    d = panel.dropna(subset=[outcome])
    # == (a) OWNERS' GENERAL TREND (no price term) ===========================
    r = fit(f"{outcome} ~ {' + '.join(f'owner_{y}' for y in YEARS)} | idind + psu_year + age_year", d)
    t = tidy_model(r, "trend", sample=outcome)
    trend.append(t.assign(outcome=outcome))
    # == (c) PREFERRED r7 AND LEAVE-ONE-REGION-OUT ===========================
    fml = f"{outcome} ~ treat_region | idind + psu_year + age_year + owner_year"
    base = fit(fml, d)
    main.append(tidy_model(base, "r7", sample=outcome).assign(outcome=outcome))
    for reg in sorted(d[CL].unique()):
        r = fit(fml, d[d[CL] != reg])
        loo.append({"outcome": outcome, "dropped_region": reg, "estimate": float(r.coef()["treat_region"]),
                    "std_error": float(r.se()["treat_region"]), "nobs": int(r._N)})
    lo = pd.DataFrame([x for x in loo if x["outcome"] == outcome])
    log.info("leave_one_out", outcome=outcome, r7=round(float(base.coef()["treat_region"]), 4),
             min=round(float(lo.estimate.min()), 4), max=round(float(lo.estimate.max()), 4),
             n_negative=int((lo.estimate < 0).sum()), n_regions=len(lo))

# == (b) WHERE THE PRICE VARIATION COMES FROM ================================
w = panel.drop_duplicates([CL, "year"]).pivot(index=CL, columns="year", values="log_p_region")
chg = w.sub(w[2006], axis=0)
prices = pd.DataFrame({"year": w.columns, "national_mean_log_price": w.mean().to_numpy(),
                       "national_change_since_2006": chg.mean().to_numpy(),
                       "cross_region_sd_of_change": chg.std().to_numpy()})
log.info("price_variation", table="\n" + prices.round(3).to_string(index=False))

write_table(log, pd.concat(trend, ignore_index=True), f"empirics/results/{EXERCISE}_trend.csv", sort_by=["outcome", "term"])
write_table(log, prices, f"empirics/results/{EXERCISE}_prices.csv", sort_by=["year"])
write_table(log, pd.DataFrame(loo), f"empirics/results/{EXERCISE}_loo.csv", sort_by=["outcome", "dropped_region"])
out = pd.concat(main, ignore_index=True)
out = out[out.term == "treat_region"]
check_sample_consistency(log, out, EXERCISE, caught)
write_table(log, out, f"empirics/results/{EXERCISE}.csv", sort_by=["outcome"])
log.info("end")
