"""
analysis_config.py
Stage:      analysis: shared setup imported by every Python empirics script (like 00_setup.R).
Purpose:    One place for paths and global analysis choices, each with its ANALYSIS_PLAN.md ID.
Reads:      nothing
Writes:     nothing
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data" / "scripts" / "utils"))

WORKFILE = Path("data/processed/longrun_2006/longrun_2006.csv")
SEED = 20260101
KEY = ["idind"]
EXPECTED_N = 11607  # adults asked j223 in 2006 (process_longrun_2006.log attrition summary)
CONTROLS = ["age", "age2", "female", "C(educ_group)", "C(settlement)", "log_income"]  # ANALYSIS_PLAN.md D5
VCOV = {"CRV1": "psu"}  # ANALYSIS_PLAN.md D6


def demean(data, cols, fes, tol=1e-10, max_iter=500):
    """Residualize cols on several fixed effects by alternating projections (FWL)."""
    out = data[cols].astype(float).copy()
    for _ in range(max_iter):
        prev = out.copy()
        for fe in fes:
            out = out - out.groupby(data[fe]).transform("mean")
        if (out - prev).abs().to_numpy().max() < tol:
            return out
    raise RuntimeError("demeaning did not converge")


def script_name(file: str) -> str:
    """04_analyze_reaction_functions.py -> analyze_reaction_functions (results/log name)."""
    stem = Path(file).stem
    return stem.split("_", 1)[1] if stem[:2].isdigit() else stem


def wild_p_fwl(data, outcome, param, others, fes, cluster, reps=9999, seed=SEED):
    """Wild cluster bootstrap p-value for `param` after partialling out the fixed effects and the
    other regressors (Frisch-Waugh-Lovell); returns (coef, p). ANALYSIS_PLAN.md D12/D16."""
    import numpy as np
    import pandas as pd
    import pyfixest as pf

    d = data.dropna(subset=[outcome, param] + others)
    r = demean(d, [outcome, param] + others, fes)
    if others:
        b = np.linalg.lstsq(r[others].to_numpy(), r[[outcome, param]].to_numpy(), rcond=None)[0]
        r[[outcome, param]] = r[[outcome, param]].to_numpy() - r[others].to_numpy() @ b
    r = r[[outcome, param]].rename(columns={outcome: "ry", param: "rx"})
    r["cl"] = pd.factorize(d[cluster])[0]
    fw = pf.feols("ry ~ rx", data=r, vcov={"CRV1": "cl"})
    wb = fw.wildboottest(param="rx", reps=reps, seed=seed)
    if not np.isfinite(float(wb["t value"])):
        raise ValueError("non-finite bootstrap t-statistic")
    return float(fw.coef()["rx"]), float(wb["Pr(>|t|)"])
