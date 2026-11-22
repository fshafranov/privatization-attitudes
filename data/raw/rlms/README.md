---
dataset: rlms
collection_type: provided  # registration-gated download, copied in by the user
provider: HSE University and Carolina Population Center (UNC), Russia Longitudinal Monitoring Survey (RLMS-HSE)
url: https://www.hse.ru/en/rlms/  # also UNC Dataverse: https://dataverse.unc.edu/dataverse/rlms-hse
date_retrieved: TODO  # YYYY-MM-DD, when the user downloads the files
license: TODO  # RLMS-HSE Data Use Agreement signed at online registration; record version (2026 DUA)
format: TODO  # Stata .dta expected (zipped, one per round, or longitudinal files)
years: 1994-2025  # rounds 5-34, per HSE news of 2026-09-10 (not yet checked against files)
geography: Russia, nationally representative household panel
unit: TODO  # household-round (hh file) and individual-round (ind file)
codebook: "Household's Database 1994-2023 Codebooks; Longitudinal Data 1994-2023 Individuals Codebooks (HSE English codebooks)"
script: data/scripts/collection/acquire_rlms.py
---

# Russia Longitudinal Monitoring Survey (RLMS-HSE)

## Description

A household and individual panel from 1994 onward. The variables relevant here, from the English
longitudinal codebooks (read 2026-11-22; which rounds each item appears in is **not yet verified**):

- Housing (household file): `c1` own or rent; `c2` "privatized, personal property" vs
  "unprivatized"; `c4` owner of the dwelling (state, cooperative, private); `c4.0` house owner
  (including "not privatized"); `c1.1` market value.
- Enterprise ownership (individual file, job 1 / job 2): `j26`/`j52` (co)owner of the enterprise;
  `j28`/`j54` percent the respondent owns; `j309`/`j314` whether the enterprise's ownership changed;
  `j23`/`j49` whether the state owns the enterprise.
- Politics and attitudes (individual file): `j91`–`j94` voted in the 1996 presidential rounds and
  for whom; `j102.x` who can save Russia (democrats, businessmen, government, ...); `j103` view of
  the country's course; `j104` opinion of market reform (continue / stop / do differently);
  `j106.x` choice for president; `j118.x` closeness to democrats or communists; `j69.7` the
  government should limit the incomes of the rich; `j67`/`j68` whether rich and poor, or ordinary
  people and the powerful, can cooperate; `j69.01` generalized trust; `j65` life satisfaction.
- The longitudinal codebook has no voucher item. The 1994 round-5 cross-section questionnaire
  might have one; not checked.

Checksums: `data/raw/MANIFEST.sha256`.

## Access quirks

The download needs a personal HSE account and the Data Use Agreement accepted at registration.
The user has to do this. UNC's page describes the household and individual files as public, with
no application. The community price data and birth day and month are restricted (DUA by email)
and not needed here.
