"""
acquire_rlms.py
Stage:      collection (A1-A4)
Purpose:    Documented copy step for the RLMS-HSE files. They sit behind a personal HSE account
            and a Data Use Agreement, so they cannot be downloaded by script.
Source:     https://www.hse.ru/en/rlms/ (registration), files as listed in data/raw/rlms/README.md
Reads:      data/raw/rlms/ (placed there by hand)
Writes:     data/logs/acquire_rlms.log
Verified:   both archives exist, are non-empty, and hold the expected .dta member (A3)
Manual step: log in at https://www.hse.ru/en/rlms/, download the household and individual
            longitudinal Stata files for 1994-2025 (English), and save them unchanged as
            data/raw/rlms/RLMS_HH_1994_2025_eng_DTA.zip and
            data/raw/rlms/RLMS_IND_1994_2025_eng_DTA.7z. Then run
            `python <skill-dir>/scripts/audit.py . --write-manifest` to record checksums.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
from pipeline import check, get_logger, project_root  # noqa: E402

RAW_DIR = Path("data/raw/rlms")
EXPECTED = {
    "RLMS_HH_1994_2025_eng_DTA.zip": "RLMS_HH_1994_2025_eng.dta",
    "RLMS_IND_1994_2025_eng_DTA.7z": "RLMS_IND_1994_2025_eng.dta",
}

log = get_logger("acquire_rlms")
root = project_root()

# == STEP 1: VERIFY HAND-PLACED FILES ==========================================
for archive, member in EXPECTED.items():
    p = root / RAW_DIR / archive
    check(p.exists(), f"missing {p.relative_to(root)}: see the manual step in this header")
    check(p.stat().st_size > 0, f"{archive} is empty")
    listing = subprocess.run(["tar", "-tf", str(p)], capture_output=True, text=True, check=True).stdout.split()
    check(listing == [member], f"{archive}: expected one member {member}, found {listing}")
    log.info("verified", file=str(p.relative_to(root)), bytes=p.stat().st_size, member=member)
log.info("end")
