"""
process_housing_panel.py
Stage:      processing (C1-C4)
Purpose:    TODO: what analysis-ready workfile this builds and for which exercises.
Reads:      data/clean/<dataset>/<dataset>.csv, ...
Writes:     data/processed/housing_panel/housing_panel.csv, data/processed/housing_panel/housing_panel_dropped.csv,
            data/logs/process_housing_panel.log
Unit:       TODO: unit of observation of the output (e.g. city x year)
Decisions:  ANALYSIS_PLAN.md D# (every filter threshold, join type, construction choice)
"""
import sys
from pathlib import Path

import numpy as np  # noqa: F401
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
from pipeline import (AttritionTracker, check, checked_merge, get_logger,  # noqa: E402,F401
                      log_shape, project_root, summarize_var, write_table)

WORKFILE = "housing_panel"
OUT = Path("data/processed") / WORKFILE / f"housing_panel.csv"
KEY = []

log = get_logger(f"process_housing_panel")
root = project_root()

# == LOAD ===================================================================
# a = pd.read_csv(root / "data/clean/<dataset>/<dataset>.csv"); log_shape(log, a, "clean <dataset>")

# == PHASE 1: SAMPLE SELECTION ==============================================
# att = AttritionTracker(log, a, "clean <dataset>")
# a = att.filter(a, a["age"].between(25, 65), "F1 age 25-65 (ANALYSIS_PLAN.md D#)")
# att.summary()
# att.write_dropped(f"data/processed/housing_panel/housing_panel_dropped.csv")  # every excluded row + reason

# == PHASE 2: MERGE / RESHAPE ===============================================
# df = checked_merge(log, a, b, on=["fips"], how="left", validate="m:1", name="a x b")  # left: ANALYSIS_PLAN.md D#

# == PHASE 3: VARIABLE CONSTRUCTION =========================================
# df["log_employment"] = np.log(df["employment"].where(df["employment"] > 0))  # zeros -> NaN: ANALYSIS_PLAN.md D#
# summarize_var(log, df, "log_employment", inputs=["employment"])

# == FINAL CHECKS AND WRITE =================================================
# check(df.duplicated(KEY).sum() == 0, f"output key {KEY} not unique")
# write_table(log, df, str(OUT), sort_by=KEY)
log.info("end")
