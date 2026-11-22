"""
03_analyze_housing_wealth.py
Stage:      analysis (D1-D4)
Purpose:    Trial run of the housing-wealth design: do 2006 owners' attitudes move with local
            house prices relative to non-owners in the same PSU and year?
            (a) spread of local price changes across PSUs; (b) first stage: owners' own
            reported value per m2 on the leave-out local index; (c) reduced form: attitude
            indices on owner_2006 x log local price, person FE + PSU-by-year FE + age-bin-by-year FE.
Reproduces: n/a: original analysis (design follows Campbell & Cocco 2006; Ansell 2014)
SEs:        clustered by PSU (38 clusters) plus wild cluster bootstrap p-values (ANALYSIS_PLAN.md D12)
Reads:      data/processed/housing_wealth/housing_wealth.csv, data/processed/housing_wealth/price_index.csv
            (external regional price columns from D13 are in the workfile)
Writes:     empirics/results/analyze_housing_wealth.csv, empirics/results/analyze_housing_wealth_prices.csv,
            empirics/results/warnings/analyze_housing_wealth.md, empirics/results/logs/analyze_housing_wealth.log
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
WORKFILE = Path("data/processed/housing_wealth/housing_wealth.csv")
log = get_logger(EXERCISE, log_dir="empirics/results/logs")
root = project_root()
df = pd.read_csv(root / WORKFILE)
pi = pd.read_csv(root / "data/processed/housing_wealth/price_index.csv")

# == INPUT ASSERTIONS ========================================================
check(not df.duplicated(["idind", "year"]).any(), "idind x year not unique")
check(set(df.year) == {2006, 2012, 2017, 2018}, f"unexpected years {sorted(set(df.year))}")
check(df.psu.nunique() == 38, f"expected 38 PSUs, found {df.psu.nunique()}")

# == (a) PRICE VARIATION ACROSS PSUs =========================================
w = pi.pivot(index="psu", columns="id_w", values="log_p")
chg = pd.DataFrame({"d_2006_2012": w[21] - w[15], "d_2012_2018": w[27] - w[21], "d_2006_2018": w[27] - w[15]})
prices = chg.describe().T[["mean", "std", "min", "max"]].reset_index().rename(columns={"index": "change"})
rw = df.drop_duplicates(["okato11", "year"]).pivot(index="okato11", columns="year", values="log_p_region")
rchg = pd.DataFrame({"region_d_2006_2012": rw[2012] - rw[2006], "region_d_2012_2018": rw[2018] - rw[2012],
                     "region_d_2006_2018": rw[2018] - rw[2006]})
prices = pd.concat([prices, rchg.describe().T[["mean", "std", "min", "max"]].reset_index().rename(columns={"index": "change"})])
log.info("region_price_changes", corr_with_psu_index=round(float(
    df.groupby(["psu", "year"])[["log_p_local", "log_p_region"]].mean().diff().dropna().corr().iloc[0, 1]), 3))
write_table(log, prices, f"empirics/results/{EXERCISE}_prices.csv", sort_by=["change"])
log.info("price_changes", table="\n" + prices.round(3).to_string(index=False),
         corr_changes=round(float(chg.d_2006_2012.corr(chg.d_2012_2018)), 3))

results, caught = [], []


def run(fml, data, spec, label, outcome, boot_param=None, cluster="psu"):
    with warnings.catch_warnings(record=True) as wr:
        warnings.simplefilter("always")
        res = pf.feols(fml, data=data, vcov={"CRV1": cluster})
    caught.extend(f"{label} {spec}: {x.message}" for x in wr)
    t = tidy_model(res, spec, sample=label)
    t["outcome"], t["mean_dep"], t["wild_p"], t["cluster"] = outcome, float(data[outcome].mean()), np.nan, cluster
    if boot_param is not None:
        try:  # wild cluster bootstrap on FWL-residualized data (few clusters); ANALYSIS_PLAN.md D12
            fes = [f.strip() for f in fml.split("|")[1].split("+")]
            others = [x for x in fml.split("~")[1].split("|")[0].replace(" ", "").split("+") if x != boot_param]
            d = data.dropna(subset=[outcome, boot_param] + others)
            r = demean(d, [outcome, boot_param] + others, fes)
            if others:  # partial out the other regressors too (FWL)
                b = np.linalg.lstsq(r[others].to_numpy(), r[[outcome, boot_param]].to_numpy(), rcond=None)[0]
                r[[outcome, boot_param]] = r[[outcome, boot_param]].to_numpy() - r[others].to_numpy() @ b
            r = r[[outcome, boot_param]].rename(columns={outcome: "ry", boot_param: "rx"})
            r[cluster] = pd.factorize(d[cluster])[0]  # integer codes: the bootstrap cannot take strings
            fwl = pf.feols("ry ~ rx", data=r, vcov={"CRV1": cluster})
            check(abs(float(fwl.coef()["rx"]) - float(res.coef()[boot_param])) < 1e-6,
                  f"FWL coefficient differs from FE estimate in {label} {spec}")
            wb = fwl.wildboottest(param="rx", reps=9999, seed=SEED)
            check(np.isfinite(float(wb["t value"])), f"bootstrap t is not finite in {label} {spec}")
            t.loc[t.term == boot_param, "wild_p"] = float(wb["Pr(>|t|)"])
        except Exception as e:  # report CRV1 only and log why the bootstrap failed
            caught.append(f"{label} {spec}: wild bootstrap failed: {e}")
    results.append(t)


# == (b) FIRST STAGE: OWNERS' OWN VALUATION ON THE LEAVE-OUT LOCAL INDEX =====
fs = df[(df.owner_2006 == 1) & df.log_value_m2_own.notna()].copy()
fs = fs[fs.groupby("idind").year.transform("size") >= 2]
log.info("first_stage_sample", rows=len(fs), persons=int(fs.idind.nunique()))
run("log_value_m2_own ~ log_p_local | idind + year", fs, "fs", "first_stage", "log_value_m2_own", "log_p_local")
# external Rosstat regional price (ANALYSIS_PLAN.md D13), clustered by region
run("log_value_m2_own ~ log_p_region | idind + year", fs, "fs_region", "first_stage", "log_value_m2_own",
    "log_p_region", cluster="okato11")

# == (c) REDUCED FORM ========================================================
panel = df[df.groupby("idind").year.transform("size") >= 2].copy()
panel["psu_year"] = panel.psu.astype(int) * 10000 + panel.year      # explicit interactions: the bootstrap
panel["age_year"] = panel.age_bin + "_" + panel.year.astype(str)  # cannot parse a^b fixed-effect syntax
panel["owner_year"] = panel.owner_2006.astype(int).astype(str) + "_" + panel.year.astype(str)  # D19
log.info("panel_sample", rows=len(panel), persons=int(panel.idind.nunique()),
         owners=int(panel.drop_duplicates("idind").owner_2006.sum()))
for outcome in ["idx_trust_state", "idx_democracy", "trust_government"]:
    d = panel.dropna(subset=[outcome])
    # s1: person + year FE (price main effect identified, region shocks not absorbed)
    run(f"{outcome} ~ treat + log_p_local | idind + year", d, "s1", "reduced_form", outcome)
    # s2: person + PSU-by-year FE: owners vs non-owners in the same place and year
    run(f"{outcome} ~ treat | idind + psu_year", d, "s2", "reduced_form", outcome, "treat")
    # s3: + age-bin-by-year FE (life-cycle trends differ between owners and non-owners)
    run(f"{outcome} ~ treat | idind + psu_year + age_year", d, "s3", "reduced_form", outcome, "treat")
    # s4: exposure in roubles (2006 floor space x local price), same FE as s3
    run(f"{outcome} ~ exposure | idind + psu_year + age_year", d, "s4", "reduced_form", outcome, "exposure")
    # s5: drop Moscow City and St Petersburg (PSUs 1, 2): booming and politically distinct
    run(f"{outcome} ~ treat | idind + psu_year + age_year", d[~d.psu.isin([1, 2])], "s5",
        "reduced_form_no_capitals", outcome, "treat")
    # r2-r5: same designs with the external Rosstat regional price (D13), clustered by region (32)
    run(f"{outcome} ~ treat_region | idind + psu_year", d, "r2", "reduced_form_region", outcome, "treat_region", "okato11")
    run(f"{outcome} ~ treat_region | idind + psu_year + age_year", d, "r3", "reduced_form_region", outcome,
        "treat_region", "okato11")
    run(f"{outcome} ~ exposure_region | idind + psu_year + age_year", d, "r4", "reduced_form_region", outcome,
        "exposure_region", "okato11")
    run(f"{outcome} ~ treat_region | idind + psu_year + age_year", d[~d.psu.isin([1, 2])], "r5",
        "reduced_form_region_no_capitals", outcome, "treat_region", "okato11")
    # r6: r3 + owner x local income (D16): separates housing prices from a general regional boom
    run(f"{outcome} ~ treat_region + owner_x_local_inc | idind + psu_year + age_year", d, "r6",
        "reduced_form_region_income", outcome, "treat_region", "okato11")
    # r7/s7: + owner-by-year FE (D19): removes the general owner/non-owner trend that owner x log price
    # otherwise picks up because prices rose almost everywhere; only cross-regional price differences remain
    run(f"{outcome} ~ treat | idind + psu_year + age_year + owner_year", d, "s7", "reduced_form_owner_trend",
        outcome, "treat")
    run(f"{outcome} ~ treat_region | idind + psu_year + age_year + owner_year", d, "r7", "reduced_form_owner_trend",
        outcome, "treat_region", "okato11")
    run(f"{outcome} ~ treat_region + owner_x_local_inc | idind + psu_year + age_year + owner_year", d, "r8",
        "reduced_form_owner_trend_income", outcome, "treat_region", "okato11")

out = pd.concat(results, ignore_index=True)
out = out[out.term.isin(["log_p_local", "treat", "exposure", "log_p_region", "treat_region", "exposure_region"])]
check_sample_consistency(log, out[out["sample"].isin(["reduced_form", "reduced_form_region"])].assign(sample=lambda x: x["sample"] + "|" + x.outcome), EXERCISE, caught)
write_table(log, out, f"empirics/results/{EXERCISE}.csv", sort_by=["sample", "outcome", "spec", "term"])
log.info("end")
