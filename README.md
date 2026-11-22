# Mass privatization and political attitudes in Russia (RLMS) — replication package

## Overview
TODO: one paragraph on the paper/project and what this package reproduces.

## Reproduce everything

```bash
uv sync                                     # Python environment from uv.lock (.venv)
Rscript -e 'renv::restore()'                # R packages from renv.lock (if R is used)
uv run python run_all.py                    # rebuild from data/raw/: clean -> process -> analyze -> tables
uv run python run_all.py --with-collection  # also re-download raw data first
```

Expected runtime: TODO. Outputs: `data/clean/`, `data/processed/`, `empirics/results/`.
Each run writes `data/logs/run_all.log` and `data/logs/session_info.log` (interpreter and package versions).

## Software environment
- Python TODO (managed by uv: `pyproject.toml`, pinned in `uv.lock`)
- R TODO (pinned in `renv.lock`)
- Stata TODO version, ado packages: TODO

## Data sources

| Dataset slug | Provider | Raw folder | Acquisition | Cleaning |
|---|---|---|---|---|
| `rlms` | TODO | `data/raw/rlms/` | `acquire_rlms.py` | `clean_rlms.py` |

Provenance details are in each `data/raw/{dataset}/README.md`. Raw files are checksummed
in `data/raw/MANIFEST.sha256`.

## Workfiles

| Workfile | Unit of observation | Built by |
|---|---|---|
| `housing_panel` | TODO | `process_housing_panel.py` |
| `shares_panel` | TODO | `process_shares_panel.py` |

## Results → paper map

| Paper output | File | Script |
|---|---|---|
| TODO: Table 1 | `empirics/results/tables/...tex` | `empirics/scripts/analyze_...` |

## Replication status (vs published)

| Table | Validation script | Cells matching | Unexplained mismatches |
|---|---|---|---|
| TODO | `empirics/scripts/validate_...` | | see `empirics/results/warnings/` |

## Decisions and status
Decisions (D*), robustness checks (R*) and the change log: `ANALYSIS_PLAN.md`. Current status: `research-state.md`. Replication gaps: `mismatch-register.csv`.
