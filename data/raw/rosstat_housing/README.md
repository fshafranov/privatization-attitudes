---
dataset: rosstat_housing
collection_type: acquisition
provider: Rosstat, via the Internet Archive Wayback Machine (snapshot 2024-04-17)
url: https://web.archive.org/web/20240417184008id_/https://rosstat.gov.ru/storage/mediabank/sred_vtor_2021.xlsx
date_retrieved: 2026-11-23
license: Russian official statistics (public)
format: xlsx
years: 2021 (quarterly)
geography: Russian Federation subjects (sheet 1) and subject centres (sheet 2)
unit: region x quarter; roubles per m2, by flat type
codebook: sheet "Содержание" in the file
script: data/scripts/collection/acquire_housing_prices.py
---

# Rosstat average prices on the secondary housing market, 2021

Used only to validate the statbase transcription (see `data/raw/statbase_housing/README.md`).
rosstat.gov.ru itself could not be reached: its certificate chain is not trusted on this
machine, so the archived copy was used.
