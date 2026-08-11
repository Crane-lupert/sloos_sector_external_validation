# sloos_sector_external_validation (S3)

🚀 **LAUNCHING — Path B** (fork from S1 `sloos_sector_cross_section` close commit `4ce5c49`, 2026-05-06)

> **SSRN preprint**: abstract_id **6729904** — <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6729904> (Ahn, Hyun; posted 2026-05-07). *"Cross-Country External Validation of Bank Lending Shock × Sector Equity Heterogeneity: Eurozone Replicates US, UK Universe-Power Caveat"*, working paper, 2026. Manuscript in this repository: [analysis/paper_v2_en.pdf](analysis/paper_v2_en.pdf).

> Cross-country external validation — UK (BoE Credit Conditions Survey) + Eurozone (ECB Bank Lending Survey) replication of S1's SLOOS sectoral decomposition. Tier 1 candidate (J Mon Econ / RFS direct submission realistic if 3 of 3 cross-country Spearman pairs ≥ 0.5).

## What this repo does

This repo extends S1 ([Crane-lupert/sloos_sector_cross_section](https://github.com/Crane-lupert/sloos_sector_cross_section), LAYER A LOCKED — event-study class 2026-05-05) by replicating the SLOOS-equivalent shock × cross-section equity sector framework on:

- **United Kingdom**: Bank of England Credit Conditions Survey (CCS) C&I tightening, 2007-Q1+ (~76 quarters, ~14-18 events expected) × **STOXX 600 GBR-filter** (116 currently-active firms — FTSE 350 vendor unavailable in Compustat Global, Bonferroni power 1.4× loss caveat documented in §limitations)
- **Eurozone**: ECB Bank Lending Survey (BLS) C&I tightening, 2003-Q1+ (~88 quarters, ~17-20 events expected) × **STOXX 600 full** (~421+ active firms, eurozone country list)
- **US reference**: S1 v3 honest panel (frozen at S1 commit `4ce5c49`, 15/33 cells significant)

The **cross-country external validation** is the primary novelty over:
- **Wilson 2023 FRL** ("Profitable timing of the stock market with the senior loan officer survey") — first aggregate SLOOS-equity timing finding (S&P 500 only), no sector decomposition, US-only
- **Hafemann-Tillmann 2021 SSRN 4000366** ("Lending Standards and the Business Cycle: Evidence from Loan Survey Releases") — first SLOOS release-day shock identification via Bayesian VAR, US macro VAR aggregate, no equity sector cross-section
- **Bidder-Krane-Park 2026.02 FEDS Note** ("Measuring Shocks to Banks' Expectations for Lending Standards Using SLOOS") — first AR-residual expectation methodology, US macro VAR aggregate, no sector decomposition
- **S1 sloos_sector_cross_section** (2026-05-05 close) — first US SLOOS sectoral decomposition under Bonferroni framework, single-country

S3 contributes the **first cross-country external validation** of the SLOOS-sector phenomenon — does the sectoral pattern hold in UK and Eurozone, or is it a US-specific artifact?

## Status

🚀 **LAUNCHING** (Phase 0 Day 1 critical: BoE CCS + ECB BLS series start year verification — if ≥2015 per country, ABANDONED).

Reference validation: `D:/vscode/meta-harness/audits/2026-05-06-S3-international-validation-reference-validation.md`.

## Hypothesis

BoE CCS / ECB BLS C&I-equivalent AR(1) residual shock event (`|z_innov| > 1.0σ`) → forward {1m, 3m, 6m} 11-GICS sector cross-section CAR cyclical heterogeneity (S1 와 same direction).

**Cross-country PRIMARY (S3 extension)**:
- (N-S3-A) UK ↔ US (S1) 6m sector Spearman ≥ 0.5
- (N-S3-B) Eurozone ↔ US (S1) 6m sector Spearman ≥ 0.5
- (N-S3-C) UK ↔ Eurozone 6m sector Spearman ≥ 0.5

## Outcome class (Bayesian prior)

| Outcome | Probability |
|---|---:|
| **A+ external validation (portfolio 3rd LAYER A LOCKED, J Mon Econ candidate)** | **~20%** |
| A 2-of-3 country (B+ Layer A LOCKED — international class) | ~25% |
| B+ partial | ~25% |
| frozen-two-layer (Path B sub-mode) | ~20% |
| ABANDONED (data integrity / floor 미달) | ~10% |

## Methodology

90% framework lifted from S1: cell-level Welch t + Bonferroni-K=33 critical t≈3.17 + F-test sector heterogeneity + alternative event def Spearman + Bootstrap CI + 6-component baseline (FF5+Mom+IVOL+SRF+E-CSI US-anchored + 6th AR-residual UK CCS / Eurozone BLS shocks).

**Per-country PASS floors**:
- UK: ≥4 cells (Bonferroni power 1.4× loss adjusted, S1 floor 5 ÷ 1.4)
- Eurozone: ≥5 cells (full power, S1 floor 동일)
- US: S1 reference 15/33 (frozen)

5 new modules contribute the cross-country validation: `boe_ccs_fetch.py` / `ecb_bls_fetch.py` / `stoxx600_universe.py` / `comp_global_panel.py` / `cross_country_validation.py`.

## Data

- **BoE statistical interactive database** (CCS C&I net % tightening, public download)
- **ECB SDW** (BLS C&I net % tightening, public download)
- **WRDS courier** (`comp_global_daily` Tier A small + B medium 7 tables dumped 2026-05-05 + g_secd filtered fastlane STOXX 600 universe × 2003-2024 dumped 2026-05-06, 251 MB compressed)
- **Ken French data library** (FF5 + Mom US, US-anchored baseline, paper limitation)
- **S1 v3 reference panel** (`crsp_sector_panel_DRTSCILM_AR1_TIMEVAR_v2_2026-05-05.parquet`, frozen at S1 commit `4ce5c49`)

Sample: UK ~14-18 events / Eurozone ~17-20 events (Phase 0 Day 1 verification mandatory).

## Known caveats

- **FTSE 350 vendor unavailable** in Compustat Global (idxcstflg=N for FTSE 100/250/350/AllShare, 0 reconstitution rows). UK substitute = STOXX 600 GBR-filter (33% of FTSE 350 size, large/mid-cap only). Bonferroni power 1.4× loss documented as §limitation.
- **6-component baseline US-anchored** (Ken French US factors, BKP US E-CSI, Ferreira US SRF). Per-country factor library 부재 — paper §limitation 명시. Future revision robustness check via Datastream subscription path 가능 (현재 학교 subscription unblock 거부).
- **Survivor bias**: STOXX 600 universe 의 time-varying from/thru 검증 의무 (Phase 0 Day 2). filtered g_secd dump 가 universe-restricted 라 *currently-active firms 만* 포함 가능성 잔존.

## Korean distill

See `analysis/README_KR.md` (한국어 distill, close 시점에 finalize).

## Reproduction

Code, data, and figures are committed alongside the paper draft (`analysis/paper_v2_en.md`) so reviewers can reproduce the analysis end-to-end.

```bash
# Install dependencies
uv sync

# Regenerate figures from cached parquet/json
uv run python analysis/generate_figures.py

# Run the local interactive dashboard (NOT publicly hosted)
uv run streamlit run dashboard/app.py
```

The dashboard is local-only — there is no public Streamlit Cloud deployment, both to avoid free-tier inactivity sleep and to eliminate link-rot risk for the published paper. All figures, tables, and numerical claims in the paper can be regenerated from the cached parquet/json files in `data/cache/` without touching the dashboard.

## License

Source code in this repository is released under the [MIT License](LICENSE).

The working-paper text and its figures are **not** covered by that licence: they
remain (c) 2026 Hyun Ahn, all rights reserved. Third-party data are governed by
their original providers' terms and are not redistributed here. See
[NOTICE](NOTICE) for the full scope statement.

## Acknowledgments

This research builds on:
- Wilson, Linus (2023). *Finance Research Letters* 54: 103755.
- Hafemann, Lucas and Peter Tillmann (2021). Marburg WP 2021-31 / SSRN 4000366.
- Bidder, Rhys, David Krane, and Joonkyu Park (2026.02). *Federal Reserve FEDS Notes*.
- Bassett, William F., Mary Beth Chosak, John C. Driscoll, and Egon Zakrajšek (2014). *J Monetary Economics* 62.
- Ferreira, Thiago R. T. (2024). *J Monetary Economics* 147(C).
- Lucca, David O. and Emanuel Moench (2015). *J Finance* 70(1).
- Savor, Pavel and Mungo Wilson (2014). *RFS* 113(2).
- S1 sloos_sector_cross_section (Crane-lupert, 2026-05-05, MIT) — direct US-side foundation.
