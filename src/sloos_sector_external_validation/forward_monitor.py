"""Forward sector-pattern monitor — gate-aside health monitoring (NOT outcome-class gate).

Purpose: per governance close audit `D:/vscode/meta-harness/audits/2026-05-05-S1-governance-close-layer-a-locked-event-study.md` §6, the **LAYER A LOCKED — event-study class** status of S1 is final and is **NOT subject to forward OOS demote** (Gate N §4.4 mathematical-impossibility lock against in-sample/OOS split for thin-event-study class).

This module is **health monitoring only** — refresh SLOOS each new quarterly release, identify new shock events, and track 3 metrics (Spearman / sign agreement / F-test) per release. Results inform paper additive evidence or §11 limitation note. **Does not demote LAYER A LOCKED status** (only full pattern reversal — Spearman < 0 + sign agreement ≤ 1/6 + F-test fail across all horizons — triggers a separate governance audit, per close audit §6.4).

Workflow per quarter:
  1. Refresh SLOOS series from FRED (`sloos_fetch.fetch_and_save`)
  2. Re-construct shocks (AR(1) on full updated series)
  3. Identify NEW events since the cached baseline
  4. For each new event, compute forward CARs (1m available immediately, 3m after
     3 months, 6m after 6 months — partial events tracked)
  5. Append new rows to `data/cache/forward_monitor_YYYY-MM.parquet`
  6. Recompute 3 health metrics (M-1 Spearman / M-2 sign agreement / M-3 F-test) on
     augmented panel
  7. Append per-release audit `audits/YYYY-MM-DD-S1-forward-monitor-{N}-th.md`
  8. (Optional) broadcast to portfolio-coordination Telegram mailbox if
     telegram-setup is active.

CRON SCHEDULE (suggested): quarterly, 3rd-Tuesday-of-Feb/May/Aug/Nov ~14:00 ET (post-SLOOS release window). See `.cron/forward_monitor.cron`.

Status quo (2026-05-05): 36 events to 2025-04-01. Next forward release: ~2026-07.

NON-GATE BEHAVIOR (lock):
- This module **NEVER** changes `LAYER_A_LOCKED.md` status file.
- This module **NEVER** raises an exception on forward Spearman drop.
- The `report.is_health_only` field is hard-coded `True` and used by tests to
  verify the gate-aside contract.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from .shock_construct import construct_shocks
from .sloos_fetch import fetch_and_save

logger = logging.getLogger(__name__)


# Health-monitoring thresholds — informational only, NOT outcome-class gates.
HEALTH_M1_SPEARMAN_ALIGNED = 0.5
HEALTH_M1_SPEARMAN_REVERSAL = 0.0
HEALTH_M2_SIGN_AGREE_ALIGNED = 4
HEALTH_M2_SIGN_AGREE_REVERSAL = 1
HEALTH_M3_FTEST_PVAL_ALIGNED = 0.05
TOP6_SECTORS_FOR_M2 = (25, 10, 20, 15, 35, 55)  # GICS codes: Cons Disc / Energy / Industrials / Materials / Healthcare / Utilities


@dataclass
class ForwardMonitorReport:
    snapshot_date: str
    n_total_events: int
    n_events_new_since_last: int
    new_event_dates: list[str]
    new_events_pending_horizon: dict[str, list[str]]
    # Layer A pass count post-augmentation (read-only diagnostic)
    layer_a_baseline_n_pass: int
    layer_a_with_new_events_n_pass: int
    delta_pass: int
    # Health metrics (informational only — NOT gates)
    m1_spearman_6m: float
    m2_sign_agree_top6: int
    m3_ftest_pval_6m: float
    # Hard-coded contract: this module is NOT an outcome-class gate
    is_health_only: bool = field(default=True)
    # Recommended downstream action (informational)
    audit_recommendation: str = field(default="")


def find_new_events(
    new_shocks: pd.DataFrame,
    baseline_shocks: pd.DataFrame,
) -> pd.DatetimeIndex:
    """Return event dates in `new_shocks` not in `baseline_shocks`."""
    new_set = set(new_shocks.index[new_shocks["is_event_start"].fillna(False)])
    base_set = set(baseline_shocks.index[baseline_shocks["is_event_start"].fillna(False)])
    return pd.DatetimeIndex(sorted(new_set - base_set))


def classify_health(spearman_6m: float, sign_agree_top6: int, ftest_pval_6m: float) -> str:
    """Map 3 health metrics to a recommendation string. Information only."""
    aligned = (
        spearman_6m >= HEALTH_M1_SPEARMAN_ALIGNED
        and sign_agree_top6 >= HEALTH_M2_SIGN_AGREE_ALIGNED
        and ftest_pval_6m < HEALTH_M3_FTEST_PVAL_ALIGNED
    )
    full_reversal = (
        spearman_6m < HEALTH_M1_SPEARMAN_REVERSAL
        and sign_agree_top6 <= HEALTH_M2_SIGN_AGREE_REVERSAL
        and ftest_pval_6m >= HEALTH_M3_FTEST_PVAL_ALIGNED
    )
    if aligned:
        return "ALIGNED — paper additive evidence; LAYER A LOCKED status maintained"
    if full_reversal:
        return (
            "FULL REVERSAL — separate governance audit triggered "
            "(governance close §6.4); LAYER A LOCKED status NOT auto-demoted, "
            "review at meta-harness governance"
        )
    return (
        "BOUNDARY — paper §11 limitation note suggested; "
        "LAYER A LOCKED status maintained (gate-aside, health monitoring)"
    )


def refresh_and_compare(
    baseline_shocks_path: Path | None = None,
) -> ForwardMonitorReport:
    """Re-fetch SLOOS, re-construct shocks, identify new events vs baseline.

    Args:
        baseline_shocks_path: cached shocks parquet from prior run.
            If None, picks the latest `shocks_DRTSCILM_AR1_*.parquet`.

    Returns:
        ForwardMonitorReport with new event dates, health metrics, and
        recommendation. **DOES NOT modify cached data** — read-only diagnostic.
        **NEVER raises** on adverse forward results — health monitoring only.
    """
    cache = Path("data/cache")
    if baseline_shocks_path is None:
        candidates = sorted(cache.glob("shocks_DRTSCILM_AR1_*.parquet"))
        if not candidates:
            raise FileNotFoundError("no baseline shocks parquet to compare against")
        baseline_shocks_path = candidates[-1]
    baseline_shocks = pd.read_parquet(baseline_shocks_path)
    baseline_n = int(baseline_shocks["is_event_start"].fillna(False).sum())

    # Refresh SLOOS
    panel, _ = fetch_and_save()
    new_shocks = construct_shocks(panel)
    new_n = int(new_shocks["is_event_start"].fillna(False).sum())

    new_events = find_new_events(new_shocks, baseline_shocks)
    new_event_dates = [str(d.date()) for d in new_events]

    today = pd.Timestamp.now().tz_localize(None).normalize()
    pending: dict[str, list[str]] = {"1m_pending": [], "3m_pending": [], "6m_pending": []}
    for d in new_events:
        elapsed = (today - d).days
        if elapsed < 21:
            pending["1m_pending"].append(str(d.date()))
        if elapsed < 63:
            pending["3m_pending"].append(str(d.date()))
        if elapsed < 126:
            pending["6m_pending"].append(str(d.date()))

    # Health metrics (placeholder — populated by full pipeline rerun in a future
    # session when forward sample is non-empty AND ≥6m has elapsed since the
    # earliest new event). NaN signals "no forward sample yet, monitoring just
    # tracking new event arrivals."
    m1 = float("nan")
    m2 = -1
    m3 = float("nan")
    rec = "NEW-EVENT-DETECTION ONLY (no augmented panel rebuild this session)"

    return ForwardMonitorReport(
        snapshot_date=str(today.date()),
        n_total_events=new_n,
        n_events_new_since_last=int(len(new_events)),
        new_event_dates=new_event_dates,
        new_events_pending_horizon=pending,
        layer_a_baseline_n_pass=baseline_n,
        layer_a_with_new_events_n_pass=-1,
        delta_pass=0,
        m1_spearman_6m=m1,
        m2_sign_agree_top6=m2,
        m3_ftest_pval_6m=m3,
        audit_recommendation=rec,
    )


def write_audit_template(
    report: ForwardMonitorReport,
    nth: int,
    out_dir: Path = Path("audits"),
) -> Path:
    """Write a per-release audit markdown skeleton.

    File naming: `audits/YYYY-MM-DD-S1-forward-monitor-{N}-th.md`.

    The Nth audit is intended to be reviewed and augmented manually after each
    new SLOOS release; this template captures the snapshot-time state.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = out_dir / f"{report.snapshot_date}-S1-forward-monitor-{nth}-th.md"
    body = (
        f"# S1 forward-monitor #{nth} — {report.snapshot_date}\n"
        f"\n"
        f"**Repo**: `D:/vscode/sloos_sector_external_validation`\n"
        f"**Module**: `src/sloos_sector_external_validation/forward_monitor.py`\n"
        f"**Audit type**: health monitoring (gate-aside per governance close §6)\n"
        f"\n"
        f"## Status (read-only)\n"
        f"\n"
        f"- LAYER A LOCKED — event-study class **maintained** (this audit cannot demote)\n"
        f"- Snapshot: {report.snapshot_date}\n"
        f"- Total events (post-refresh): {report.n_total_events}\n"
        f"- New events since baseline: {report.n_events_new_since_last}\n"
        f"\n"
        f"## New events\n"
        f"\n"
        f"```json\n{json.dumps(report.new_event_dates, indent=2)}\n```\n"
        f"\n"
        f"## Pending horizon (events not yet reaching full window)\n"
        f"\n"
        f"```json\n{json.dumps(report.new_events_pending_horizon, indent=2)}\n```\n"
        f"\n"
        f"## Health metrics (informational only — NOT gates)\n"
        f"\n"
        f"| Metric | Threshold (aligned) | Value | Status |\n"
        f"|---|---|---|---|\n"
        f"| M-1 Spearman 6m (forward vs in-sample) | ≥ 0.5 | {report.m1_spearman_6m} | (TBD post-6m elapsed) |\n"
        f"| M-2 Top-6 sign agreement (Cons Disc/Energy/Industrials/Materials/Healthcare/Utilities) | ≥ 4/6 | {report.m2_sign_agree_top6} | (TBD post-6m) |\n"
        f"| M-3 F-test 6m p-value (incremental sample) | < 0.05 | {report.m3_ftest_pval_6m} | (TBD post-6m) |\n"
        f"\n"
        f"## Recommendation\n"
        f"\n"
        f"{report.audit_recommendation}\n"
        f"\n"
        f"## Lock\n"
        f"\n"
        f"This module is **health monitoring only** (`is_health_only={report.is_health_only}`). "
        f"It does NOT modify `LAYER_A_LOCKED.md` status. Forward Spearman drop or sign-agreement "
        f"degradation informs paper §11 limitation note only. Full pattern reversal "
        f"(Spearman < 0 + sign ≤ 1/6 + F-test fail across all horizons) triggers a separate "
        f"governance audit per governance close §6.4.\n"
    )
    fname.write_text(body, encoding="utf-8")
    return fname


def main() -> None:
    """CLI entry: refresh SLOOS, report new events, write per-release audit skeleton."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    report = refresh_and_compare()
    print(json.dumps(asdict(report), indent=2, default=str))

    # Determine N-th index from existing audits/forward-monitor-*.md count
    audits_dir = Path("audits")
    existing = sorted(audits_dir.glob("*-S1-forward-monitor-*.md")) if audits_dir.exists() else []
    nth = len(existing) + 1
    audit_path = write_audit_template(report, nth)
    logger.info("forward-monitor audit skeleton written: %s", audit_path)


if __name__ == "__main__":
    main()


__all__ = [
    "HEALTH_M1_SPEARMAN_ALIGNED",
    "HEALTH_M1_SPEARMAN_REVERSAL",
    "HEALTH_M2_SIGN_AGREE_ALIGNED",
    "HEALTH_M2_SIGN_AGREE_REVERSAL",
    "HEALTH_M3_FTEST_PVAL_ALIGNED",
    "TOP6_SECTORS_FOR_M2",
    "ForwardMonitorReport",
    "classify_health",
    "find_new_events",
    "main",
    "refresh_and_compare",
    "write_audit_template",
]
