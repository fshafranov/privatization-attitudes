"""
01_analyze_housing_attitudes.py
Stage:      analysis (D1-D4)
Purpose:    TODO: what is estimated, in one sentence (the estimand, not just "regressions").
Reproduces: TODO: paper, Table X columns 1-N (or "n/a: original analysis")
Specs:      s1 OLS -> s2 + controls -> s3 + fixed effects -> s4 IV (simple to complex)
SEs:        TODO: clustering level and why (ANALYSIS_PLAN.md D#)
Reads:      data/processed/<workfile>/<workfile>.csv
Writes:     empirics/results/analyze_housing_attitudes.csv, empirics/results/warnings/analyze_housing_attitudes.md,
            empirics/results/logs/analyze_housing_attitudes.log
"""
import sys
import warnings
from pathlib import Path

import pandas as pd
import pyfixest as pf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis_config import WORKFILE, script_name  # noqa: E402  (+ KEY, EXPECTED_N, VCOV, ...)
from pipeline import (check, check_sample_consistency, get_logger, project_root,  # noqa: E402
                      tidy_model, write_table)

EXERCISE = script_name(__file__)   # results/log name without the NN_ prefix
KEY = []                 # unit of observation (or import from analysis_config)
EXPECTED_N = None        # exact; update deliberately when the workfile changes
REQUIRED = []            # every variable any spec uses
VCOV = "hetero"          # or {"CRV1": "state"}; ANALYSIS_PLAN.md D#

log = get_logger(EXERCISE, log_dir="empirics/results/logs")
root = project_root()
df = pd.read_csv(root / WORKFILE)

# == INPUT ASSERTIONS (D2) ==================================================
check(len(df) == EXPECTED_N, f"expected N={EXPECTED_N}, workfile has {len(df)}")
check(df.duplicated(KEY).sum() == 0, f"unit of observation {KEY} not unique")
missing = [v for v in REQUIRED if v not in df.columns]
check(not missing, f"required variables missing from workfile: {missing}")
sample = df.dropna(subset=REQUIRED).copy()  # one common sample for all specs (D4)
log.info("estimation_sample", rows=len(sample), of=len(df), complete_on=REQUIRED)

results, caught = [], []


def fit(fml: str, spec: str, data: pd.DataFrame, label: str = "main"):
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        m = pf.feols(fml, data=data, vcov=VCOV)
    caught.extend(f"{spec}: {x.message}" for x in w)
    log.info("spec", spec=spec, formula=fml, nobs=int(m._N))
    results.append(tidy_model(m, spec, sample=label))
    return m


# == SPEC 1: BASELINE OLS ===================================================
# fit("y ~ x", "s1_ols", sample)

# == SPEC 2: ADD CONTROLS ===================================================
# fit("y ~ x + c1 + c2", "s2_controls", sample)

# == SPEC 3: FIXED EFFECTS ==================================================
# fit("y ~ x + c1 + c2 | city + year", "s3_fe", sample)

# == SPEC 4: IV =============================================================
# fit("y ~ c1 + c2 | city + year | x ~ z", "s4_iv", sample)

# == EXPORT AND CONSISTENCY (D3, D4) ========================================
out = pd.concat(results, ignore_index=True)
write_table(log, out, f"empirics/results/analyze_housing_attitudes.csv", sort_by=["spec", "term"])
check_sample_consistency(log, out, EXERCISE, caught)
log.info("end")
