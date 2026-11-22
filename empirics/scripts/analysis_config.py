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
