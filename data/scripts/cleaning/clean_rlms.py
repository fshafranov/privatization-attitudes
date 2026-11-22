"""
clean_rlms.py
Stage:      cleaning (B1-B4)
Purpose:    Stream the RLMS-HSE longitudinal Stata files out of their archives, keep the
            columns this project uses, and recode RLMS non-response codes to missing.
Codebook:   HSE English codebooks "Longitudinal Data 1994-2023 Individuals" and
            "Household's Database 1994-2023" (treated as a hypothesis, B1)
Reads:      data/raw/rlms/RLMS_IND_1994_2025_eng_DTA.7z, data/raw/rlms/RLMS_HH_1994_2025_eng_DTA.zip
Writes:     data/clean/rlms/rlms_ind.csv, data/clean/rlms/rlms_hh.csv,
            data/clean/rlms/discrepancies.csv, data/logs/clean_rlms.log
Unit:       person-round (idind, id_w) and household-round (id_h, id_w); unchanged (B3)
Decisions:  ANALYSIS_PLAN.md D1 (j223 "does not know" kept as its own code)
Note:       the individual .dta is 16 GB uncompressed and is never written to disk: it is piped
            from `tar -xOf` into data/scripts/utils/dta_stream.py (numeric columns only).
"""
import subprocess

import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
from dta_stream import read_columns  # noqa: E402
from pipeline import Discrepancies, check, get_logger, log_shape, project_root, write_table  # noqa: E402

RAW = Path("data/raw/rlms")
OUT = Path("data/clean/rlms")

IND_COLS = (
    ["id_w", "idind", "id_h", "year", "int_y", "region", "psu", "status", "h5", "age", "marst",
     "diplom", "j60", "j1", "j23", "j26", "j28",
     "j223", "j224", "j226", "j69_5", "j69_7", "j107", "j110", "j65", "j66", "j66_1", "j206"]
    + [f"j210_{i}" for i in range(1, 5)]
    + [f"j211_0{i}" for i in range(1, 8)]
    + [f"j209_{i}" for i in range(1, 6)]
    + [f"j214_{i:02d}" for i in range(1, 11)]
    + ["j219", "j228_2"]
    + [f"j207_{i}" for i in (1, 2, 3, 5, 6, 7, 8, 9, 10, 11)]
    + [f"j208_{i}" for i in range(1, 8)]
)
HH_COLS = ["id_w", "id_h", "psu", "region", "status", "c1", "c2", "c4", "c4_0", "c1_1", "c5", "c6"]
SENTINELS = [99999996, 99999997, 99999998, 99999999]  # none of these / DK / refused / no answer
NOTHING = 99999996  # j214_*: "there is nothing that can be done" is an answer, kept as code 96 (D7)
DK = 99999997

# Codebook value sets, checked in phase 2 (non-missing codes only)
CATEGORY_SETS = {
    "j223": {1, 2, 3, 4}, "j224": {1, 2}, "j26": {1, 2}, "h5": {1, 2},
    "j210_1": {1}, "j210_2": {2}, "j210_3": {3}, "j210_4": {4},
    "c2": {1, 2}, "c1": {1, 2, 3}, "c4_0": {1, 2, 3, 4},
}
RANGES = {"age": (0, 110), "year": (1994, 2025), "id_w": (5, 34), "c6": (1, 5000), "c1_1": (0, 5e9)}

log = get_logger("clean_rlms")
disc = Discrepancies(log)
root = project_root()


def stream(archive: str, cols: list):
    proc = subprocess.Popen(["tar", "-xOf", str(root / RAW / archive)], stdout=subprocess.PIPE)
    df = read_columns(proc.stdout, cols)
    proc.stdout.close()  # tar then stops on a broken pipe after the data section; that is expected
    proc.wait()
    return df


def clean(df, name, key):
    # == PHASE 1: LOAD AND PROFILE ==========================================
    n_in = len(df)
    log_shape(log, df, f"{name} raw")

    # == PHASE 2: PRE-CLEANING ASSERTIONS ===================================
    check(df.duplicated(key).sum() == 0, f"{name}: key {key} not unique in raw data")
    for col, allowed in CATEGORY_SETS.items():
        if col not in df:
            continue
        s = df[col].dropna()
        unknown = sorted(set(s[~s.isin(SENTINELS)].unique()) - allowed)
        if unknown:
            disc.add(col, f"codes {sorted(allowed)}", unknown[:20], int(s.isin(unknown).sum()), "kept, flagged")
    for col, (lo, hi) in RANGES.items():
        if col in df:
            s = df[col].dropna()
            s = s[~s.isin(SENTINELS)]  # non-response codes are recoded in phase 3, not range errors
            bad = ~s.between(lo, hi)
            if bad.any():  # implausible magnitudes: flagged, set to missing in phase 3
                disc.add(col, f"[{lo}, {hi}]", f"{s[bad].min()}..{s[bad].max()}", int(bad.sum()), "set to missing")
                df.loc[s[bad].index, col] = np.nan

    # == PHASE 3: TRANSFORMATIONS ===========================================
    if "j223" in df:  # ANALYSIS_PLAN.md D1: DK is a substantive answer to j223, kept as code 7
        n_dk = int((df.j223 == DK).sum())
        df.loc[df.j223 == DK, "j223"] = 7
        log.info("recode", var="j223", code=DK, to=7, n=n_dk)
    for col in [c for c in df.columns if c.startswith("j214_")]:  # ANALYSIS_PLAN.md D7
        n96 = int((df[col] == NOTHING).sum())
        df.loc[df[col] == NOTHING, col] = 96
        log.info("recode", var=col, code=NOTHING, to=96, n=n96)
    for col in df.columns:
        if col in key:
            continue
        mask = df[col].isin(SENTINELS)
        if mask.any():
            df[col] = df[col].mask(mask)
            log.info("recode_sentinels", var=col, n_recoded=int(mask.sum()))
    for col in key + ["year", "int_y", "region", "psu", "status", "h5"]:
        if col in df and df[col].notna().all() and (df[col] % 1 == 0).all():
            df[col] = df[col].astype("int64")

    # == PHASE 4: POST-CLEANING ASSERTIONS ==================================
    check(len(df) == n_in, f"{name}: row count changed {n_in} -> {len(df)} (B3)")
    check(not df[[c for c in df.columns if c not in key]].isin(SENTINELS).any().any(),
          f"{name}: sentinel codes remain")
    # == PHASE 5: FINAL PROFILE AND WRITE ====================================
    log_shape(log, df, f"{name} clean")
    log.info("share_missing", data=name, share=df.isna().mean().round(4).to_dict())
    write_table(log, df, str(OUT / f"{name}.csv"), sort_by=key)


clean(stream("RLMS_HH_1994_2025_eng_DTA.zip", HH_COLS), "rlms_hh", ["id_h", "id_w"])
clean(stream("RLMS_IND_1994_2025_eng_DTA.7z", IND_COLS), "rlms_ind", ["idind", "id_w"])
disc.write(str(OUT / "discrepancies.csv"))
log.info("end")
