# v3 reference implementation - as run on 2026-11-21; absolute paths replaced by v3paths (see scripts/v3/README.md)
"""Phase 4 (S1/S2/S3, SLOOS) shared library. Implements FROZEN_PARAMS.json; reads phase4/cache and 1-3 phase outputs read-only."""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from v3paths import V3WORK, WRDS_DUMP, REPO_CACHE
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm
import duckdb

W = V3WORK + ""
P4 = W + "phase4/"
C = P4 + "cache/"
O = P4 + "out/"
O1 = W + "out/"
O3 = W + "phase3/out/"
S3C = REPO_CACHE
MULT = 100000
DAY0 = np.datetime64("1970-01-01", "D")
US_END = pd.Timestamp("2024-12-31")
EURO = {"AUT", "BEL", "CYP", "DEU", "ESP", "EST", "FIN", "FRA", "GRC", "HRV", "IRL", "ITA", "LTU", "LUX", "LVA", "MLT", "NLD",
        "PRT", "SVK", "SVN"}
CATS = ["CI", "CRE", "RRE", "CC", "OC"]


def days(x):
    return (pd.DatetimeIndex(pd.to_datetime(x)).values.astype("datetime64[D]") - DAY0).astype(np.int64)


def jdump(obj, path):
    json.dump(obj, open(path, "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))


def connect():
    con = duckdb.connect()
    con.execute("SET threads=4"); con.execute("SET memory_limit='7GB'"); con.execute(f"SET temp_directory='{P4}tmp'")
    return con


# ------------------------------------------------------------------ calendars
def us_calendar():
    d = pd.read_parquet(C + "dsi.parquet")
    return pd.DatetimeIndex(d.date)


def eu_calendar(reg):
    return pd.DatetimeIndex(pd.read_csv(O3 + f"cal_{reg}.csv", parse_dates=["date"]).date)


def first_after(cal, d):
    """index of first calendar day strictly after d"""
    return int(np.searchsorted(cal.values, np.datetime64(pd.Timestamp(d)), side="right"))


def first_on_after(cal, d):
    return int(np.searchsorted(cal.values, np.datetime64(pd.Timestamp(d)), side="left"))


def last_on_before(cal, d):
    return int(np.searchsorted(cal.values, np.datetime64(pd.Timestamp(d)), side="right")) - 1


# ------------------------------------------------------------------ keyed arrays with "last record <= day" lookup
class Keyed:
    def __init__(self, ids, dnum, **cols):
        ids = np.asarray(ids, dtype=np.int64); dnum = np.asarray(dnum, dtype=np.int64)
        k = ids * MULT + dnum
        o = np.argsort(k, kind="stable")
        self.keys = k[o]
        assert np.all(np.diff(self.keys) > 0), "duplicate (id, day) keys"
        self.cols = {c: np.asarray(v)[o] for c, v in cols.items()}

    def lookup(self, ids, dnum, col, stale_min=None):
        """value of `col` at the last record <= dnum for each id; rec day; NaN if none or older than stale_min (array or scalar)."""
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

    def has_exact(self, ids, dnum):
        ids = np.asarray(ids, dtype=np.int64); dnum = np.broadcast_to(np.asarray(dnum, dtype=np.int64), ids.shape)
        q = ids * MULT + dnum
        i = np.searchsorted(self.keys, q, side="left")
        i2 = np.minimum(i, len(self.keys) - 1)
        return self.keys[i2] == q


def us_index(permnos=None):
    """Total-return log index (dsf ret + appended delisting returns), and a price table (dsf rows only).
    Returns (idx: Keyed with col lv, px: Keyed with prc, shrout, bid, ask, cap)."""
    d = pd.read_parquet(C + "crsp_bank_dsf.parquet")
    if permnos is not None:
        d = d[d.permno.isin(permnos)]
    d = d.sort_values(["permno", "date"]).reset_index(drop=True)
    d["date"] = pd.to_datetime(d.date)
    r = d.ret.to_numpy(dtype=float)
    r = np.where(np.isnan(r) | (r < -1), 0.0, r)
    r = np.where(r <= -0.9999, -0.9999, r)
    d["r"] = r
    dl = pd.read_parquet(C + "delist.parquet")
    dl = dl[(dl.dlstcd >= 200) & dl.dlstdt.notna() & dl.permno.isin(set(d.permno))].copy()
    sub = np.where((dl.dlstcd >= 500) & (dl.dlstcd <= 599), np.where(dl.exchcd == 3, -0.55, -0.30), 0.0)
    dl["r"] = dl.dlret.where(dl.dlret.notna(), sub)
    dl["r"] = dl.r.clip(lower=-0.9999)
    lastd = d.groupby("permno").date.max()
    dl["date"] = np.maximum(pd.to_datetime(dl.dlstdt).values, (lastd.reindex(dl.permno).values + np.timedelta64(1, "D")))
    dl = dl.sort_values(["permno", "date"]).drop_duplicates("permno", keep="last")
    a = pd.concat([d[["permno", "date", "r"]], dl[["permno", "date", "r"]]], ignore_index=True).sort_values(["permno", "date"])
    a = a.drop_duplicates(["permno", "date"], keep="first")
    a["lv"] = np.log1p(a.r.to_numpy()).astype(float)
    a["lv"] = a.groupby("permno").lv.cumsum()
    idx = Keyed(a.permno, days(a.date), lv=a.lv.to_numpy())
    prc = d.prc.abs().where(d.prc.abs() > 0)
    px = Keyed(d.permno, days(d.date), prc=prc.to_numpy(), shrout=d.shrout.to_numpy(), bid=d.bid.to_numpy(), ask=d.ask.to_numpy(),
               cap=(prc * d.shrout * 1000.0).to_numpy())
    return idx, px, dl[["permno", "date", "r", "dlstcd"]].reset_index(drop=True)


def half_spread(bid, ask):
    bid = np.asarray(bid, float); ask = np.asarray(ask, float)
    with np.errstate(invalid="ignore", divide="ignore"):
        mid = (ask + bid) / 2
        rs = (ask - bid) / mid
        ok = (bid > 0) & (ask >= bid) & (rs < 0.5)
    return np.where(ok, rs / 2, np.nan)


def fill_hs(hs, default=0.0025):
    hs = np.asarray(hs, float)
    if np.all(np.isnan(hs)):
        return np.full(hs.shape, default)
    return np.where(np.isnan(hs), np.nanmedian(hs), hs)


# ------------------------------------------------------------------ inference
def nw_mean(x, lags=1):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) < 3:
        return dict(n=len(x), mean=np.nan, t=np.nan, se=np.nan)
    m = sm.OLS(x, np.ones(len(x))).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return dict(n=int(len(x)), mean=float(m.params[0]), t=float(m.tvalues[0]), se=float(m.bse[0]))


def ols_slope(y, x, cov="HC0", lags=None):
    y = np.asarray(y, float); x = np.asarray(x, float)
    ok = np.isfinite(y) & np.isfinite(x)
    X = sm.add_constant(x[ok])
    if cov == "HAC":
        m = sm.OLS(y[ok], X).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    else:
        m = sm.OLS(y[ok], X).fit(cov_type=cov)
    return dict(n=int(ok.sum()), a=float(m.params[0]), b=float(m.params[1]), t=float(m.tvalues[1]), se=float(m.bse[1]),
                r2=float(m.rsquared))


def verdict(t, halves, sign=+1, crit=2.24):
    """PHASE4 section 3: holds / weak / not holding (expected sign `sign`). halves: list of half means (or slopes)."""
    ts = sign * t
    same = all(np.sign(h) == sign for h in halves if np.isfinite(h))
    if ts >= crit and same:
        return "holds"
    if (ts >= 1.96 and ts < crit) or (ts >= crit and not same):
        return "weak"
    if -ts >= 1.96:
        return "not holding (significant opposite sign, reported separately)"
    return "not holding"


class Results:
    def __init__(self):
        self.rows = []

    def add(self, test_id, sample, **stats):
        for k, v in stats.items():
            self.rows.append(dict(test_id=test_id, sample=sample, stat=k, value=v))

    def save(self, path):
        pd.DataFrame(self.rows).to_csv(path, index=False)
