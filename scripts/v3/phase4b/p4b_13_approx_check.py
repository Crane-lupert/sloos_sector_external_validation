# v3 reference implementation - as run on 2026-11-21; absolute paths replaced by v3paths (see scripts/v3/README.md)
"""Phase 4B / step 13 - check of the approximate SLOOS release dates (dates only, no returns).

1. Rebuild the phase-1 rule (scripts/13_release_tables.py): approx = fred_date + median lag (days) by quarter-of-year over
   the 1997-2001 exact releases; confirm it reproduces approx_release_regular_practice.
2. Where the exact date is known (1997-2026 releases), apply the same rule and the PHASE4B entry rule
   (entry = close of the 10th trading day strictly after the approximate date) and count releases whose actual date is
   on or after that entry day (= the approximate-date entry would not have been strictly after the release).
3. List the approximate-dated releases of the 4B window with their entry dates.
Output: logs/p4b_13_approx_check.log, out/approx_release_entry_check.csv
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from v3paths import V3WORK, WRDS_DUMP, REPO_CACHE
import sys
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np
import pandas as pd
from p4blib import *

pd.set_option("display.width", 250)
cal = pd.DatetimeIndex(pd.read_parquet(C + "dsi_1989_2025.parquet").date)
rel = pd.read_csv(O1 + "release_dates_US_SLOOS.csv", parse_dates=["fred_date", "release_date", "approx_release_regular_practice"])
rel["q"] = rel.fred_date.dt.quarter
rel["lag"] = (rel.release_date - rel.fred_date).dt.days
base = rel[rel.release_date.notna() & rel.fred_date.dt.year.between(1997, 2001)]
med = base.groupby("q").lag.median()
print("median lag (days from quarter start) by quarter, 1997-2001 exact releases:", med.to_dict(), "| n per quarter", base.groupby("q").size().to_dict())
rel["rule_approx"] = rel.fred_date + pd.to_timedelta(rel.q.map(med).astype(int), unit="D")
a = rel[rel.approx_release_regular_practice.notna()]
print("rule reproduces approx_release_regular_practice for all", len(a), "approx rows:", bool((a.rule_approx == a.approx_release_regular_practice).all()))


def entry_after_approx(d):
    i = first_after(cal, d) + 9
    return cal[i] if i < len(cal) else pd.NaT


ex = rel[rel.release_date.notna() & (rel.release_date <= cal[-1] - pd.Timedelta(days=20))].copy()
ex["rule_entry"] = ex.rule_approx.map(entry_after_approx)
ex["actual_minus_approx_days"] = (ex.release_date - ex.rule_approx).dt.days
ex["actual_on_or_after_rule_entry"] = ex.release_date >= ex.rule_entry
ex["slack_days"] = (ex.rule_entry - ex.release_date).dt.days
for lab, lo, hi in [("1997-2001 (regime used to build the rule)", 1997, 2001), ("2002-2024", 2002, 2024), ("1997-2024", 1997, 2024)]:
    z = ex[ex.fred_date.dt.year.between(lo, hi)]
    print(f"{lab}: n {len(z)} | actual - approx (days): min {z.actual_minus_approx_days.min()}, median {z.actual_minus_approx_days.median():.0f}, "
          f"max {z.actual_minus_approx_days.max()} | actual release on or after the approx+10TD entry day: {int(z.actual_on_or_after_rule_entry.sum())} "
          f"| min slack (entry - actual, calendar days) {z.slack_days.min()}")
late = ex[ex.actual_on_or_after_rule_entry]
if len(late):
    print("releases where the approx+10TD entry would not be strictly after the actual release:")
    print(late[["fred_date", "release_date", "rule_approx", "rule_entry", "actual_minus_approx_days"]].to_string(index=False))
w = rel[(rel.fred_date >= "1990-07-01") & (rel.fred_date <= "2000-04-01") & rel.release_date.isna()].copy()
w["entry_close"] = w.approx_release_regular_practice.map(entry_after_approx)
w["cal_days_approx_to_entry"] = (w.entry_close - w.approx_release_regular_practice).dt.days
print("\napproximate-dated releases in the 4B window:", len(w))
print(w[["fred_date", "approx_release_regular_practice", "entry_close", "cal_days_approx_to_entry"]].to_string(index=False))
out = pd.concat([ex.assign(kind="exact_known")[["kind", "fred_date", "release_date", "rule_approx", "rule_entry", "actual_minus_approx_days",
                                                "actual_on_or_after_rule_entry", "slack_days"]],
                 w.assign(kind="approx_4B_window")[["kind", "fred_date", "approx_release_regular_practice", "entry_close", "cal_days_approx_to_entry"]]],
                ignore_index=True)
out.to_csv(O + "approx_release_entry_check.csv", index=False)
print("saved out/approx_release_entry_check.csv")
