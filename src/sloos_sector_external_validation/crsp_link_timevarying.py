"""Time-varying CRSP↔Compustat link via dsenames.ncusip + comp.names.year1/year2.

Workaround for blocked `ccmxpf_lnkhist`. Achieves time-varying linkage by
combining:

- CRSP `crsp_a_stock.dsenames`:
    (permno, namedt, nameendt, ncusip, comnam, ticker)
    The `ncusip` is the CUSIP active during [namedt, nameendt).
    A single permno can have multiple rows if name/CUSIP changed over time.

- Compustat `comp_na_daily_all.names`:
    (gvkey, cusip, conm, tic, year1, year2)
    `year1`/`year2` are the validity range for the gvkey-CUSIP mapping.

Join key: SUBSTR(ncusip, 1, 8) ↔ SUBSTR(cusip, 1, 8).

For each match, the valid period is intersection:
    valid_from = max(namedt, DATE(year1, 1, 1))
    valid_to   = min(nameendt or far-future, DATE(year2, 12, 31))

When valid_from < valid_to, emit (permno, gvkey, valid_from, valid_to) row.

Result is a time-varying link panel. `link_at_event()` filters to rows
valid at a given event date. This is THE substitute for ccmxpf_lnkhist
linktype/linkprim functionality (modulo the link-quality flags which we
cannot reconstruct).

Comparisons vs alternatives:
- Static CUSIP8 (crsp_link.build_cusip8_link): 95.4% R3000 coverage, but
  ignores CUSIP changes (~23% of permnos have multi-period CUSIP history).
- Time-varying dsenames (this module): preserves CUSIP changes; coverage
  comparable; suited for academic-grade per-event linkage.
- Real ccmxpf_lnkhist (currently USAGE-blocked): adds linktype/linkprim
  quality flags that filter to academically-valid primary links. Without
  these flags, our time-varying link includes lower-quality / spinoff /
  preferred-class links that ccmxpf would normally reject. Most production
  link rows are LC/LU primary, so the difference is small in practice.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from .wrds_courier_adapter import query

logger = logging.getLogger(__name__)


FAR_FUTURE = pd.Timestamp("2099-12-31")


def _pull_dsenames(gvkeys: list[str] | None = None) -> pd.DataFrame:
    """Pull dsenames rows, optionally pre-filtered to CUSIP8s of universe gvkeys.

    Pre-filter via Compustat names CUSIP8 set: this is dramatically faster
    than pulling all 117k dsenames rows and post-filtering.
    """
    if gvkeys:
        gv_quoted = ",".join(f"'{g}'" for g in gvkeys)
        sql = f"""
            WITH univ_cusip8 AS (
                SELECT DISTINCT SUBSTR(cusip, 1, 8) AS cusip8
                FROM comp_na_daily_all.names
                WHERE cusip IS NOT NULL AND gvkey IN ({gv_quoted})
            )
            SELECT d.permno, d.namedt, d.nameendt, d.ncusip, d.comnam, d.ticker
            FROM crsp_a_stock.dsenames d
            INNER JOIN univ_cusip8 u ON SUBSTR(d.ncusip, 1, 8) = u.cusip8
            WHERE d.ncusip IS NOT NULL
            ORDER BY d.permno, d.namedt
        """
    else:
        sql = """
            SELECT permno, namedt, nameendt, ncusip, comnam, ticker
            FROM crsp_a_stock.dsenames
            WHERE ncusip IS NOT NULL
            ORDER BY permno, namedt
        """
    return query(sql)


def _pull_comp_names(gvkeys: list[str] | None = None) -> pd.DataFrame:
    base = """
        SELECT gvkey, cusip, conm, tic, year1, year2
        FROM comp_na_daily_all.names
        WHERE cusip IS NOT NULL
    """
    if gvkeys:
        quoted = ",".join(f"'{g}'" for g in gvkeys)
        base += f" AND gvkey IN ({quoted})"
    return query(base)


def build_time_varying_link(
    gvkeys: list[str] | None = None,
    use_compustat_year_filter: bool = False,
    extend_open_periods_to_future: bool = True,
) -> pd.DataFrame:
    """Build time-varying (permno, gvkey, valid_from, valid_to) link panel.

    Args:
        use_compustat_year_filter: if True, additionally intersect dsenames
            period with comp.names year1/year2. WARNING: this is overly
            restrictive in practice — comp.names year1/year2 mark each
            individual name-record's validity, not the gvkey's overall
            tracking range. Many firms have name records with narrow
            year1/year2 even though the gvkey persists. Default False
            uses dsenames period only (CRSP-side time validity), which
            gives proper survivor-bias-corrected coverage.
        extend_open_periods_to_future: if True (default), dsenames rows
            whose nameendt equals the CRSP data cutoff (2024-12-31) are
            treated as "still active" — extends valid_to to FAR_FUTURE.
            This correctly handles firms still listed at end-of-data.

    Output columns:
      permno (int), gvkey (str), valid_from (Timestamp), valid_to (Timestamp),
      cusip8 (str).
    """
    dsenames = _pull_dsenames(gvkeys=gvkeys)
    comp_names = _pull_comp_names(gvkeys=gvkeys)
    if dsenames.empty or comp_names.empty:
        return pd.DataFrame(columns=["permno", "gvkey", "valid_from", "valid_to", "cusip8"])

    dsenames = dsenames.copy()
    dsenames["cusip8"] = dsenames["ncusip"].astype(str).str[:8]
    dsenames["namedt"] = pd.to_datetime(dsenames["namedt"])
    dsenames["nameendt"] = pd.to_datetime(dsenames["nameendt"])

    if extend_open_periods_to_future:
        # If a firm's last dsenames row ends at the data cutoff, treat as still active
        last_per_permno = dsenames.groupby("permno")["nameendt"].transform("max")
        is_last_row = dsenames["nameendt"] == last_per_permno
        cutoff = dsenames["nameendt"].max()
        at_cutoff = dsenames["nameendt"] == cutoff
        dsenames.loc[is_last_row & at_cutoff, "nameendt"] = FAR_FUTURE

    comp_names = comp_names.copy()
    comp_names["cusip8"] = comp_names["cusip"].astype(str).str[:8]

    merged = dsenames.merge(
        comp_names[["gvkey", "cusip8"]].drop_duplicates(),
        on="cusip8",
        how="inner",
    )

    if use_compustat_year_filter:
        # Optional: also intersect with comp.names year1/year2
        comp_names["year1_dt"] = pd.to_datetime(
            comp_names["year1"].astype("Int64").astype(str) + "-01-01", errors="coerce"
        )
        comp_names["year2_dt"] = pd.to_datetime(
            comp_names["year2"].astype("Int64").astype(str) + "-12-31", errors="coerce"
        )
        merged_year = merged.merge(
            comp_names[["gvkey", "cusip8", "year1_dt", "year2_dt"]],
            on=["gvkey", "cusip8"],
            how="left",
        )
        merged = merged_year
        namedt = merged["namedt"]
        nameendt = merged["nameendt"].fillna(FAR_FUTURE)
        year1_dt = merged["year1_dt"].fillna(pd.Timestamp("1900-01-01"))
        year2_dt = merged["year2_dt"].fillna(FAR_FUTURE)
        merged["valid_from"] = pd.concat([namedt, year1_dt], axis=1).max(axis=1)
        merged["valid_to"] = pd.concat([nameendt, year2_dt], axis=1).min(axis=1)
    else:
        # Default: dsenames period only (CRSP firm-existence validity)
        merged["valid_from"] = merged["namedt"]
        merged["valid_to"] = merged["nameendt"].fillna(FAR_FUTURE)

    valid = merged[merged["valid_from"] < merged["valid_to"]].copy()
    out = valid[["permno", "gvkey", "valid_from", "valid_to", "cusip8"]].drop_duplicates(
        subset=["permno", "gvkey", "valid_from", "valid_to"]
    ).reset_index(drop=True)
    out["permno"] = out["permno"].astype(int)
    return out


def link_at_event(
    link: pd.DataFrame,
    event_date: pd.Timestamp,
) -> pd.DataFrame:
    """Filter time-varying link to rows valid at event_date."""
    if link.empty:
        return link
    evt = pd.Timestamp(event_date)
    valid = (link["valid_from"] <= evt) & (link["valid_to"] > evt)
    out = link[valid].copy()
    return out.drop_duplicates(subset=["permno", "gvkey"]).reset_index(drop=True)


def cache_link(
    universe: pd.DataFrame,
    out_dir: Path = Path("data/cache"),
    save: bool = True,
) -> pd.DataFrame:
    gvkeys = universe["gvkey"].dropna().astype(str).unique().tolist()
    logger.info("building time-varying link for %d universe gvkeys...", len(gvkeys))
    link = build_time_varying_link(gvkeys=gvkeys)
    n_pairs = link.drop_duplicates(subset=["permno", "gvkey"]).shape[0]
    logger.info("link rows: %d (unique permno×gvkey pairs: %d)", len(link), n_pairs)
    if save:
        out_dir.mkdir(parents=True, exist_ok=True)
        snap = pd.Timestamp.utcnow().tz_localize(None).strftime("%Y-%m-%d")
        out_path = out_dir / f"ccm_link_timevarying_{snap}.parquet"
        link.to_parquet(out_path)
    return link


def link_summary(link: pd.DataFrame, universe: pd.DataFrame | None = None) -> dict:
    if link.empty:
        return {"n_rows": 0}
    pairs = link.drop_duplicates(subset=["permno", "gvkey"])
    n_pairs = int(len(pairs))
    n_permno = int(pairs["permno"].nunique())
    n_gvkey = int(pairs["gvkey"].nunique())
    multi_periods_per_pair = link.groupby(["permno", "gvkey"]).size()
    multi_pairs_per_permno = pairs.groupby("permno")["gvkey"].nunique()
    multi_pairs_per_gvkey = pairs.groupby("gvkey")["permno"].nunique()
    out = {
        "n_link_rows": int(len(link)),
        "n_unique_permno_gvkey_pairs": n_pairs,
        "n_unique_permnos": n_permno,
        "n_unique_gvkeys": n_gvkey,
        "n_pairs_with_multi_periods": int((multi_periods_per_pair > 1).sum()),
        "n_permnos_with_multi_gvkey": int((multi_pairs_per_permno > 1).sum()),
        "n_gvkeys_with_multi_permno": int((multi_pairs_per_gvkey > 1).sum()),
    }
    if universe is not None:
        univ_gvkeys = set(universe["gvkey"].dropna().astype(str).unique())
        matched = univ_gvkeys & set(pairs["gvkey"].astype(str).unique())
        out["universe_gvkeys"] = len(univ_gvkeys)
        out["universe_gvkeys_matched"] = len(matched)
        out["universe_coverage_pct"] = round(len(matched) / max(len(univ_gvkeys), 1) * 100, 1)
    return out


__all__ = [
    "FAR_FUTURE",
    "build_time_varying_link",
    "cache_link",
    "link_at_event",
    "link_summary",
]
