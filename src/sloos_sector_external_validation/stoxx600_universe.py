"""STOXX 600 universe build (Path B specific, S3).

Constructs UK + Eurozone-broad universes from Compustat Global STOXX 600
historical reconstitution (`comp_global_daily.g_idxcst_his` filtered to
gvkeyx=150376) joined with `comp_global_daily.g_company` for GICS sector
and ISO loc.

Universe definitions (per S3 reference validation §3.2 + courier outbox response
2026-05-05 234029 §g_idxcst_his_verification):

UK universe (loc='GBR'):
    - Currently-active firms: ~119 (verified 2026-05-06)
    - All-time historical members: ~450 (excludes mergers, delistings)
    - Bonferroni-K=33 power loss caveat: 1.4× vs Eurozone broad due to smaller N

Eurozone-broad universe (continental Europe ex-UK):
    - Currently-active firms: ~420 (verified 2026-05-06)
    - 24 ISO loc codes: DEU, FRA, CHE, SWE, ITA, NLD, ESP, DNK, FIN, NOR,
      BEL, IRL, AUT, PRT, LUX, POL, GRC, CZE, HUN, ISL, LIE, CYP, MLT, HRV
    - Excludes: USA, ZAF, HKG, AUS, MEX, KAZ, RUS, BMU, JEY, GIB, IMN, ARE, ISR
      (offshore / non-European listings on STOXX 600 occasionally)

Time-varying construction:
    - Read g_idxcst_his × g_company once into a master DataFrame
    - For any event date `t`, filter rows where `from <= t AND (thru IS NULL OR t <= thru)`
    - Survivor-bias check: every gvkey's `from` and `thru` are honored, so a firm
      that was in STOXX 600 in 2008 but delisted in 2010 IS counted for 2008
      events but NOT for 2012 events.

Note on "Eurozone-broad":
    The S3 reference validation broadly defines Eurozone as continental Europe
    (incl. CHE, SWE, DNK, NOR, POL — non-EUR-currency members). The ECB BLS
    aggregate (eurozone strict, U2 dimension) is the canonical shock proxy.
    The mismatch — broader equity universe vs strict EUR-area shock — is
    intentional: continental-European banks are highly EUR-area-exposed even
    if not directly EUR-domiciled (CHE banks, SWE banks). Robustness check on
    EUR-strict-only universe deferred to Phase 1.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from .preferred_universe import GICS_NAME

STOXX_600_GVKEYX = 150376

# ISO 3-letter codes for the broader "Continental Europe" Eurozone-broad universe.
# Includes EUR-area strict + non-EUR-area continental Europe (CHE, SWE, DNK, NOR, POL,
# GRC, CZE, HUN, ISL).
EUROZONE_BROAD_LOCS: list[str] = [
    "DEU",  # Germany
    "FRA",  # France
    "CHE",  # Switzerland (CHF, non-EU)
    "SWE",  # Sweden (SEK, EU non-eurozone)
    "ITA",  # Italy
    "NLD",  # Netherlands
    "ESP",  # Spain
    "DNK",  # Denmark (DKK, EU non-eurozone)
    "FIN",  # Finland
    "NOR",  # Norway (NOK, EEA non-EU)
    "BEL",  # Belgium
    "IRL",  # Ireland
    "AUT",  # Austria
    "PRT",  # Portugal
    "LUX",  # Luxembourg
    "POL",  # Poland (PLN, EU non-eurozone)
    "GRC",  # Greece
    "CZE",  # Czech Republic (CZK, EU non-eurozone)
    "HUN",  # Hungary (HUF, EU non-eurozone)
    "ISL",  # Iceland (EEA non-EU)
    "LIE",  # Liechtenstein (CHF zone, EEA)
    "CYP",  # Cyprus (eurozone)
    "MLT",  # Malta (eurozone)
    "HRV",  # Croatia (eurozone since 2023)
]

# Strict EUR-currency-area subset for Phase 1 robustness check.
EUROZONE_STRICT_LOCS: list[str] = [
    "DEU",
    "FRA",
    "ITA",
    "NLD",
    "ESP",
    "FIN",
    "BEL",
    "IRL",
    "AUT",
    "PRT",
    "LUX",
    "GRC",
    "CYP",
    "MLT",
    "HRV",
]

UK_LOC = "GBR"


def _open_courier():
    """Open the WRDS courier DuckDB connection (lifted from S1 wrds_courier_adapter pattern)."""
    courier_path = Path("e:/wrds-data-courier/src")
    if str(courier_path) not in sys.path:
        sys.path.insert(0, str(courier_path))
    from wrds_courier_client import open_db  # type: ignore[import-not-found]

    return open_db()


def query_stoxx600_master() -> pd.DataFrame:
    """Pull the full STOXX 600 historical reconstitution panel joined with g_company.

    Returns DataFrame with columns:
        gvkey, iid, from, thru, conml, gsector, loc, costat, ipodate, dldte
    where:
        from / thru: index membership window (DATE; thru IS NULL means still active)
        gsector: GICS sector code (10..60); NULL for ~2 unmapped firms
        loc: ISO 3-letter country code
        costat: 'A' (active) / 'I' (inactive — delisted)
    """
    db = _open_courier()
    rows = db.execute(
        """
        SELECT i.gvkey, i.iid, i."from" AS from_date, i.thru,
               g.conml, g.gsector, g.loc, g.costat, g.ipodate, g.dldte
        FROM comp_global_daily.g_idxcst_his i
        JOIN comp_global_daily.g_company g ON g.gvkey = i.gvkey
        WHERE i.gvkeyx = ?
        ORDER BY i.gvkey, i."from"
        """,
        [STOXX_600_GVKEYX],
    ).fetchall()
    cols = ["gvkey", "iid", "from_date", "thru", "conml", "gsector", "loc", "costat", "ipodate", "dldte"]
    df = pd.DataFrame(rows, columns=cols)
    df["from_date"] = pd.to_datetime(df["from_date"])
    df["thru"] = pd.to_datetime(df["thru"])
    df["ipodate"] = pd.to_datetime(df["ipodate"])
    df["dldte"] = pd.to_datetime(df["dldte"])
    return df


def build_uk_universe(master: pd.DataFrame | None = None) -> pd.DataFrame:
    """Filter master STOXX 600 panel to loc='GBR'."""
    if master is None:
        master = query_stoxx600_master()
    return master[master["loc"] == UK_LOC].reset_index(drop=True)


def build_eurozone_universe(
    master: pd.DataFrame | None = None,
    strict: bool = False,
) -> pd.DataFrame:
    """Filter master STOXX 600 panel to continental Europe ex-UK.

    Args:
        strict: if True, restrict to EUR-currency-area only (Phase 1 robustness).
                Default False = broad continental Europe per S3 reference validation.
    """
    if master is None:
        master = query_stoxx600_master()
    locs = EUROZONE_STRICT_LOCS if strict else EUROZONE_BROAD_LOCS
    return master[master["loc"].isin(locs)].reset_index(drop=True)


def firms_active_at(universe: pd.DataFrame, date: pd.Timestamp) -> pd.DataFrame:
    """Return rows of `universe` whose membership window covers `date`.

    A firm is "active in STOXX 600 at date `t`" iff
        from_date <= t <= COALESCE(thru, +infinity).

    Handles tz-naive vs tz-aware timestamps and second-vs-nanosecond precision
    by coercing both sides to ns tz-naive.
    """
    date = pd.Timestamp(date)
    if date.tzinfo is not None:
        date = date.tz_localize(None)
    date = date.normalize().as_unit("ns")
    from_arr = universe["from_date"].astype("datetime64[ns]")
    thru_arr = universe["thru"].astype("datetime64[ns]")
    in_window = (from_arr <= date) & (thru_arr.isna() | (thru_arr >= date))
    return universe[in_window].reset_index(drop=True)


def universe_size_per_event(
    universe: pd.DataFrame,
    event_dates: pd.DatetimeIndex,
) -> pd.DataFrame:
    """Per event date, count distinct gvkeys active. Useful for cell-n audits."""
    rows = []
    for d in event_dates:
        active = firms_active_at(universe, d)
        rows.append({"event_date": d, "n_firms": int(active["gvkey"].nunique())})
    return pd.DataFrame(rows)


def per_sector_n_audit(universe: pd.DataFrame, event_dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Pivot of (sector × event_date) firm counts.

    Rows: gsector (10..60); Cols: event_date; Cells: n distinct firms active that quarter.
    Last column appended: total distinct gvkeys per sector ever active during any event.
    """
    long_rows = []
    seen_per_sector: dict[int, set[str]] = {}
    for d in event_dates:
        active = firms_active_at(universe, d)
        per_sec = active.groupby("gsector")["gvkey"].nunique()
        for sec, n in per_sec.items():
            if pd.isna(sec):
                continue
            long_rows.append({"event_date": d, "gsector": int(sec), "n_firms": int(n)})
            seen_per_sector.setdefault(int(sec), set()).update(active.loc[active["gsector"] == sec, "gvkey"])

    long = pd.DataFrame(long_rows)
    if long.empty:
        return long
    pivot = long.pivot(index="gsector", columns="event_date", values="n_firms").fillna(0).astype(int)
    pivot["distinct_total"] = [len(seen_per_sector.get(int(s), set())) for s in pivot.index]
    pivot["sector_name"] = [GICS_NAME.get(int(s), f"Unknown {s}") for s in pivot.index]
    return pivot


