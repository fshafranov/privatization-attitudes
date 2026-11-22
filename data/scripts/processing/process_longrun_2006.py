"""
process_longrun_2006.py
Stage:      processing (C1-C4)
Purpose:    One row per adult asked the 2006 privatization-revision item (j223), with each
            person's 1990s history: workplace share ownership, household housing
            privatization, 1980s cooperative membership, plus controls.
Reads:      data/clean/rlms/rlms_ind.csv, data/clean/rlms/rlms_hh.csv
Writes:     data/processed/longrun_2006/longrun_2006.csv,
            data/processed/longrun_2006/longrun_2006_dropped.csv, data/logs/process_longrun_2006.log
Unit:       person (idind), 2006 round
Decisions:  ANALYSIS_PLAN.md D1-D6
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
from pipeline import AttritionTracker, check, checked_merge, get_logger, log_shape, project_root, summarize_var, write_table  # noqa: E402

OUT = Path("data/processed/longrun_2006")
log = get_logger("process_longrun_2006")
root = project_root()
ind = pd.read_csv(root / "data/clean/rlms/rlms_ind.csv")
hh = pd.read_csv(root / "data/clean/rlms/rlms_hh.csv")
log_shape(log, ind, "rlms_ind")
log_shape(log, hh, "rlms_hh")

# == PHASE 1: SAMPLE SELECTION ===============================================
base = ind[ind.year == 2006].copy()
tr = AttritionTracker(log, base, "2006 round, all individuals")
base = tr.filter(base, base.age >= 18, "age 18+ (adult questionnaire)")
base = tr.filter(base, base.j223.notna(), "j223 asked and answered or DK")  # ANALYSIS_PLAN.md D1
tr.summary()
tr.write_dropped(str(OUT / "longrun_2006_dropped.csv"), sort_by=["idind"])

# == PHASE 2: HISTORIES (MERGES) =============================================
# Shares: ANALYSIS_PLAN.md D2. j26 is asked of the employed only.
sh = ind[ind.j26.isin([1, 2])][["idind", "year", "j26"]]
early = sh[sh.year <= 1996].groupby("idind").j26.agg(share_early=lambda s: int((s == 1).any())).reset_index()
later = sh[sh.year.between(1998, 2005)].groupby("idind").j26.agg(share_later=lambda s: int((s == 1).any())).reset_index()
hist = checked_merge(log, early, later, on="idind", how="left", validate="1:1", name="shares early x later")

# Housing: ANALYSIS_PLAN.md D3. Person's household in each 1994-2002 round -> household c2.
link = ind[ind.year <= 2002][["idind", "id_w", "id_h"]].dropna()
link = link.astype({"id_h": "int64"})
hh_c2 = hh[hh.c2.isin([1, 2])][["id_h", "id_w", "c2"]]
ph = checked_merge(log, link, hh_c2, on=["id_h", "id_w"], how="inner", validate="m:1", name="person x household c2")
ph = ph.sort_values(["idind", "id_w"])
def housing_path(s):
    s = s.to_numpy()
    if len(s) < 2:
        return np.nan
    if s[0] == 1:
        return "privatized_at_first_obs"
    # first observed unprivatized: became privatized if the last two observations say so (persistence)
    if (s[-1] == 1) and (len(s) == 2 or s[-2] == 1):
        return "became_privatized"
    if (s == 2).all():
        return "never_privatized"
    return "unclear"
hpath = ph.groupby("idind").c2.agg(housing_path=housing_path).reset_index()

df = checked_merge(log, base, hist, on="idind", how="left", validate="1:1", name="2006 x shares")
df = checked_merge(log, df, hpath, on="idind", how="left", validate="1:1", name="2006 x housing")

# == PHASE 3: VARIABLE CONSTRUCTION ==========================================
valid = df.j223.isin([1, 2, 3, 4])
df["revise"] = np.where(valid, df.j223.isin([3, 4]).astype(float), np.nan)  # ANALYSIS_PLAN.md D1
df["nationalize"] = np.where(valid, (df.j223 == 3).astype(float), np.nan)
df["dont_know"] = (df.j223 == 7).astype(float)
for i, name in [(1, "rich_by_work"), (3, "rich_by_crime"), (4, "rich_by_connections")]:
    df[name] = (df[f"j210_{i}"] == i).astype(float)  # multi-select: chosen = code, not chosen = blank
df["share_owner_early"] = df.share_early                                # ANALYSIS_PLAN.md D2
df["lost_shares"] = np.where(df.share_early == 1, (df.share_later == 0).astype(float), np.nan)
df.loc[(df.share_early == 1) & df.share_later.isna(), "lost_shares"] = np.nan  # not observed employed later
df["coop_1980s"] = df.j224.map({1: 1.0, 2: 0.0})                       # ANALYSIS_PLAN.md D4
df["female"] = (df.h5 == 2).astype(float)
df["age2"] = df.age ** 2 / 100
df["log_income"] = np.log1p(df.j60.clip(lower=0))                      # ANALYSIS_PLAN.md D5
df["educ_group"] = df.diplom
df["settlement"] = df.status

# -- Attitude indices (ANALYSIS_PLAN.md D7): Kling-Liebman-Katz mean of z-scores ---------------
# Each component is signed so that higher = more of the index concept; z-scores use the mean and
# SD of this 2006 adult sample; a person needs at least half of an index's components.
asked214 = df[[f"j214_{i:02d}" for i in range(1, 11)]].notna().any(axis=1)
asked211 = df[[f"j211_0{i}" for i in range(1, 8)]].notna().any(axis=1)
pick = lambda col, code, asked: ((df[col] == code).astype(float)).where(asked)
rev5 = lambda col: 6 - df[col]  # 1-5 scale where 1 = strongly agree / very important / fully trust
COMPONENTS = {
    "idx_market_legit": {
        "keep_scale": df.j223.map({1: 4, 2: 3, 4: 2, 3: 1}),  # 4 = leave with owners ... 1 = return to state
        "rich_by_work": df.rich_by_work, "rich_not_crime": 1 - df.rich_by_crime,
        "rich_not_connections": 1 - df.rich_by_connections,
        "millionaire_hard_work": pick("j211_01", 1, asked211),
        "millionaire_not_criminal": 1 - ((df.j211_06 == 6) | (df.j211_07 == 7)).astype(float).where(asked211),
        "not_return_to_state": 1 - pick("j214_06", 6, asked214),
        "not_price_regulation": 1 - pick("j214_04", 4, asked214),
        "no_need_reduce_inequality": pick("j214_10", 10, asked214),
    },
    "idx_democracy": {
        "free_elections": rev5("j208_1"), "free_speech": rev5("j208_3"), "free_press": rev5("j208_4"),
        "opposition": rev5("j208_5"), "two_term_limit": rev5("j209_1"), "against_appointed_governors": df.j209_2,
    },
    "idx_trust_state": {f"trust_{n}": rev5(c) for n, c in [("government", "j207_1"), ("duma", "j207_2"),
                        ("courts", "j207_3"), ("army", "j207_5"), ("police", "j207_6"), ("parties", "j207_11")]},
    "idx_state_approval": {"national_govt_responsive": rev5("j209_3"), "regional_govt_responsive": rev5("j209_4"),
                           "corruption_declined": rev5("j209_5")},
}
for idx, comps in COMPONENTS.items():
    z = pd.DataFrame({k: (v - v.mean()) / v.std() for k, v in comps.items()})
    k = z.shape[1]
    raw = z.mean(axis=1).where(z.notna().sum(axis=1) >= k / 2)
    df[idx] = (raw - raw.mean()) / raw.std()
    zc = z.dropna()
    alpha = k / (k - 1) * (1 - zc.var().sum() / zc.sum(axis=1).var()) if len(zc) > 1 else np.nan
    log.info("index", var=idx, components=list(comps), n=int(df[idx].notna().sum()),
             complete_cases=len(zc), cronbach_alpha=round(float(alpha), 3),
             corr_with_revise=round(float(df[idx].corr(df.revise)), 3))
    summarize_var(log, df, idx)

for v, lo, hi in [("revise", 0, 1), ("nationalize", 0, 1), ("dont_know", 0, 1), ("rich_by_crime", 0, 1),
                  ("share_owner_early", 0, 1), ("lost_shares", 0, 1), ("coop_1980s", 0, 1),
                  ("age", 18, 110), ("log_income", 0, None)]:
    summarize_var(log, df, v, lower=lo, upper=hi)
log.info("housing_path", counts=df.housing_path.value_counts(dropna=False).to_dict())
check(df.idind.is_unique, "idind not unique in workfile")

keep = ["idind", "psu", "region", "settlement", "age", "age2", "female", "educ_group", "log_income",
        "j223", "revise", "nationalize", "dont_know", "rich_by_work", "rich_by_crime", "rich_by_connections",
        "share_owner_early", "lost_shares", "housing_path", "coop_1980s",
        "idx_market_legit", "idx_democracy", "idx_trust_state", "idx_state_approval"]
write_table(log, df[keep], str(OUT / "longrun_2006.csv"), sort_by=["idind"])
log.info("end")
