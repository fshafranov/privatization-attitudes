"""
process_housing_wealth.py
Stage:      processing (C1-C4)
Purpose:    Person-round panel for 2006, 2012, 2017, 2018 (the rounds asking trust and
            democratic-values items) with 2006 housing tenure, a local house-price index, and
            attitude indices on a common scale.
Reads:      data/clean/rlms/rlms_ind.csv, data/clean/rlms/rlms_hh.csv,
            data/clean/housing_prices/secondary_prices.csv, data/scripts/processing/psu_region_crosswalk.csv
Writes:     data/processed/housing_wealth/housing_wealth.csv,
            data/processed/housing_wealth/housing_wealth_dropped.csv,
            data/processed/housing_wealth/price_index.csv, data/logs/process_housing_wealth.log
Unit:       person-round (idind, year)
Decisions:  ANALYSIS_PLAN.md D9-D13, D16-D18
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
from pipeline import AttritionTracker, check, checked_merge, get_logger, log_shape, project_root, summarize_var, write_table  # noqa: E402

OUT = Path("data/processed/housing_wealth")
YEARS = [2006, 2012, 2017, 2018]
ROUND = {2006: 15, 2012: 21, 2017: 26, 2018: 27}  # RLMS id_w for each year
TRUST = ["j207_1", "j207_2", "j207_3", "j207_5", "j207_6", "j207_11"]
DEMOC = ["j208_1", "j208_3", "j208_4", "j208_5"]  # j209 items exist in 2006 only
log = get_logger("process_housing_wealth")
root = project_root()
ind = pd.read_csv(root / "data/clean/rlms/rlms_ind.csv",
                  usecols=["idind", "id_w", "id_h", "year", "age", "h5", "diplom", "j60", "j1", "j23", "marst"] + TRUST + DEMOC)
hh = pd.read_csv(root / "data/clean/rlms/rlms_hh.csv")
check(all(ind.loc[ind.year == y, "id_w"].eq(w).all() for y, w in ROUND.items()), "round numbers do not match years")

# == PHASE 1: LOCAL PRICE INDEX (ANALYSIS_PLAN.md D10) =======================
# Owners' self-reported market value per m2 of floor space, leave-one-household-out mean of
# logs within PSU x round. Trimmed at the 1st/99th percentile of log value per m2 by round.
h = hh[hh.id_w.isin(ROUND.values()) & (hh.c1 == 1) & hh.c1_1.gt(0) & hh.c6.gt(0)].copy()
h["lv"] = np.log(h.c1_1 / h.c6)
lo, hi = h.groupby("id_w").lv.transform(lambda s: s.quantile(0.01)), h.groupby("id_w").lv.transform(lambda s: s.quantile(0.99))
h = h[h.lv.between(lo, hi)]
# Unit errors (values in thousands, or extra zeros) survive a national trim: drop reports more
# than 5x away from their PSU-round median (ANALYSIS_PLAN.md D10, amended 2026-11-22)
med = h.groupby(["psu", "id_w"]).lv.transform("median")
n_before = len(h)
h = h[(h.lv - med).abs() <= np.log(5)]
log.info("unit_error_trim", dropped=n_before - len(h), kept=len(h), rule="|log v - PSU-round median| <= log 5")
g = h.groupby(["psu", "id_w"]).lv
h["n_psu"] = g.transform("size")
h["log_p_loo"] = (g.transform("sum") - h.lv) / (h.n_psu - 1)
psu_idx = h.groupby(["psu", "id_w"]).agg(log_p=("lv", "mean"), n_owners=("lv", "size")).reset_index()
check(psu_idx.n_owners.min() >= 10, f"a PSU-round has fewer than 10 owners reporting value: {psu_idx.n_owners.min()}")
write_table(log, psu_idx, str(OUT / "price_index.csv"), sort_by=["psu", "id_w"])
log.info("price_index", psu_rounds=len(psu_idx), min_owners=int(psu_idx.n_owners.min()),
         sd_log_p_by_round=psu_idx.groupby("id_w").log_p.std().round(3).to_dict())

# == PHASE 2: SAMPLE AND MERGES ==============================================
p = ind[ind.year.isin(YEARS)].copy()
p = checked_merge(log, p, hh[["id_h", "id_w", "psu", "status", "nfm1_n", "c1", "c4_0", "c1_1", "c6", "c9_12a"]], on=["id_h", "id_w"],
                  how="left", validate="m:1", name="person x household")
tr = AttritionTracker(log, p, "person-rounds 2006/2012/2017/2018")
p = tr.filter(p, p.age >= 18, "age 18+")
# baseline tenure in 2006 (ANALYSIS_PLAN.md D9)
b = p[p.year == 2006][["idind", "id_h", "c1", "c4_0", "c6", "psu", "diplom", "j60", "j1", "j23", "marst", "status", "nfm1_n",
                       "c9_12a"]].rename(columns={"psu": "psu_2006", "c6": "space_2006"})
b["owner_2006"] = np.select(
    [(b.c1 == 1) & (b.c4_0 == 1), b.c1.isin([2, 3]) | b.c4_0.isin([2, 3])], [1.0, 0.0], default=np.nan)
p = tr.filter(p, p.idind.isin(b.idind), "observed as adult in 2006 (baseline)")
# 2006 baseline characteristics for flexible baseline-by-year controls (ANALYSIS_PLAN.md D17);
# missing values become their own category so no observation is lost
cat = lambda s: s.map(lambda x: "missing" if pd.isna(x) else str(int(x)))
b["b_educ"] = cat(b.diplom)
inc3 = pd.qcut(b.j60.where(b.j60 > 0), 3, labels=["low", "mid", "high"]).astype(object)
b["b_inc"] = inc3.where(inc3.notna(), "none")
b["b_work"] = cat(b.j1)
b["b_state_job"] = cat(b.j23)
b["b_marst"] = cat(b.marst)
b["b_settle"] = cat(b.status)
# household size = people with an individual record in the household in 2006 (nfm1_n is asked of
# only about a fifth of households)
hh_n = ind[ind.year == 2006].groupby("id_h").size()
size = pd.cut(b.id_h.map(hh_n), [0, 1, 2, 3, 4, 99], labels=["1", "2", "3", "4", "5+"]).astype(object)
b["b_hhsize"] = size.where(size.notna(), "missing")
b["second_flat_2006"] = np.where(b.c9_12a.isin([1, 2]), (b.c9_12a == 1).astype(float), np.nan)  # D18
BASE = ["b_educ", "b_inc", "b_work", "b_state_job", "b_marst", "b_settle", "b_hhsize"]
p = p.merge(b[["idind", "owner_2006", "space_2006", "psu_2006", "second_flat_2006"] + BASE], on="idind", how="left",
            validate="m:1")
p = tr.filter(p, p.owner_2006.notna(), "2006 tenure classifiable (own vs not)")
p = tr.filter(p, p.psu == p.psu_2006, "same PSU as in 2006 (D9: movers dropped)")
p = checked_merge(log, p, h[["id_h", "id_w", "log_p_loo"]], on=["id_h", "id_w"], how="left", validate="m:1",
                  name="person x own-household leave-out index")
p = checked_merge(log, p, psu_idx[["psu", "id_w", "log_p"]], on=["psu", "id_w"], how="left", validate="m:1",
                  name="person x PSU index")
p["log_p_local"] = p.log_p_loo.fillna(p.log_p)  # leave-out when the household itself reported, else PSU mean
p = tr.filter(p, p.log_p_local.notna(), "local price index available")
# External regional prices (ANALYSIS_PLAN.md D13): PSU -> region crosswalk, Rosstat Q4 price per m2
cw = pd.read_csv(Path(__file__).resolve().parent / "psu_region_crosswalk.csv", dtype={"okato11": str})
rp = pd.read_csv(root / "data/clean/housing_prices/secondary_prices.csv", dtype={"okato11": str})
names = rp.drop_duplicates("okato11").set_index("okato11").region
bad = [r.psu for r in cw.itertuples() if r.region_check not in str(names.get(r.okato11, ""))]
check(not bad, f"crosswalk region names do not match the price file for PSUs {bad}")
check(cw.psu.is_unique and set(cw.psu) == set(range(1, 39)), "crosswalk must list PSUs 1-38 once")
p = checked_merge(log, p, cw[["psu", "okato11"]], on="psu", how="left", validate="m:1", name="person x PSU-region crosswalk")
p = checked_merge(log, p, rp[["okato11", "year", "price_rub_m2"]], on=["okato11", "year"], how="left",
                  validate="m:1", name="person x regional price")
p = tr.filter(p, p.price_rub_m2.notna(), "regional price available")
tr.summary()
tr.write_dropped(str(OUT / "housing_wealth_dropped.csv"), sort_by=["idind", "year"])

# == PHASE 3: VARIABLE CONSTRUCTION ==========================================
# Indices on a fixed scale: z-scores against the 2006 adult distribution, so changes over
# time are kept (ANALYSIS_PLAN.md D11). Items 1-5 reversed so higher = more trust / importance.
base06 = p[p.year == 2006]
for name, items in [("idx_trust_state", TRUST), ("idx_democracy", DEMOC)]:
    z = pd.DataFrame({c: ((6 - p[c]) - (6 - base06[c]).mean()) / (6 - base06[c]).std() for c in items})
    p[name] = z.mean(axis=1).where(z.notna().sum(axis=1) >= len(items) / 2)
    summarize_var(log, p, name)
p["trust_government"] = 6 - p.j207_1
p["treat"] = p.owner_2006 * p.log_p_local                       # ANALYSIS_PLAN.md D12
p["exposure"] = p.owner_2006 * p.space_2006 * np.exp(p.log_p_local) / 1e6  # rub millions of baseline housing
p["log_p_region"] = np.log(p.price_rub_m2)                       # ANALYSIS_PLAN.md D13
p["treat_region"] = p.owner_2006 * p.log_p_region
p["exposure_region"] = p.owner_2006 * p.space_2006 * p.price_rub_m2 / 1e6
# ANALYSIS_PLAN.md D16: leave-one-out PSU-year mean of log(1 + personal income), interacted with owner
p["log_inc"] = np.log1p(p.j60.clip(lower=0))
g = p.groupby(["psu", "year"]).log_inc
p["local_inc"] = (g.transform("sum") - p.log_inc.fillna(0)) / (g.transform("count") - p.log_inc.notna())
p["owner_x_local_inc"] = p.owner_2006 * p.local_inc
summarize_var(log, p, "local_inc", lower=0)
p["log_value_m2_own"] = np.where((p.c1 == 1) & (p.c1_1 > 0) & (p.c6 > 0), np.log(p.c1_1 / p.c6), np.nan)
p["age_bin"] = pd.cut(p.age, [17, 30, 45, 60, 120], labels=["18-30", "31-45", "46-60", "61+"]).astype(str)
p["female"] = (p.h5 == 2).astype(float)
for v, lo_, hi_ in [("treat", 0, None), ("owner_2006", 0, 1), ("log_p_local", 5, 15)]:
    summarize_var(log, p, v, lower=lo_, upper=hi_)
check(not p.duplicated(["idind", "year"]).any(), "idind x year not unique")
log.info("panel", persons=int(p.idind.nunique()), rounds_per_person=p.groupby("idind").size().value_counts().to_dict(),
         owners_2006_share=round(float(p.drop_duplicates("idind").owner_2006.mean()), 3))
keep = ["idind", "year", "psu", "okato11", "owner_2006", "space_2006", "log_p_local", "treat", "exposure",
        "log_p_region", "treat_region", "exposure_region", "local_inc", "owner_x_local_inc", "log_value_m2_own",
        "idx_trust_state", "idx_democracy", "trust_government", "age", "age_bin", "female", "diplom",
        "second_flat_2006"] + BASE
write_table(log, p[keep], str(OUT / "housing_wealth.csv"), sort_by=["idind", "year"])
log.info("end")