def expected_per_cell_n(
    universe: pd.DataFrame,
    event_dates: pd.DatetimeIndex,
    horizons: list[int] | None = None,
) -> pd.DataFrame:
    """For each (sector × horizon) cell, the expected firm-event count is

        n_cell = sum_over_events( n_firms_active_at_event_in_sector )

    horizons here are window labels (1m / 3m / 6m); the firm-event count is the
    same per horizon since the same firm contributes one firm-event per event-window
    (the horizon affects the CAR computation later, not the n).

    Returns DataFrame with rows = sector, cols = ['horizon_1m', 'horizon_3m',
    'horizon_6m', 'sector_name']. The 50-event live-trading floor (CLAUDE.md
    §1.4 inherited) is the threshold for PASS.
    """
    if horizons is None:
        horizons = [1, 3, 6]
    rows: dict[int, dict[str, int | str]] = {}
    for d in event_dates:
        active = firms_active_at(universe, d)
        per_sec = active.groupby("gsector")["gvkey"].nunique()
        for sec, n in per_sec.items():
            if pd.isna(sec):
                continue
            sec_int = int(sec)
            rows.setdefault(sec_int, {f"horizon_{h}m": 0 for h in horizons})
            for h in horizons:
                rows[sec_int][f"horizon_{h}m"] = int(rows[sec_int][f"horizon_{h}m"]) + int(n)
    out = pd.DataFrame.from_dict(rows, orient="index")
    out.index.name = "gsector"
    out["sector_name"] = [GICS_NAME.get(int(s), f"Unknown {s}") for s in out.index]
    return out.sort_index()


def save_universes(
    uk: pd.DataFrame,
    eurozone: pd.DataFrame,
    out_dir: Path = Path("data/cache"),
    snap: str | None = None,
) -> dict[str, Path]:
    """Persist UK + Eurozone universe panels to parquet."""
    out_dir.mkdir(parents=True, exist_ok=True)
    if snap is None:
        snap = pd.Timestamp.utcnow().strftime("%Y-%m-%d")
    paths = {
        "uk": out_dir / f"stoxx600_uk_universe_{snap}.parquet",
        "eurozone": out_dir / f"stoxx600_eurozone_universe_{snap}.parquet",
    }
    uk.to_parquet(paths["uk"])
    eurozone.to_parquet(paths["eurozone"])
    return paths


__all__ = [
    "EUROZONE_BROAD_LOCS",
    "EUROZONE_STRICT_LOCS",
    "STOXX_600_GVKEYX",
    "UK_LOC",
    "build_eurozone_universe",
    "build_uk_universe",
    "expected_per_cell_n",
    "firms_active_at",
    "per_sector_n_audit",
    "query_stoxx600_master",
    "save_universes",
    "universe_size_per_event",
]
