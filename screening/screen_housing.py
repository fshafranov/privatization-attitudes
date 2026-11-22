"""screen_housing.py — pre-pipeline feasibility screen (not part of run_all.py).

Purpose: count, by RLMS round, how often the housing-privatization items are asked and how
many households switch from unprivatized to privatized between rounds.
Reads: RLMS_HH_1994_2025_eng.dta (extracted from data/raw/rlms/RLMS_HH_1994_2025_eng_DTA.zip;
       path passed as argv[1]).
Writes: screening/results/housing_items_by_round.csv, screening/results/housing_transitions.csv,
        screening/results/housing_2025_retro.csv
Unit: household-round (id_h, id_w).
Run: uv run python -I screening/screen_housing.py <path to extracted .dta>
"""

import sys
from pathlib import Path

import pandas as pd
import pyreadstat

OUT = Path(__file__).resolve().parent / "results"
OUT.mkdir(exist_ok=True)

df, _ = pyreadstat.read_dta(sys.argv[1], usecols=["id_w", "id_h", "c1", "c2", "c21", "c22"])

# Item coverage by round
g = df.groupby("id_w")
cov = pd.DataFrame(
    {
        "n_households": g.size(),
        "c2_answered": g.c2.apply(lambda s: s.isin([1, 2]).sum()),
        "c2_privatized": g.c2.apply(lambda s: (s == 1).sum()),
        "c2_unprivatized": g.c2.apply(lambda s: (s == 2).sum()),
        "c22_answered": g.c22.apply(lambda s: s.between(1, 6).sum()),
    }
)
cov.to_csv(OUT / "housing_items_by_round.csv")

# Round-to-round transitions in c2
p = df[df.c2.isin([1, 2])][["id_h", "id_w", "c2"]].sort_values(["id_h", "id_w"])
if p.duplicated(["id_h", "id_w"]).any():
    raise ValueError("id_h not unique within round")
p["prev"] = p.groupby("id_h").c2.shift()
t = p.dropna(subset=["prev"])
# id_h is renumbered in round 6 (1995): 1994->1995 pairs would match unrelated households, so drop them
t = t[t.id_w != 6]
tr = pd.DataFrame(
    {
        "unpriv_to_priv": t.assign(x=(t.prev == 2) & (t.c2 == 1)).groupby("id_w").x.sum(),
        "priv_to_unpriv": t.assign(x=(t.prev == 1) & (t.c2 == 2)).groupby("id_w").x.sum(),
        "stay_unpriv": t.assign(x=(t.prev == 2) & (t.c2 == 2)).groupby("id_w").x.sum(),
    }
)
ever = p.groupby("id_h").c2.agg(lambda s: ((s.shift() == 2) & (s == 1)).any())
tr.loc["households_ever_switching"] = [int(ever.sum()), None, None]
tr.to_csv(OUT / "housing_transitions.csv")

# 2025 retrospective acquisition year for privatized homes
w = df[(df.id_w == 34) & (df.c22 == 4) & (df.c21 < 3000)]
bins = [1900, 1990, 1992, 1994, 1996, 1998, 2000, 2002, 2005, 2010, 2017, 2030]
retro = pd.cut(w.c21, bins).value_counts().sort_index().rename("n_households")
retro.to_csv(OUT / "housing_2025_retro.csv")
print(cov.to_string(), tr.to_string(), retro.to_string(), sep="\n\n")
