"""Walk-forward 5-fold tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sloos_sector_external_validation.walk_forward import (
    N_FOLDS,
    WALK_FORWARD_FLOOR,
    _split_chronological,
    run_walk_forward,
)


def test_lock_constants():
    assert N_FOLDS == 5
    assert WALK_FORWARD_FLOOR == 4


def test_split_chronological_produces_n_folds():
    dates = list(pd.date_range("2020-01-01", periods=36, freq="QS"))
    splits = _split_chronological(dates, n_folds=5)
    assert len(splits) == 5
    # Each fold's train should be earlier than test (no leakage)
    for tr, te in splits:
        assert max(tr) < min(te)
    # First fold's train smaller than last fold's
    assert len(splits[0][0]) < len(splits[-1][0])


def test_split_chronological_train_expands():
    dates = list(pd.date_range("2020-01-01", periods=36, freq="QS"))
    splits = _split_chronological(dates, n_folds=5)
    train_sizes = [len(tr) for tr, _ in splits]
    # Strictly non-decreasing (expanding window)
    assert all(a <= b for a, b in zip(train_sizes[:-1], train_sizes[1:]))


def test_split_chronological_test_blocks_disjoint():
    dates = list(pd.date_range("2020-01-01", periods=36, freq="QS"))
    splits = _split_chronological(dates, n_folds=5)
    test_indices = []
    for _, te in splits:
        test_indices.extend(te)
    # Test blocks should be disjoint and contiguous
    assert len(test_indices) == len(set(test_indices))


def test_split_chronological_too_few_events_raises():
    dates = list(pd.date_range("2020-01-01", periods=3, freq="QS"))
    with pytest.raises(ValueError):
        _split_chronological(dates, n_folds=5)


# Integration test on Day 11 snapshot
def test_real_walk_forward_passes_phase2_floor():
    cache = Path("data/cache")
    files = sorted(cache.glob("sector_panel_*.parquet"))
    if not files:
        pytest.skip("no panel snapshot")
    panel = pd.read_parquet(files[-1])
    wf = run_walk_forward(panel, horizon="6m")
    assert wf.pass_phase2_floor, (
        f"Walk-forward FAIL: {wf.n_folds_pass}/{wf.n_folds_total} folds positive"
    )
    assert wf.n_folds_pass >= 4, f"only {wf.n_folds_pass} of 5 folds positive"
