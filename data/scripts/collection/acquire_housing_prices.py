"""
acquire_housing_prices.py
Stage:      collection (A1-A4)
Purpose:    Regional average prices per m2 on the secondary housing market (Rosstat form 1-RZh),
            (1) as republished year by year on statbase.ru, (2) Rosstat's own 2021 regional file
            from the Wayback Machine, used to validate the statbase transcription.
Source:     https://statbase.ru/datasets/national-statistics-of-russia/labor-income-prices/
            average-prices-in-the-secondary-housing-market-by-region-national-stat/?syear=YYYY
            https://web.archive.org/web/20240417184008id_/https://rosstat.gov.ru/storage/mediabank/sred_vtor_2021.xlsx
Reads:      network only
Writes:     data/raw/statbase_housing/secondary_YYYY.html (2001-2025),
            data/raw/rosstat_housing/sred_vtor_2021.xlsx, data/logs/acquire_housing_prices.log
Verified:   each file exists, is non-empty, has the expected format and (HTML) region rows (A3)
Notes:      statbase's robots.txt disallows query-string URLs; the user decided to collect these
            public pages anyway (2026-11-23). One request every 6 s, files already present are
            skipped, so the site is hit at most once per year.
Usage:      uv run python data/scripts/collection/acquire_housing_prices.py [--force]
"""
import argparse
import sys
import time
from pathlib import Path

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
from pipeline import check, get_logger, project_root, verify_files  # noqa: E402

STATBASE = ("https://statbase.ru/datasets/national-statistics-of-russia/labor-income-prices/"
            "average-prices-in-the-secondary-housing-market-by-region-national-stat/"
            "?syear={year}&frmreq=0&sproc=sum&filter=&sort=")
ROSSTAT_2021 = ("https://web.archive.org/web/20240417184008id_/"
                "https://rosstat.gov.ru/storage/mediabank/sred_vtor_2021.xlsx")
YEARS = range(2001, 2026)
DELAY_S = 6
HEADERS = {"User-Agent": "Mozilla/5.0 (academic research; low-volume download)"}


@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=5, max=60), reraise=True)
def download(url: str, dest: Path) -> None:
    tmp = dest.with_suffix(dest.suffix + ".part")
    with httpx.stream("GET", url, headers=HEADERS, timeout=120, follow_redirects=True) as r:
        r.raise_for_status()
        with tmp.open("wb") as fh:
            for chunk in r.iter_bytes(chunk_size=1 << 16):
                fh.write(chunk)
    tmp.replace(dest)


def main(force: bool) -> None:
    log = get_logger("acquire_housing_prices")
    root = project_root()
    sb_dir, rs_dir = root / "data/raw/statbase_housing", root / "data/raw/rosstat_housing"
    sb_dir.mkdir(parents=True, exist_ok=True)
    rs_dir.mkdir(parents=True, exist_ok=True)

    # == STEP 1: ROSSTAT 2021 REGIONAL FILE (WAYBACK) ==========================
    dest = rs_dir / "sred_vtor_2021.xlsx"
    if force or not dest.exists():
        download(ROSSTAT_2021, dest)
        log.info("downloaded", file=str(dest.relative_to(root)), bytes=dest.stat().st_size)

    # == STEP 2: STATBASE YEAR PAGES, POLITELY ================================
    for year in YEARS:
        dest = sb_dir / f"secondary_{year}.html"
        if dest.exists() and not force:
            log.info("present_skip", file=str(dest.relative_to(root)))
            continue
        download(STATBASE.format(year=year), dest)
        log.info("downloaded", file=str(dest.relative_to(root)), bytes=dest.stat().st_size)
        time.sleep(DELAY_S)

    # == STEP 3: VERIFY ========================================================
    verify_files(log, {"data/raw/rosstat_housing/sred_vtor_2021.xlsx": "xlsx"})
    for year in YEARS:
        p = sb_dir / f"secondary_{year}.html"
        check(p.exists() and p.stat().st_size > 0, f"missing or empty {p.name}")
        n_rows = p.read_text(encoding="utf-8", errors="replace").count("value_column")
        check(n_rows >= 60, f"{p.name}: expected >= 60 region rows, found {n_rows}")
        log.info("verified", file=p.name, region_rows=n_rows)
    log.info("end")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="re-download files already present")
    main(ap.parse_args().force)
