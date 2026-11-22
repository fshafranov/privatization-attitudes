"""
01_analyze_longrun_2006.py
Stage:      analysis (D1-D4)
Purpose:    Conditional associations between 1990s privatization histories (early workplace
            share ownership; losing those shares; household housing privatization; 1980s
            cooperative membership) and 2006 support for revising privatization (j223) and
            beliefs that the rich got rich by crime (j210_3). Descriptive, not causal.
Reproduces: n/a: original analysis (outcome wording follows Denisova et al., APSR 2009, LiTS 2006)
Specs:      s1 bivariate -> s2 + demographic and income controls -> s3 + region fixed effects
SEs:        clustered by PSU, the RLMS primary sampling unit (ANALYSIS_PLAN.md D6)
Reads:      data/processed/longrun_2006/longrun_2006.csv
Writes:     empirics/results/analyze_longrun_2006.csv, empirics/results/warnings/analyze_longrun_2006.md,
            empirics/results/logs/analyze_longrun_2006.log
"""
import sys
import warnings
from pathlib import Path

import pandas as pd
import pyfixest as pf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis_config import CONTROLS, EXPECTED_N, KEY, VCOV, WORKFILE, script_name  # noqa: E402
from pipeline import check, check_sample_consistency, get_logger, project_root, tidy_model, write_table  # noqa: E402

EXERCISE = script_name(__file__)
OUTCOMES = ["revise", "rich_by_crime", "dont_know",  # single items
            "idx_market_legit", "idx_democracy", "idx_trust_state", "idx_state_approval"]  # D7 indices (SD units)
log = get_logger(EXERCISE, log_dir="empirics/results/logs")
root = project_root()
df = pd.read_csv(root / WORKFILE)

# == INPUT ASSERTIONS (D2) ==================================================
check(len(df) == EXPECTED_N, f"expected N={EXPECTED_N}, workfile has {len(df)}")
check(df.duplicated(KEY).sum() == 0, f"unit of observation {KEY} not unique")
need = OUTCOMES + ["share_owner_early", "lost_shares", "housing_path", "coop_1980s", "region", "psu"] + \
    ["age", "age2", "female", "educ_group", "settlement", "log_income"]
missing = [v for v in need if v not in df.columns]
check(not missing, f"required variables missing: {missing}")

# housing dummies, reference = never privatized; 'unclear' paths excluded (ANALYSIS_PLAN.md D3)
df["became_privatized"] = (df.housing_path == "became_privatized").astype(float)
df["privatized_at_first_obs"] = (df.housing_path == "privatized_at_first_obs").astype(float)
df.loc[~df.housing_path.isin(["became_privatized", "privatized_at_first_obs", "never_privatized"]),
       ["became_privatized", "privatized_at_first_obs"]] = float("nan")

BLOCKS = {  # sample label -> regressors (each block has its own comparison group)
    "shares_early": ["share_owner_early"],
    "shares_lost": ["lost_shares"],
    "housing": ["became_privatized", "privatized_at_first_obs"],
    "coop": ["coop_1980s"],
}
ctrl = " + ".join(CONTROLS)
results, caught = [], []
for outcome in OUTCOMES:
    for block, xs in BLOCKS.items():
        sample = df.dropna(subset=[outcome] + xs + ["age", "female", "educ_group", "settlement", "log_income", "psu"])
        label = f"{outcome}|{block}"
        log.info("estimation_sample", outcome=outcome, block=block, rows=len(sample))
        rhs = " + ".join(xs)
        # == SPEC s1: BIVARIATE ==================================================
        # == SPEC s2: + CONTROLS =================================================
        # == SPEC s3: + REGION FIXED EFFECTS =====================================
        specs = {"s1": f"{outcome} ~ {rhs}", "s2": f"{outcome} ~ {rhs} + {ctrl}",
                 "s3": f"{outcome} ~ {rhs} + {ctrl} | region"}
        for spec, fml in specs.items():
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                res = pf.feols(fml, data=sample, vcov=VCOV)
            caught += [f"{label} {spec}: {x.message}" for x in w]
            t = tidy_model(res, spec, sample=label, fe="region" if spec == "s3" else "")
            t["outcome"], t["block"], t["mean_dep"] = outcome, block, float(sample[outcome].mean())
            results.append(t[t.term.isin(xs)])

out = pd.concat(results, ignore_index=True)

# == MULTIPLE TESTING (ANALYSIS_PLAN.md D8) ==================================
# Benjamini-Hochberg q-values within the family "s3 x four indices x five history terms"
fam = (out.spec == "s3") & out.outcome.str.startswith("idx_")
p = out.loc[fam, "p_value"].sort_values()
m = len(p)
check(m == 20, f"expected 20 tests in the index family, found {m}")
q = (p * m / range(1, m + 1))[::-1].cummin()[::-1].clip(upper=1)
out["q_value_bh"] = q.reindex(out.index)
out["holm_reject_05"] = pd.Series(dtype="float64")
holm = (p * [m - i for i in range(m)]).cummax().clip(upper=1)
out.loc[fam, "holm_reject_05"] = (holm.reindex(out.index[fam]) < 0.05).astype(float)
log.info("multiple_testing", family_size=m, min_q=round(float(q.min()), 4),
         n_q_below_10=int((q < 0.10).sum()), n_holm_reject=int((holm < 0.05).sum()))

check_sample_consistency(log, out, EXERCISE, caught)
write_table(log, out, f"empirics/results/{EXERCISE}.csv", sort_by=["outcome", "block", "spec", "term"])
log.info("end")
