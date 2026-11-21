# v3 reference implementation - as run on 2026-11-21; absolute paths replaced by v3paths (see scripts/v3/README.md)
"""Phase 4B shared library - copied from phase4/scripts/p4lib.py (unchanged logic) with the input paths made explicit.
Differences from p4lib: us_index() takes the daily-file path (legacy dsf or dsf_v2 extract) and the delisting table as arguments;
verdict_4b() implements PHASE4B_SPEC section 3 (confirm / consistent / refuted / strongly refuted). The phase-4 originals are not modified."""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from v3paths import V3WORK, WRDS_DUMP, REPO_CACHE
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm

W = V3WORK + ""
P4 = W + "phase4/"
P4C = P4 + "cache/"
P4O = P4 + "out/"
P4B = W + "phase4b/"
C = P4B + "cache/"
O = P4B + "out/"
O1 = W + "out/"
MULT = 100000
DAY0 = np.datetime64("1970-01-01", "D")
CATS = ["CI", "CRE", "RRE", "CC", "OC"]


def days(x):
    return (pd.DatetimeIndex(pd.to_datetime(x)).values.astype("datetime64[D]") - DAY0).astype(np.int64)


def jdump(obj, path):
    json.dump(obj, open(path, "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))


def first_after(cal, d):
    """index of first calendar day strictly after d"""
    return int(np.searchsorted(cal.values, np.datetime64(pd.Timestamp(d)), side="right"))


def first_on_after(cal, d):
    return int(np.searchsorted(cal.values, np.datetime64(pd.Timestamp(d)), side="left"))


def last_on_before(cal, d):
    return int(np.searchsorted(cal.values, np.datetime64(pd.Timestamp(d)), side="right")) - 1


class Keyed:
    """keyed arrays with 'last record <= day' lookup (copied from p4lib)"""
    def __init__(self, ids, dnum, **cols):
        ids = np.asarray(ids, dtype=np.int64); dnum = np.asarray(dnum, dtype=np.int64)
        k = ids * MULT + dnum
        o = np.argsort(k, kind="stable")
        self.keys = k[o]
        assert np.all(np.diff(self.keys) > 0), "duplicate (id, day) keys"
        self.cols = {c: np.asarray(v)[o] for c, v in cols.items()}

    def lookup(self, ids, dnum, col, stale_min=None):
        ids = np.asarray(ids, dtype=np.int64); dnum = np.broadcast_to(np.asarray(dnum, dtype=np.int64), ids.shape)
        q = ids * MULT + dnum
        i = np.searchsorted(self.keys, q, side="right") - 1
        ok = i >= 0
        i2 = np.where(ok, i, 0)
        same = ok & (self.keys[i2] // MULT == ids)
        rec = np.where(same, self.keys[i2] % MULT, -1)
        if stale_min is not None:
            same = same & (rec >= np.asarray(stale_min))
        v = np.where(same, self.cols[col][i2].astype(float), np.nan)
        return np.where(same, rec, -1), v


def us_index(dsf_path, delist):
    """Total-return log index (daily ret + appended delisting returns) and a price table - p4lib.us_index logic.
    dsf_path: parquet with permno, date, ret, prc, shrout, bid, ask. delist: DataFrame permno, dlstdt, dlstcd, dlret, exchcd
    (phase-4 rule: dlstcd >= 200 appended at max(dlstdt, last dsf date + 1 day); missing dlret with dlstcd 500-599 -> -0.30 NYSE/AMEX,
    -0.55 NASDAQ; other missing -> 0). Pass an empty delist frame to append nothing."""
    d = pd.read_parquet(dsf_path, columns=["permno", "date", "ret", "prc", "shrout", "bid", "ask"])
    d = d.sort_values(["permno", "date"]).reset_index(drop=True)
    d["date"] = pd.to_datetime(d.date)
    r = d.ret.to_numpy(dtype=float)
    r = np.where(np.isnan(r) | (r < -1), 0.0, r)
    r = np.where(r <= -0.9999, -0.9999, r)
    d["r"] = r
    dl = delist[(delist.dlstcd >= 200) & delist.dlstdt.notna() & delist.permno.isin(set(d.permno))].copy()
    if len(dl):
        sub = np.where((dl.dlstcd >= 500) & (dl.dlstcd <= 599), np.where(dl.exchcd == 3, -0.55, -0.30), 0.0)
        dl["r"] = dl.dlret.where(dl.dlret.notna(), sub)
        dl["r"] = dl.r.clip(lower=-0.9999)
        lastd = d.groupby("permno").date.max()
        dl["date"] = np.maximum(pd.to_datetime(dl.dlstdt).values, (lastd.reindex(dl.permno).values + np.timedelta64(1, "D")))
        dl = dl.sort_values(["permno", "date"]).drop_duplicates("permno", keep="last")
    else:
        dl = pd.DataFrame({"permno": pd.Series(dtype=int), "date": pd.Series(dtype="datetime64[ns]"), "r": pd.Series(dtype=float),
                           "dlstcd": pd.Series(dtype=float)})
    a = pd.concat([d[["permno", "date", "r"]], dl[["permno", "date", "r"]]], ignore_index=True).sort_values(["permno", "date"])
    a = a.drop_duplicates(["permno", "date"], keep="first")
    a["lv"] = np.log1p(a.r.to_numpy()).astype(float)
    a["lv"] = a.groupby("permno").lv.cumsum()
    idx = Keyed(a.permno, days(a.date), lv=a.lv.to_numpy())
    prc = d.prc.abs().where(d.prc.abs() > 0)
    px = Keyed(d.permno, days(d.date), prc=prc.to_numpy(), shrout=d.shrout.to_numpy(), bid=d.bid.to_numpy(), ask=d.ask.to_numpy(),
               cap=(prc * d.shrout * 1000.0).to_numpy())
    return idx, px, dl[["permno", "date", "r", "dlstcd"]].reset_index(drop=True)


def nw_mean(x, lags=1):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) < 3:
        return dict(n=len(x), mean=np.nan, t=np.nan, se=np.nan)
    m = sm.OLS(x, np.ones(len(x))).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return dict(n=int(len(x)), mean=float(m.params[0]), t=float(m.tvalues[0]), se=float(m.bse[0]))


def ols_slope(y, x, cov="HAC", lags=1):
    y = np.asarray(y, float); x = np.asarray(x, float)
    ok = np.isfinite(y) & np.isfinite(x)
    if ok.sum() < 4:
        return dict(n=int(ok.sum()), a=np.nan, b=np.nan, t=np.nan, se=np.nan, r2=np.nan, t_a=np.nan)
    X = sm.add_constant(x[ok])
    if cov == "HAC":
        m = sm.OLS(y[ok], X).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    else:
        m = sm.OLS(y[ok], X).fit(cov_type=cov)
    return dict(n=int(ok.sum()), a=float(m.params[0]), b=float(m.params[1]), t=float(m.tvalues[1]), se=float(m.bse[1]),
                r2=float(m.rsquared), t_a=float(m.tvalues[0]))


def verdict_4b(est, t, sign=+1):
    """PHASE4B_SPEC section 3: confirm = expected sign and |t| >= 1.96; consistent = expected sign, |t| < 1.96;
    refuted = opposite sign (|t| >= 1.96 -> strongly refuted)."""
    if not (np.isfinite(est) and np.isfinite(t)):
        return "n/a"
    if np.sign(est) == sign:
        return "확인 (confirmed)" if abs(t) >= 1.96 else "부합 (consistent, not significant)"
    return "강한 반박 (strongly refuted)" if abs(t) >= 1.96 else "반박 (refuted)"


class Results:
    def __init__(self):
        self.rows = []

    def add(self, test_id, sample, **stats):
        for k, v in stats.items():
            self.rows.append(dict(test_id=test_id, sample=sample, stat=k, value=v))

    def save(self, path):
        pd.DataFrame(self.rows).to_csv(path, index=False)
