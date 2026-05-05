"""CRSP↔Compustat link via CUSIP8 join (Phase 3 honest revision).

The proper time-varying link table `comp.ccmxpf_lnkhist` (or
`crsp_a_ccm.ccmxpf_lnkhist`) is USAGE-blocked in our WRDS subscription
(see `E:/wrds-data-courier/outbox/S1-ccmxpf-lnkhist-blocked-20260505-140255.json`).

Courier-recommended alternative is a CUSIP8 join via existing tables:
  crsp_a_stock.dsenames.cusip ↔ comp_na_daily_all.names.cusip

On our R3000 universe (2,898 gvkeys), this gives 95.4% permno coverage
(2,765 firms), 1-to-1 mapping, no ambiguity.

LIMITATION: static link only. CUSIP changes / spinoffs / mergers that
cause permno↔gvkey reassignment are not tracked. Paper §11 limitation.
When `ccmxpf_lnkhist` is unblocked, swap to time-varying link and
re-validate.

SWAP-IN PREP (2026-05-05 follow-up): a 1,927-row sample of the schema
is available at `wrdsappssamp_all.ccmxpf_lnkhist` with simplified
columns (lpermno, gvkey, linkdt, linkenddt). Production version adds:
  - linktype: LC/LU/LX/NU/etc. — link quality flag
  - linkprim: P/C/J/N — primary marker
  - usedflag: -1/+1 — used in CCM merged file
  - liid: Compustat IID for link

Production swap-in MUST filter `linktype IN ('LC','LU') AND linkprim
IN ('P','C')` for academic-grade linkage. The function
`build_ccmxpf_link()` below implements that filter and is ready to be
called once the real table USAGE is unblocked.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from .wrds_courier_adapter import query

logger = logging.getLogger(__name__)


def build_cusip8_link(gvkeys: list[str] | None = None) -> pd.DataFrame:
    """Build permno↔gvkey link via CUSIP8 SUBSTR.

    Args:
        gvkeys: optional whitelist to restrict the join. Otherwise pulls all.

    Returns:
        DataFrame with columns [permno, gvkey, cusip8, conm, tic].
    """
    base_sql = """
        SELECT
            d.permno,
            n.gvkey,
            SUBSTR(d.cusip, 1, 8) AS cusip8,
            n.conm,
            n.tic
        FROM crsp_a_stock.dsenames d
        INNER JOIN comp_na_daily_all.names n
          ON SUBSTR(d.cusip, 1, 8) = SUBSTR(n.cusip, 1, 8)
        WHERE d.cusip IS NOT NULL AND n.cusip IS NOT NULL
    """
    if gvkeys:
        quoted = ",".join(f"'{g}'" for g in gvkeys)
        base_sql += f" AND n.gvkey IN ({quoted})"
    df = query(base_sql)
    # Dedupe (one row may exist for multiple share classes / cusip versions per pair)
    df = df.drop_duplicates(subset=["permno", "gvkey"]).reset_index(drop=True)
    return df


def cache_link(
    universe: pd.DataFrame,
    out_dir: Path = Path("data/cache"),
    save: bool = True,
) -> pd.DataFrame:
    """Build the CCM link restricted to a universe and cache as parquet."""
    gvkeys = universe["gvkey"].dropna().astype(str).unique().tolist()
    logger.info("building CUSIP8 link for %d universe gvkeys...", len(gvkeys))
    link = build_cusip8_link(gvkeys=gvkeys)
    logger.info("link rows: %d, unique permnos: %d, unique gvkeys: %d",
                len(link), link["permno"].nunique(), link["gvkey"].nunique())
    if save:
        out_dir.mkdir(parents=True, exist_ok=True)
        snap = pd.Timestamp.utcnow().tz_localize(None).strftime("%Y-%m-%d")
        out_path = out_dir / f"ccm_link_cusip8_{snap}.parquet"
        link.to_parquet(out_path)
    return link


def link_summary(link: pd.DataFrame, universe: pd.DataFrame | None = None) -> dict:
    """Return coverage stats."""
    n_pairs = int(len(link))
    n_permno = int(link["permno"].nunique())
    n_gvkey = int(link["gvkey"].nunique())
    permno_per_gvkey = link.groupby("gvkey")["permno"].nunique()
    gvkey_per_permno = link.groupby("permno")["gvkey"].nunique()
    out = {
        "n_pairs": n_pairs,
        "n_unique_permnos": n_permno,
        "n_unique_gvkeys": n_gvkey,
        "ambiguity_gvkeys_with_multi_permno": int((permno_per_gvkey > 1).sum()),
        "ambiguity_permnos_with_multi_gvkey": int((gvkey_per_permno > 1).sum()),
    }
    if universe is not None:
        univ_gvkeys = set(universe["gvkey"].dropna().astype(str).unique())
        matched = univ_gvkeys & set(link["gvkey"].astype(str).unique())
        out["universe_gvkeys"] = len(univ_gvkeys)
        out["universe_gvkeys_matched"] = len(matched)
        out["universe_coverage_pct"] = round(len(matched) / max(len(univ_gvkeys), 1) * 100, 1)
    return out


def build_ccmxpf_link(
    schema_table: str = "crsp_a_ccm.ccmxpf_lnkhist",
    gvkeys: list[str] | None = None,
    apply_quality_filter: bool = True,
) -> pd.DataFrame:
    """Production CCM link via real ccmxpf_lnkhist (when USAGE unblocked).

    Args:
        schema_table: 'crsp_a_ccm.ccmxpf_lnkhist' (legacy) or 'crsp_m_ccm.ccmxpf_lnkhist'
            (monthly) or 'crsp_q_ccm.ccmxpf_lnkhist' (quarterly).
            Sample: 'wrdsappssamp_all.ccmxpf_lnkhist' (1,927 rows, schema-only).
        gvkeys: optional whitelist.
        apply_quality_filter: if True (default), filter to academic-grade
            primary links: linktype ∈ {LC, LU} ∧ linkprim ∈ {P, C}.
            Disable only for schema testing on the sample table.

    Returns DataFrame with columns: lpermno, gvkey, liid, linkdt, linkenddt,
    linktype, linkprim. Sample table has only the first 4 columns; quality
    filter cannot be applied there.
    """
    select_cols = "lpermno, gvkey, linkdt, linkenddt"
    if apply_quality_filter:
        select_cols += ", liid, linktype, linkprim, usedflag"

    sql = f"SELECT {select_cols} FROM {schema_table}"
    where_clauses = []
    if gvkeys:
        quoted = ",".join(f"'{g}'" for g in gvkeys)
        where_clauses.append(f"gvkey IN ({quoted})")
    if apply_quality_filter:
        where_clauses.append("linktype IN ('LC','LU')")
        where_clauses.append("linkprim IN ('P','C')")
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)
    df = query(sql)
    if "lpermno" in df.columns:
        df = df.rename(columns={"lpermno": "permno"})
    return df


def link_to_event_aware(
    link_df: pd.DataFrame,
    event_date: pd.Timestamp,
    gvkey_col: str = "gvkey",
    permno_col: str = "permno",
    linkdt_col: str = "linkdt",
    linkenddt_col: str = "linkenddt",
) -> pd.DataFrame:
    """Filter a time-varying link table to rows valid AT event_date.

    A row is valid at event_date iff linkdt ≤ event_date AND
    (linkenddt IS NULL OR linkenddt > event_date).

    Returns DataFrame with one row per (gvkey, permno) pair active at
    event_date. If multiple permnos map to the same gvkey at the event
    (e.g., share-class restructure), all are returned — caller handles
    deduplication if needed.

    Use this with `build_ccmxpf_link()` for proper time-varying linkage:

        full_link = build_ccmxpf_link(gvkeys=universe_gvkeys)  # historical
        for evt in event_dates:
            evt_link = link_to_event_aware(full_link, evt)
            # ... use evt_link.permno for CRSP queries at this event date
    """
    if link_df.empty:
        return link_df
    df = link_df.copy()
    if linkdt_col not in df.columns or linkenddt_col not in df.columns:
        raise ValueError(
            f"link table must have {linkdt_col} and {linkenddt_col} columns. "
            f"Schema-only sample without these cannot be used for event-aware filtering."
        )
    valid = (df[linkdt_col] <= event_date) & (
        df[linkenddt_col].isna() | (df[linkenddt_col] > event_date)
    )
    return df[valid].reset_index(drop=True)


def smoke_test_sample() -> dict:
    """Pull the 1,927-row sample to verify schema. Safe to call anytime.

    Returns dict with row count, distinct permnos/gvkeys, columns observed.
    """
    df = query("SELECT * FROM wrdsappssamp_all.ccmxpf_lnkhist LIMIT 5000")
    return {
        "n_rows": int(len(df)),
        "columns": list(df.columns),
        "n_unique_lpermno": int(df["lpermno"].nunique()) if "lpermno" in df.columns else 0,
        "n_unique_gvkey": int(df["gvkey"].nunique()) if "gvkey" in df.columns else 0,
        "linkdt_min": str(df["linkdt"].min()) if "linkdt" in df.columns else "",
        "linkdt_max": str(df["linkdt"].max()) if "linkdt" in df.columns else "",
        "n_active_links": int(df["linkenddt"].isna().sum()) if "linkenddt" in df.columns else 0,
        "note": "Sample-only schema lacks linktype/linkprim/usedflag/liid → cannot apply quality filter.",
    }


__all__ = [
    "build_ccmxpf_link",
    "build_cusip8_link",
    "cache_link",
    "link_summary",
    "link_to_event_aware",
    "smoke_test_sample",
]
