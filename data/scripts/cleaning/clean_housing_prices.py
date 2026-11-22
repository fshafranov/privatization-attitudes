"""
clean_housing_prices.py
Stage:      cleaning (B1-B4)
Purpose:    Parse the statbase.ru year pages into a region-year table of Rosstat's average price
            per m2 on the secondary housing market (all flat types, Q4 / end of year), and check the
            2021 values against Rosstat's own regional file.
Codebook:   statbase page layout (one `it_row` per region: link /data/ruNN-..., hidden okato_block,
            value_column); Rosstat sred_vtor_2021.xlsx sheet 1 (subjects, quarterly, "all types" in
            columns 1, 6, 11, 16)
Reads:      data/raw/statbase_housing/secondary_YYYY.html, data/raw/rosstat_housing/sred_vtor_2021.xlsx
Writes:     data/clean/housing_prices/secondary_prices.csv, data/clean/housing_prices/national_prices.csv, data/clean/housing_prices/validation_2021.csv,
            data/clean/housing_prices/discrepancies.csv, data/logs/clean_housing_prices.log
Unit:       region x year (okato11, year)
Decisions:  ANALYSIS_PLAN.md D13
"""
import html
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
from pipeline import Discrepancies, check, get_logger, log_shape, project_root, write_table  # noqa: E402

RAW = Path("data/raw/statbase_housing")
OUT = Path("data/clean/housing_prices")
NO_DATA_YEARS = {2002, 2004}  # statbase pages for these years carry no table (checked 2026-11-23)
log = get_logger("clean_housing_prices")
disc = Discrepancies(log)
root = project_root()

ROW = re.compile(r'class="it_row(.*?)(?=class="it_row|\Z)', re.S)
LINK = re.compile(r'href="/data/ru(\d+)-average-prices[^"]*"\s+title="Данные по годам ([^"]+)"')
OKATO = re.compile(r'okato_block"[^>]*>\s*(\d+)\s*<')
VALUE = re.compile(r'value_column[^>]*>\s*<a href="/data/ru\d+-[^"]*"[^>]*>\s*([\d\s.,]+?)\s*</a>')

# == PHASE 1: LOAD AND PROFILE ==============================================
recs = []
for f in sorted((root / RAW).glob("secondary_*.html")):
    year = int(f.stem.split("_")[1])
    s = f.read_text(encoding="utf-8", errors="replace")
    sel = re.findall(r'<option[^>]*selected[^>]*>\s*(\d{4})', s)
    n_before = len(recs)
    for block in ROW.findall(s):
        m, o, v = LINK.search(block), OKATO.search(block), VALUE.search(block)
        if not (m and v):
            continue
        recs.append({"year": year, "statbase_code": int(m.group(1)), "region": html.unescape(m.group(2)).strip(),
                     "okato2": int(o.group(1)) if o else None, "price_raw": v.group(1)})
    n = len(recs) - n_before
    log.info("page", file=f.name, rows=n, selected_year=sel[:1])
    if year in NO_DATA_YEARS:
        check(n == 0, f"{f.name}: expected no table, found {n} rows")
    else:
        check(n >= 60 and sel[:1] == [str(year)], f"{f.name}: {n} rows, selected year {sel[:1]}")
df = pd.DataFrame(recs)
n_in = len(df)
log_shape(log, df, "parsed")

# == PHASE 2: PRE-CLEANING ASSERTIONS =======================================
check(not df.duplicated(["statbase_code", "year"]).any(), "region x year not unique")
national = df[df.region == "В целом по стране"]
check(national.okato2.isna().all(), "national row unexpectedly has an OKATO code")
check(df[df.region != "В целом по стране"].okato2.notna().all(), "a region row lacks an OKATO code")
log.info("set_aside", rows=len(national), reason="national total, not a region (written to national_prices.csv)")

# == PHASE 3: TRANSFORMATIONS ================================================
df["price_rub_m2"] = pd.to_numeric(df.price_raw.str.replace(r"\s", "", regex=True).str.replace(",", "."),
                                   errors="raise")
df = df.drop(columns="price_raw")
nat = df[df.region == "В целом по стране"][["year", "price_rub_m2"]]
df = df[df.region != "В целом по стране"].copy()
df["okato2"] = df.okato2.astype(int)

# == PHASE 4: POST-CLEANING ASSERTIONS AND VALIDATION AGAINST ROSSTAT ========
check(len(df) + len(nat) == n_in, f"row count changed {n_in} -> {len(df)} + {len(nat)} national")
check(df.price_rub_m2.between(1_000, 2_000_000).all(), "price per m2 outside 1k-2m roubles")
rs = pd.read_excel(root / "data/raw/rosstat_housing/sred_vtor_2021.xlsx", sheet_name=1, header=None)
check(rs.iloc[3, 16] == "IV квартал" and rs.iloc[4, 16] == "Все типы квартир", "Rosstat layout changed")
rs = rs[rs[0].astype(str).str.match(r"^\d{11} - ")].copy()
rs["okato11"] = rs[0].astype(str).str[:11]
rs["rosstat_q4_2021"] = pd.to_numeric(rs[16], errors="coerce")
rs = rs[["okato11", 0, "rosstat_q4_2021"]].rename(columns={0: "rosstat_name"})
# Statbase lists Arkhangelsk and Tyumen oblasts WITHOUT their autonomous okrugs, and the okrugs
# separately, all under the parent's 2-digit OKATO; map them to Rosstat's 11-digit sub-rows.
SUBROW = {29: "11001000000", 83: "11100000000", 72: "71001000000", 86: "71100000000", 89: "71140000000"}
df["okato11"] = df.statbase_code.map(SUBROW).fillna(df.okato2.map(lambda x: f"{x:02d}000000000"))
check(not df.duplicated(["okato11", "year"]).any(), "okato11 x year not unique")
val = df[df.year == 2021].merge(rs, on="okato11", how="left", indicator=True)
val["diff"] = val.price_rub_m2 - val.rosstat_q4_2021
both = val[val._merge == "both"]
log.info("validation_2021", statbase=len(val), rosstat_rows=len(rs),
         matched=len(both), exact=int((both["diff"].abs() < 0.5).sum()), max_abs_diff=float(both["diff"].abs().max()))
for _, r in both[both["diff"].abs() >= 0.5].iterrows():
    disc.add("price_rub_m2", f"Rosstat Q4 2021 {r.rosstat_q4_2021}", r.price_rub_m2, 1, f"kept; okato {r.okato11}")
check(len(both) >= 80 and (both["diff"].abs() < 0.5).mean() >= 0.98,
      "statbase 2021 does not reproduce Rosstat Q4 2021 for at least 98% of matched regions")
write_table(log, val.drop(columns="_merge").assign(merge=val._merge.astype(str)), str(OUT / "validation_2021.csv"),
            sort_by=["okato11"])

# == PHASE 5: FINAL PROFILE AND WRITE ========================================
log_shape(log, df, "clean")
log.info("coverage", regions_by_year=df.groupby("year").size().to_dict())
write_table(log, df, str(OUT / "secondary_prices.csv"), sort_by=["okato11", "year"])
write_table(log, nat, str(OUT / "national_prices.csv"), sort_by=["year"])
disc.write(str(OUT / "discrepancies.csv"))
log.info("end")
