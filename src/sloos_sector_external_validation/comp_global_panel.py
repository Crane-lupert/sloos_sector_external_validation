"""Compustat Global panel build (Path B specific, S3).

Reads filtered g_secd (STOXX 600 universe × 2003-2024, 17.8M rows compressed 251 MB)
and constructs per-country forward CAR panels.

Per country panel:
    - UK panel: filter to UK universe gvkey list × event dates × forward window
      Expected size: ~40-60K firm-events
    - Eurozone panel: filter to Eurozone universe gvkey list × event dates × forward window
      Expected size: ~150-250K firm-events

Forward CAR computation:
    - Event date t (BoE CCS / ECB BLS shock release date)
    - Forward windows: 1m (~21 td) / 3m (~63 td) / 6m (~126 td)
    - Hedge benchmark: STOXX 600 index daily return (or per-country index)
    - CAR_i = log(P_{i,t+h}) - log(P_{i,t}) - (log(I_{t+h}) - log(I_t))

Currency normalization:
    - Primary: local currency (GBP for UK, EUR for Eurozone)
      Rationale: removes FX shock contamination, cleaner sector heterogeneity attribution
    - Robustness: USD-converted (Tier C FX rates from courier — defer to Phase 2)

Critical:
    - g_secd column `curcdd` indicates currency code per row
    - `comp_global_daily.g_secd.stoxx600_2003plus.csv.gz` filtered fastlane dump
    - Read via wrds_courier_adapter (lifted from S1) or direct duckdb query

This module is a placeholder. V0 overnight prompt populates during Phase 0 Day 3.

References:
- Courier outbox response: g_secd 17.8M rows STOXX 600 × 2003-2024
- S1 inheritance: src/sloos_sector_external_validation/crsp_panel.py (lifted, but US-only)
- New module — Path B specific (different vendor: comp_global_daily vs CRSP)
"""

from __future__ import annotations

# TODO (Phase 0 Day 3): implement comp_global panel build
# - read_g_secd_filtered(universe_gvkeys: list, date_range: tuple) -> pd.DataFrame
# - build_country_panel(country: str, universe: pd.DataFrame, events: pd.DataFrame, horizons: list) -> pd.DataFrame
# - compute_forward_car(panel: pd.DataFrame, hedge_benchmark: pd.Series, horizon_days: int) -> pd.DataFrame
# - save_panel_parquet(uk_panel: pd.DataFrame, eurozone_panel: pd.DataFrame, path: str) -> None
