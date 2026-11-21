# sloos_sector_external_validation

**Loan-Officer Surveys and the Cross-Section of Bank Stock Returns: Evidence from Commercial Real Estate Lending Standards, 1991–2024** — working paper, v3 (November 2026).

Manuscript: [analysis/paper_v3_en.md](analysis/paper_v3_en.md) · Korean version: [analysis/paper_v3_kr.md](analysis/paper_v3_kr.md) · Korean summary: [analysis/README_KR.md](analysis/README_KR.md)

> **Status.** v3 replaces the May 2026 manuscript posted as SSRN 6729904 ("Cross-Country External Validation of Bank Lending Shock × Sector Equity Heterogeneity"). The sector-level results of that version do not survive corrected event dates, point-in-time universes and event-level inference (paper, Appendix C). The SSRN entry is being revised to v3; until that revision is posted, the PDF on SSRN is the earlier version, which is kept here under [analysis/archive_v2/](analysis/archive_v2/).

## Question

The Federal Reserve's Senior Loan Officer Opinion Survey (SLOOS) reports, by loan category, the net share of banks tightening lending standards. When the survey says standards are tightening in one category, do the stocks of banks that hold a lot of that category subsequently do worse than the stocks of banks that hold little of it? Both inputs are public: the survey readings, and each bank holding company's loan mix (FR Y-9C).

## Results

| Test | Sample | Estimate | *t* |
|---|---|---:|---:|
| Exposure sort specified before returns were computed: lowest minus highest quintile of exposure to tightening, equal-weighted, held between survey releases | 2000–2024, 95 releases, about 230 listed bank holding companies | +1.19% per quarter | 2.42 |
| Same statistic, pooled | 1991–2024, 133 releases | +1.00% per quarter | 2.56 |
| Low-CRE minus high-CRE bank return spread on the net CRE tightening just released (where the pattern was found) | 2000–2024 | +0.95 pp per 10 pp | 3.90 |
| Same test on a non-overlapping earlier sample, specified before those data were assembled | 1991–2000, 38 releases | +0.85 pp per 10 pp | 2.22 |
| Same test, pooled | 1991–2024 | +0.93 pp per 10 pp | 4.02 |

A static sort on CRE share is not significant (0.49% per quarter, *t* = 0.76): the information is in the survey's variation over time.

## What is not claimed

- **Not a profitable strategy.** The spread is 0.19% per quarter (*t* = 0.24) in value-weighted portfolios and 0.61% (*t* = 1.24) after quoted spreads and an assumed 1% borrowing fee.
- **Concentrated in CRE downturns.** Excluding 1991–92 and 2008–09 the pooled slope is 0.51 (*t* = 2.36).
- **Mechanism not established.** A test of whether credit losses of exposed banks rise over the next four quarters has the expected sign but does not reach significance (*t* = 1.49).
- **Pre-specification is documented by the author's files**, not by a public registry (paper, Section 3.5). Twenty-five of the 38 pre-sample releases use approximate release dates.
- Two further tests specified in advance — a release-day reaction of bank stocks and aggregate market timing — do not pass (paper, Appendix B).

## Repository layout

| Path | Content |
|---|---|
| `analysis/paper_v3_en.md`, `analysis/refs_v3.bib`, `analysis/figures_v3/` | Manuscript (pandoc Markdown), references, figures |
| `analysis/v3/` | `make_tables.py`, `make_figures.py`, and the period-level series behind every table and figure (`tables/`) |
| `scripts/v3/` | Reference implementation: `phase4/` (2000–2024), `phase4b/` (1991–2000 and the 2025 record), `checks/` (independent recomputations). See [scripts/v3/README.md](scripts/v3/README.md) |
| `docs/v3/` | Specification documents written before the corresponding results (in Korean), frozen implementation choices, execution logs |
| `data/v3_inputs/` | Release dates of the three surveys with source URLs |
| `analysis/archive_v2/`, `src/`, `tests/`, `dashboard/`, `LAYER_A_LOCKED.md` | The earlier (May 2026) analysis, kept as a record |

## Reproduction

```bash
uv sync
export SLOOS_V3_WORK=/path/to/workdir        # intermediate tables
export WRDS_DUMP_DIR=/path/to/wrds/extracts  # licensed data, not in this repository
# pipeline order: scripts/v3/README.md
python analysis/v3/make_tables.py
python analysis/v3/make_figures.py
cd analysis
pandoc paper_v3_en.md --citeproc --standalone --mathml --number-sections -c v3/print.css -o paper_v3_en.html
# print paper_v3_en.html to PDF with a browser (the committed PDF was made with headless Chrome),
# or, with a LaTeX engine: pandoc paper_v3_en.md --citeproc --number-sections -o paper_v3_en.pdf
```

## Data and licences

Public: FRED (survey series), Federal Reserve Board survey pages (release dates), Federal Reserve Bank of Chicago holding-company files (FR Y-9C, 1990–2000), Kenneth French's data library. Licensed and not redistributed: CRSP, WRDS Bank Regulatory, Compustat Global.

Source code is released under the [MIT License](LICENSE). The working-paper text and figures are (c) 2026 Hyun Ahn, all rights reserved. See [NOTICE](NOTICE).

## Main references

- Chava, S., M. Gallmeyer and H. Park (2015). Credit conditions and stock return predictability. *Journal of Monetary Economics* 74, 117–132.
- Wilson, L. (2023). Profitable timing of the stock market with the senior loan officer survey. *Finance Research Letters* 54, 103733.
- Kovner, A. and P. Van Tassel (2022). Evaluating regulatory reform: banks' cost of capital and lending. *Journal of Money, Credit and Banking* 54(5), 1313–1367.
- Bassett, W. F., M. B. Chosak, J. C. Driscoll and E. Zakrajšek (2014). Changes in bank lending standards and the macroeconomy. *Journal of Monetary Economics* 62, 23–40.
- Fahlenbrach, R., R. Prilmeier and R. M. Stulz (2018). Why does fast loan growth predict poor performance for banks? *Review of Financial Studies* 31(3), 1014–1063.

The full list is in `analysis/refs_v3.bib`.
