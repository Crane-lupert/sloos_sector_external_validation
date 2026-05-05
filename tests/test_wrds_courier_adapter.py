"""Smoke tests for WRDS courier adapter.

Each test hits the real courier (read-only). They are fast (<1s) because
DuckDB metadata queries don't load CSV bodies.
"""

from __future__ import annotations

import pytest

from sloos_sector_external_validation.wrds_courier_adapter import (
    COMPUSTAT_SCHEMA,
    TABLE_ALIAS,
    open_db,
    resolve,
    smoke_test,
)


def test_table_alias_contains_required_keys():
    for alias in ("secd", "security", "company", "names"):
        assert alias in TABLE_ALIAS, f"alias '{alias}' missing from TABLE_ALIAS"


def test_resolve_secd_to_sec_dprc():
    assert resolve("secd") == f"{COMPUSTAT_SCHEMA}.sec_dprc"


def test_resolve_security_to_namesd():
    assert resolve("security") == f"{COMPUSTAT_SCHEMA}.namesd"


def test_resolve_unknown_passes_through():
    # Unknown alias falls back to the alias as table name. Useful for ad-hoc
    # tables that haven't been added to the alias map.
    assert resolve("fundq") == f"{COMPUSTAT_SCHEMA}.fundq"


def test_open_db_returns_connection():
    db = open_db()
    rows = db.execute("SELECT 1").fetchall()
    assert rows == [(1,)]


def test_smoke_test_reports_schemas():
    info = smoke_test()
    assert info["n_schemas"] >= 4, f"expected >= 4 schemas, got {info['n_schemas']}"
    assert info["secd_resolved"] == "comp_na_daily_all.sec_dprc"
