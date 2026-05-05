"""Gate K + L + M tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sloos_sector_external_validation.gates_klm import (
    GATE_K_RATIO_FLOOR,
    GATE_L_DECAY_FLOOR,
    GATE_M_COST_BP_PER_YEAR,
    SUBPERIOD_SPLIT,
    _per_event_sharpe_annualized,
    run_gate_k,
    run_gate_m,
)


def test_lock_constants():
    assert GATE_K_RATIO_FLOOR == 0.5
    assert GATE_L_DECAY_FLOOR == 0.5
    assert GATE_M_COST_BP_PER_YEAR == 5.0
    assert SUBPERIOD_SPLIT == pd.Timestamp("2010-01-01")


def test_per_event_sharpe_annualized_basic():
    df = pd.DataFrame(
        {
            "event_date": pd.to_datetime(["2020-01-01", "2020-04-01", "2020-07-01", "2020-10-01"]),
            "strategy_ret": [0.01, 0.02, 0.015, 0.012],
        }
    )
    sh = _per_event_sharpe_annualized(df)
    assert sh > 0
    assert np.isfinite(sh)


def test_per_event_sharpe_annualized_empty():
    df = pd.DataFrame(columns=["event_date", "strategy_ret"])
    sh = _per_event_sharpe_annualized(df)
    assert np.isnan(sh)


def test_per_event_sharpe_annualized_constant_returns():
    df = pd.DataFrame(
        {
            "event_date": pd.to_datetime(["2020-01-01", "2020-04-01"]),
            "strategy_ret": [0.01, 0.01],
        }
    )
    # std=0 → NaN
    sh = _per_event_sharpe_annualized(df)
    assert np.isnan(sh)


# Integration: real Day 10 panel
def test_real_gate_k_subperiod():
    cache = Path("data/cache")
    panel_files = sorted(cache.glob("sector_panel_*.parquet"))
    layer_a_files = sorted(cache.glob("layer_a_results_*.parquet"))
    if not (panel_files and layer_a_files):
        pytest.skip("snapshots missing")
    panel = pd.read_parquet(panel_files[-1])
    layer_a = pd.read_parquet(layer_a_files[-1])
    gk = run_gate_k(panel, layer_a)
    assert gk.pass_subperiod, f"Gate K subperiod ratio {gk.sub_sharpe_ratio:.3f} < 0.5"


def test_real_gate_m_net_cost():
    cache = Path("data/cache")
    panel_files = sorted(cache.glob("sector_panel_*.parquet"))
    layer_a_files = sorted(cache.glob("layer_a_results_*.parquet"))
    if not (panel_files and layer_a_files):
        pytest.skip("snapshots missing")
    panel = pd.read_parquet(panel_files[-1])
    layer_a = pd.read_parquet(layer_a_files[-1])
    gm = run_gate_m(panel, layer_a)
    assert gm.pass_floor, f"Gate M net Sharpe {gm.net_sharpe_ann:.3f} < 0"
