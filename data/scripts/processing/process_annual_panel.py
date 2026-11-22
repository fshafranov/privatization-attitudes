"""
process_annual_panel.py
Stage:      processing (C1-C4)
Purpose:    Person-year panel 2003-2018 for outcomes asked every year (life satisfaction,
            satisfaction with one's economic situation; generalized trust where asked), with 2006
            tenure, regional house prices, the 2008-09 regional price bust as an event-study
            exposure, and the leave-one-out local mean of log income.
Reads:      data/clean/rlms/rlms_ind.csv, data/clean/rlms/rlms_hh.csv,
            data/clean/housing_prices/secondary_prices.csv, data/scripts/processing/psu_region_crosswalk.csv
Writes:     data/processed/annual_panel/annual_panel.csv, data/processed/annual_panel/annual_panel_dropped.csv,
            data/logs/process_annual_panel.log
Unit:       person-year (idind, year)
Decisions:  ANALYSIS_PLAN.md D9 (tenure), D13 (prices), D14-D16
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
from pipeline import AttritionTracker, check, checked_merge, get_logger, log_shape, project_root, summarize_var, write_table  # noqa: E402

OUT = Path("data/processed/annual_panel")
YEARS = range(2003, 2019)
EVENT_YEARS = [y for y in range(2003, 2014) if y != 2007]  # 2007 = reference year (D15)
log = get_logger("process_annual_panel")
root = project_root()
ind = pd.read_csv(root / "data/clean/rlms/rlms_ind.csv",
                  usecols=["idind", "id_w", "id_h", "year", "age", "h5", "j60", "j65", "j66_1", "j206"])
hh = pd.read_csv(root / "data/clean/rlms/rlms_hh.csv", usecols=["id_h", "id_w", "psu", "c1", "c4_0"])
cw = pd.read_csv(Path(__file__).resolve().parent / "psu_region_crosswalk.csv", dtype={"okato11": str})
rp = pd.read_csv(root / "data/clean/housing_prices/secondary_prices.csv", dtype={"okato11": str})

# == PHASE 1: SAMPLE SELECTION ===============================================
p = ind[ind.year.isin(YEARS)].copy()
p = checked_merge(log, p, hh, on=["id_h", "id_w"], how="left", validate="m:1", name="person x household")
tr = AttritionTracker(log, p, "person-years 2003-2018")
p = tr.filter(p, p.age >= 18, "age 18+")
b = p[p.year == 2006][["idind", "c1", "c4_0", "psu"]].rename(columns={"psu": "psu_2006"})
b["owner_2006"] = np.select([(b.c1 == 1) & (b.c4_0 == 1), b.c1.isin([2, 3]) | b.c4_0.isin([2, 3])],
                            [1.0, 0.0], default=np.nan)  # ANALYSIS_PLAN.md D9
p = tr.filter(p, p.idind.isin(b.idind), "observed as adult in 2006 (baseline)")
p = p.merge(b[["idind", "owner_2006", "psu_2006"]], on="idind", how="left", validate="m:1")
p = tr.filter(p, p.owner_2006.notna(), "2006 tenure classifiable (own vs not)")
p = tr.filter(p, p.psu == p.psu_2006, "same PSU as in 2006")

# == PHASE 2: MERGES =========================================================
p = checked_merge(log, p, cw[["psu", "okato11"]], on="psu", how="left", validate="m:1", name="person x crosswalk")
p = checked_merge(log, p, rp[["okato11", "year", "price_rub_m2"]], on=["okato11", "year"], how="left",
                  validate="m:1", name="person x regional price (2004 has no price data)")
w = rp.pivot(index="okato11", columns="year", values="price_rub_m2")
bust = np.log(w[2009] / w[2008]).rename("bust_0809").reset_index()  # ANALYSIS_PLAN.md D15
p = checked_merge(log, p, bust, on="okato11", how="left", validate="m:1", name="person x 2008-09 regional bust")
check(p.bust_0809.notna().all(), "2008-09 price change missing for a region in the sample")
tr.summary()
tr.write_dropped(str(OUT / "annual_panel_dropped.csv"), sort_by=["idind", "year"])

# == PHASE 3: VARIABLE CONSTRUCTION ==========================================
p["life_sat"] = 6 - p.j65            # 1 = not at all ... 5 = fully satisfied (D14)
p["econ_sat"] = 6 - p.j66_1
p["trust_people"] = np.where(p.j206.isin([1, 2, 3]), (p.j206 == 1).astype(float), np.nan)
p["log_p_region"] = np.log(p.price_rub_m2)
p["treat_region"] = p.owner_2006 * p.log_p_region
for y in EVENT_YEARS:                # event-study regressors (D15)
    p[f"es_{y}"] = p.owner_2006 * p.bust_0809 * (p.year == y)
p["post_bust"] = p.owner_2006 * p.bust_0809 * p.year.between(2009, 2013)
# ANALYSIS_PLAN.md D16: leave-one-out PSU-year mean of log(1 + personal income last 30 days)
p["log_inc"] = np.log1p(p.j60.clip(lower=0))
g = p.groupby(["psu", "year"]).log_inc
p["local_inc"] = (g.transform("sum") - p.log_inc.fillna(0)) / (g.transform("count") - p.log_inc.notna())
p["owner_x_local_inc"] = p.owner_2006 * p.local_inc
p["age_bin"] = pd.cut(p.age, [17, 30, 45, 60, 120], labels=["18-30", "31-45", "46-60", "61+"]).astype(str)
p["psu_year"] = p.psu.astype(int) * 10000 + p.year
p["age_year"] = p.age_bin + "_" + p.year.astype(str)
for v, lo, hi in [("life_sat", 1, 5), ("econ_sat", 1, 5), ("trust_people", 0, 1), ("bust_0809", -1, 1),
                  ("local_inc", 0, None), ("owner_2006", 0, 1)]:
    summarize_var(log, p, v, lower=lo, upper=hi)
check(not p.duplicated(["idind", "year"]).any(), "idind x year not unique")
log.info("panel", persons=int(p.idind.nunique()), years=sorted(p.year.unique().tolist()),
         owners_2006_share=round(float(p.drop_duplicates("idind").owner_2006.mean()), 3))
keep = (["idind", "year", "psu", "okato11", "owner_2006", "age", "age_bin", "psu_year", "age_year",
         "life_sat", "econ_sat", "trust_people", "log_p_region", "treat_region", "bust_0809", "post_bust",
         "local_inc", "owner_x_local_inc"] + [f"es_{y}" for y in EVENT_YEARS])
write_table(log, p[keep], str(OUT / "annual_panel.csv"), sort_by=["idind", "year"])
log.info("end")
