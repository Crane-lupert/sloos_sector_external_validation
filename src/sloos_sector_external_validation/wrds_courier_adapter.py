"""WRDS courier adapter — thin wrapper that maps S1 planning vocabulary
(secd / security / company) to the actual table names in the courier dump
(sec_dprc / namesd / company).

The bootstrap audit (audits/2026-05-05-S1-bootstrap-eod.md) records the
naming difference. This adapter is the single import point for downstream
modules so a future courier rename never propagates through src/.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd

_COURIER_SRC = Path("e:/wrds-data-courier/src")

if str(_COURIER_SRC) not in sys.path:
    sys.path.insert(0, str(_COURIER_SRC))

from wrds_courier_client import (  # noqa: E402
    describe_table,
    list_schemas,
    open_db,
    query,
    schema_info,
)

COMPUSTAT_SCHEMA = "comp_na_daily_all"

# Planning-vocabulary -> actual courier table.
# Update here only if courier renames; downstream code uses ALIASED names.
TABLE_ALIAS: dict[str, str] = {
    "secd": "sec_dprc",
    "security": "namesd",
    "company": "company",
    "names": "names",
    "fundq": "fundq",
    "funda": "funda",
}


def resolve(alias: str) -> str:
    """Return fully-qualified courier table for a planning alias.

    >>> resolve("secd")
    'comp_na_daily_all.sec_dprc'
    """
    table = TABLE_ALIAS.get(alias, alias)
    return f"{COMPUSTAT_SCHEMA}.{table}"


def query_alias(alias: str, where: str = "", select: str = "*", limit: int | None = None) -> pd.DataFrame:
    """Convenience: SELECT <select> FROM <resolved_alias> [WHERE ...] [LIMIT ...]."""
    sql = f"SELECT {select} FROM {resolve(alias)}"
    if where:
        sql += f" WHERE {where}"
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    return query(sql)


def smoke_test() -> dict[str, Any]:
    """Verify courier connection + alias resolution. Used in tests."""
    db = open_db()
    n_tables = len(db.execute("SHOW TABLES").fetchall())
    schemas = list_schemas()
    secd_resolved = resolve("secd")
    return {
        "courier_src": str(_COURIER_SRC),
        "n_tables": n_tables,
        "n_schemas": len(schemas),
        "secd_resolved": secd_resolved,
    }


__all__ = [
    "COMPUSTAT_SCHEMA",
    "TABLE_ALIAS",
    "describe_table",
    "list_schemas",
    "open_db",
    "query",
    "query_alias",
    "resolve",
    "schema_info",
    "smoke_test",
]
