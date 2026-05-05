"""STOXX 600 universe build (Path B specific, S3).

Constructs UK + Eurozone universes from Compustat Global STOXX 600 reconstitution
(gvkeyx=150376, real reconstitution AstraZeneca/HSBC/Shell verified by courier
2026-05-05 234029 response §g_idxcst_his_verification PASS).

Universe definitions:

UK universe (FTSE 350 substitute, Bonferroni power 1.4× loss caveat):
    - STOXX 600 GBR-filter (loc='GBR')
    - 116 currently-active firms expected
    - longest-tenured (2000-01-01+): Centrica / Barclays / Vodafone / National Grid /
      GSK / Imperial Brands / BP / Man Group / British American Tobacco / BT Group

Eurozone universe (full real, no substitute needed):
    - STOXX 600 minus UK (GBR) minus non-eurozone (USA / ZAF / HKG)
    - Country list: DEU / FRA / CHE / SWE / ITA / NLD / ESP / DNK / FIN / NOR /
      BEL / IRL / AUT / PRT / LUX / POL (etc per courier response country distribution)
    - ~421+ currently-active firms expected

Time-varying construction:
    - Read comp_global_daily.g_idxcst_his filter to gvkeyx='150376'
    - Join comp_global_daily.g_company → GICS sector + ISO loc + currency
    - Apply from/thru date filters per event window (Phase 0 Day 2)
    - Survivor bias check: STOXX 600 universe 의 time-varying from/thru 검증 의무

Critical:
    - The filtered g_secd dump (`comp_global_daily.g_secd.stoxx600_2003plus.csv.gz`,
      251 MB compressed, 17.8M rows) covers STOXX 600 historical universe × 2003-2024.
    - But survivor bias possible — verify currently-active filter doesn't dominate.

This module is a placeholder. V0 overnight prompt populates during Phase 0 Day 2.

References:
- Courier outbox response: E:/wrds-data-courier/outbox/S1-pathB-international-equity-data-response-20260505-234029.json
- §g_idxcst_his_verification (AstraZeneca/HSBC/Shell PASS)
- §available_indices_with_real_constituent_history.STOXX_600_Price_Index
"""

from __future__ import annotations

# TODO (Phase 0 Day 2): implement STOXX 600 universe build
# - build_uk_universe(as_of_date: pd.Timestamp = None) -> pd.DataFrame
#   - columns: gvkey, conml, gsector, loc, from_date, thru_date
# - build_eurozone_universe(as_of_date: pd.Timestamp = None) -> pd.DataFrame
# - get_active_firms_per_event(universe: pd.DataFrame, event_dates: list) -> dict
# - per_cell_n_audit(panel: pd.DataFrame, sectors: list, horizons: list) -> pd.DataFrame
# - save_universe_parquet(uk: pd.DataFrame, eurozone: pd.DataFrame, path: str) -> None
