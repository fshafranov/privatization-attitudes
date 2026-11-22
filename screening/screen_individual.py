"""screen_individual.py — pre-pipeline feasibility screen (not part of run_all.py).

Purpose: (a) which RLMS rounds carry each political / attitude item; (b) how many respondents
report owning shares of their employer, and how many later stop; (c) how many adults live in
households that switch from unprivatized to privatized and are asked a political item both
before and after the switch.
Reads: argv[1] individual subset pickle (made by data/scripts/utils/dta_stream.py from
       data/raw/rlms/RLMS_IND_1994_2025_eng_DTA.7z); argv[2] household housing pickle
       (id_w, id_h, c2) made from RLMS_HH_1994_2025_eng.dta.
Writes: screening/results/ind_item_coverage.csv, screening/results/shares_by_round.csv,
        screening/results/shares_transitions.csv, screening/results/housing_switch_overlap.csv
Unit: person-round (idind, id_w).
"""

import sys
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parent / "results"
OUT.mkdir(exist_ok=True)

ind = pd.read_pickle(sys.argv[1])
hh = pd.read_pickle(sys.argv[2])[["id_w", "id_h", "c2"]]
if ind.duplicated(["idind", "id_w"]).any():
    raise ValueError("idind not unique within round")

ID = ["id_w", "idind", "id_h", "year", "int_y", "region", "status", "h5", "age"]
items = [c for c in ind.columns if c not in ID]
valid = ind[items].lt(99999990) & ind[items].notna()  # RLMS codes 99999997-99999999 = DK/refuse/NA

# (a) coverage: valid answers per item per round, keep items x rounds with >= 100 answers
cov = valid.groupby(ind.year).sum().T
cov.to_csv(OUT / "ind_item_coverage.csv")

# (b) workplace share ownership: j26 1 = yes, 2 = no; j28 percent owned
sh = ind[ind.j26.isin([1, 2])][["idind", "id_w", "year", "j26", "j28", "j309"]].sort_values(["idind", "id_w"])
by = sh.groupby("year").agg(answered=("j26", "size"), owners=("j26", lambda s: (s == 1).sum()))
by.to_csv(OUT / "shares_by_round.csv")
sh["prev"] = sh.groupby("idind").j26.shift()
t = sh.dropna(subset=["prev"])
trans = pd.DataFrame(
    {
        "owner_to_nonowner": t.assign(x=(t.prev == 1) & (t.j26 == 2)).groupby("year").x.sum(),
        "owner_stays": t.assign(x=(t.prev == 1) & (t.j26 == 1)).groupby("year").x.sum(),
        "nonowner_to_owner": t.assign(x=(t.prev == 2) & (t.j26 == 1)).groupby("year").x.sum(),
    }
)
trans.to_csv(OUT / "shares_transitions.csv")

# (c) housing switchers x political items
p = hh[hh.c2.isin([1, 2])].sort_values(["id_h", "id_w"]).copy()
p["prev"] = p.groupby("id_h").c2.shift()
sw = p[(p.prev == 2) & (p.c2 == 1)].groupby("id_h").id_w.min().rename("switch_w")
# id_h is unique within round only; RLMS keeps id_h for the same household across rounds in the panel
m = ind.merge(sw, left_on="id_h", right_index=True, how="inner")
rows = []
for it in ["j104", "j102_3", "j118_5", "j207_1", "j137", "j140", "j223", "j107", "j410", "j69_7"]:
    if it not in ind.columns:
        continue
    ok = m[m[it].lt(99999990) & m[it].notna()]
    pre = set(ok[ok.id_w < ok.switch_w].idind)
    post = set(ok[ok.id_w >= ok.switch_w].idind)
    rows.append({"item": it, "people_pre": len(pre), "people_post": len(post), "people_both": len(pre & post)})
pd.DataFrame(rows).to_csv(OUT / "housing_switch_overlap.csv", index=False)

pd.set_option("display.width", 250)
c = cov.where(cov >= 100)
print(c.dropna(how="all").apply(lambda r: ",".join(str(int(y)) for y in r.dropna().index), axis=1).to_string())
print(by.to_string(), trans.to_string(), pd.DataFrame(rows).to_string(), sep="\n\n")

# (d) repeated-round items only: within-person before/after counts for both designs
REP = ["j69_5", "j69_7", "j107", "j110", "j68", "j67", "j65"]
ok = lambda d, it: d[d[it].lt(99999990) & d[it].notna()]
rows_h, rows_s = [], []
for it in REP:
    o = ok(m, it)
    pre, post = set(o[o.id_w < o.switch_w].idind), set(o[o.id_w >= o.switch_w].idind)
    rows_h.append({"item": it, "people_both": len(pre & post)})
# share losers: owner in round r-1, non-owner in round r; outcome observed in both r-1 and r
lose = t[(t.prev == 1) & (t.j26 == 2)][["idind", "id_w"]]
keep = t[(t.prev == 1) & (t.j26 == 1)][["idind", "id_w"]]
iw = ind.set_index(["idind", "id_w"])
waves = sorted(ind.id_w.unique())
prevw = dict(zip(waves[1:], waves[:-1]))
for it in REP:
    v = iw[it].where(iw[it].lt(99999990))
    def both(df):
        a = v.reindex(list(zip(df.idind, df.id_w)))
        b = v.reindex(list(zip(df.idind, df.id_w.map(prevw))))
        return int((a.notna().values & b.notna().values).sum())
    rows_s.append({"item": it, "losers_both_rounds": both(lose), "keepers_both_rounds": both(keep)})
rep = pd.DataFrame(rows_h).merge(pd.DataFrame(rows_s), on="item")
rep.to_csv(OUT / "repeated_items_power.csv", index=False)
print(rep.to_string())

# (e) long-run cross-section: 2006 attitudes to privatization (j223) and wealth (j210_*) by 1990s history
o6 = ok(ind[ind.year == 2006], "j223")
early_owner = set(sh[(sh.year <= 1996) & (sh.j26 == 1)].idind)
later_non = set(sh[(sh.year.between(1998, 2005)) & (sh.j26 == 2)].idind)
lost = early_owner & later_non
hh_sw = set(m.idind)
lr = pd.DataFrame([{
    "j223_answered_2006": len(o6),
    "early_share_owners": int(o6.idind.isin(early_owner).sum()),
    "early_owners_later_nonowners": int(o6.idind.isin(lost).sum()),
    "in_housing_switch_households": int(o6.idind.isin(hh_sw).sum()),
}])
lr.to_csv(OUT / "longrun_2006_counts.csv", index=False)
print(lr.to_string())
