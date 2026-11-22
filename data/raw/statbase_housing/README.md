---
dataset: statbase_housing
collection_type: acquisition
provider: statbase.ru (republishes Rosstat form 1-RZh, average prices on the secondary housing market)
url: https://statbase.ru/datasets/national-statistics-of-russia/labor-income-prices/average-prices-in-the-secondary-housing-market-by-region-national-stat/?syear=YYYY&frmreq=0&sproc=sum&filter=&sort=
date_retrieved: 2026-11-23
license: TODO  # site terms not reviewed; robots.txt disallows query-string URLs; collected at the user's decision
format: html
years: 2001-2025 (no table for 2002 and 2004)
geography: Russian Federation subjects (76-84 per year)
unit: region x year; price in roubles per m2 of total floor area, all flat types, end of year (Q4)
codebook: none; layout described in data/scripts/cleaning/clean_housing_prices.py
script: data/scripts/collection/acquire_housing_prices.py
---

# Regional secondary-market housing prices (statbase.ru year pages)

One HTML page per year (`secondary_YYYY.html`), saved unchanged. Each page lists every region
with its statbase code (`/data/ruNN-...`), its OKATO code (hidden column) and the price.

The values are Rosstat's: the 2021 page reproduces Rosstat's own Q4 2021 regional file
(`data/raw/rosstat_housing/sred_vtor_2021.xlsx`) exactly for all 84 regions
(`data/clean/housing_prices/validation_2021.csv`).

## Access quirks

The pages are public, but statbase's robots.txt disallows URLs with query strings and the site
sells data exports. The user decided on 2026-11-23 to collect the public year pages anyway. The
collection script makes one request per year, 6 seconds apart, and skips files already present.
Arkhangelsk and Tyumen oblasts appear without their autonomous okrugs, and the okrugs appear
separately (handled in cleaning).
