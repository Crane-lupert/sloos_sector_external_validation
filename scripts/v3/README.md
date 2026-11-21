# v3 reference implementation

Code behind `analysis/paper_v3_en.md` ("Loan-Officer Surveys and the Cross-Section of Bank Stock Returns").
The scripts were run on 2026-11-21 in a separate verification workspace and copied here with their absolute paths
replaced by two environment variables. After the move, the read-only recheck (`phase4/p4_22_readonly_recheck.py`) and the
pre-sample check (`checks/s1_phase4b_check.py`) were run from this location and reproduce the paper's main statistics.

## Folders

| Folder | What it does |
|---|---|
| `phase4/` | 2000–2024: FRED survey series by loan category (`p4_01_fred.py`), CRSP and FR Y-9C extracts (`p4_10_extract.py`, `p4_11_y9c.py`), survey readings by release (`p4_12_N.py`), the pre-specified exposure sort (`p4_20_s1.py`), the release-day test (`p4_30_s2.py`), the aggregate timing reference (`p4_40_s3.py`), checks (`p4_21`, `p4_22`) |
| `phase4b/` | 1991–2000 pre-sample: download of the Chicago Fed holding-company files (`p4b_02_download.py`), item extraction (`p4b_10`, `p4b_11`), CRSP extract (`p4b_12`), the two confirmation tests (`p4b_20_h1h2_1990s.py`), checks, and the 2025 record (`p4b_30_post2025.py`) |
| `checks/` | Independent recomputations: main statistic from the bank table, loan shares from the raw filings, returns from a second CRSP file, the decomposition into fixed loan mix and survey variation |
| `../../analysis/v3/` | `make_tables.py`, `make_figures.py` — every table and figure of the paper; outputs in `analysis/v3/tables/` and `analysis/figures_v3/` |
| `../../docs/v3/` | The specification documents written before the corresponding results (`PHASE4_SPEC.md`, `PHASE4B_SPEC.md`, `PHASE4C_SPEC.md`; in Korean), the frozen implementation choices (`FROZEN_PARAMS_*.json`) and the execution logs |

## Configuration

```bash
export SLOOS_V3_WORK=/path/to/workdir        # holds phase4/, phase4b/, out/ (intermediate tables)
export WRDS_DUMP_DIR=/path/to/wrds/extracts  # <schema>.<table>.csv.gz files
```

`SLOOS_V3_WORK/out/` must contain the release-date tables from `data/v3_inputs/`.

## Data

Public, fetched by the scripts: FRED survey series; Federal Reserve Bank of Chicago holding-company files (FR Y-9C, 1990–2000);
Kenneth French's factor library. Release dates of the survey were collected from the Federal Reserve's survey pages
(`data/v3_inputs/release_dates_US_SLOOS.csv`, with source URLs).

Licensed, **not in this repository**: CRSP daily stock file, WRDS Bank Regulatory (FR Y-9C from 2000, PERMCO–RSSD link),
Compustat Global (only for the euro-area and UK reference tests). Bank-level tables that contain CRSP returns are not
published; the period-level series behind every table and figure are in `analysis/v3/tables/`.

## Order

`phase4/`: `p4_01` → `p4_10` → `p4_11` → `p4_12` → `p4_20` → `p4_30` → `p4_40` → `p4_50`.
`phase4b/`: `p4b_02` → `p4b_10` → `p4b_11` → `p4b_12` → `p4b_20` → `p4b_30` → `p4b_40`.
Then `analysis/v3/make_tables.py` and `make_figures.py`.
