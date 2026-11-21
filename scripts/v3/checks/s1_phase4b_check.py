# v3 reference implementation - as run on 2026-11-21; absolute paths replaced by v3paths (see scripts/v3/README.md)
"""Main-thread check of the SLOOS pre-sample confirmation (PHASE4B: 1991-2000) and the pooled record 1991-2025.

A. H1 and H2 recomputed from the agent's bank table with own quintile assignment.
B. Inputs checked independently:
   B1 loan shares recomputed from the raw Chicago Fed FR Y-9C files (still on disk) for a random sample,
   B2 holding-period returns recomputed from a different CRSP file (dsf_v2 instead of legacy dsf),
   B3 the CRE survey series (FRED DRTSCREL) downloaded here and compared with the release table.
C. Pooled view (descriptive): the pre-fixed S1 statistic and the CRE slope over 1991-2024 (+ the four 2025 periods).
Run: python s1_phase4b_check.py
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from v3paths import V3WORK, WRDS_DUMP, REPO_CACHE
import io
import urllib.request
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import statsmodels.api as sm

HERE = Path(__file__).resolve().parent
S = Path(V3WORK)
P4, P4B = S / "phase4", S / "phase4b"
DUMP = WRDS_DUMP.rstrip("/")


def nw(x, lag=1):
    x = np.asarray(x, float)
    f = sm.OLS(x, np.ones(len(x))).fit(cov_type="HAC", cov_kwds={"maxlags": lag})
    return f.params[0], f.tvalues[0]


def slope(y, x, lag=1):
    f = sm.OLS(np.asarray(y, float), sm.add_constant(np.asarray(x, float))).fit(cov_type="HAC", cov_kwds={"maxlags": lag})
    return f.params[1], f.tvalues[1], f.params[0], f.tvalues[0]


def quintile_ls(df, col, rcol="R"):
    out = {}
    for p, g in df.groupby("period"):
        g = g.dropna(subset=[col, rcol]).sort_values([col, "permno"], kind="mergesort")
        n = len(g)
        q = np.ceil(5 * (np.arange(n) + 1) / n).astype(int)
        out[p] = (g[rcol].values[q == 1].mean() - g[rcol].values[q == 5].mean()) * 100
    return pd.Series(out).sort_index()


# ---------------- A ----------------
b = pd.read_parquet(P4B / "out" / "h1h2_1990s_bank_table.parquet")
print("[A] 1990s bank table:", b.shape, "| columns:", [c for c in b.columns][:40])
scr = [c for c in b.columns if c.lower() == "screen"][0]
m = b[b[scr].astype(bool)].copy()
cre_col = [c for c in b.columns if c.lower() in ("share_cre", "sh_cre", "cre_share")][0]
per = pd.read_csv(P4B / "out" / "h1h2_1990s_periods.csv")
print("    period file columns:", list(per.columns))
h1 = quintile_ls(m, "BT")
h2 = quintile_ls(m, cre_col)
ncre = per.set_index("period").N_CRE.reindex(h2.index)
m1, t1 = nw(h1.values)
s2, ts2, a2, ta2 = slope(h2.values, ncre.values / 10)
print(f"    H1 (BT quintile long-short): n {len(h1)}, mean {m1:+.3f}%, t {t1:+.2f}  | agent series max abs diff {np.abs(h1.values - per.set_index('period').LS_BT.reindex(h1.index).values).max():.2e}")
print(f"    H2 (low-CRE minus high-CRE on released CRE tightening): slope {s2:+.3f}% per 10pp, t {ts2:+.2f}; intercept {a2:+.3f} (t {ta2:+.2f}) "
      f"| agent series max abs diff {np.abs(h2.values - per.set_index('period').LS_CRE.reindex(h2.index).values).max():.2e}")
yr = m.groupby("period").release_date.first().pipe(pd.to_datetime).dt.year if "release_date" in m.columns else None
if yr is not None:
    for lab, sel in [("without releases in 1991", yr != 1991), ("without 1991-1992", yr > 1992), ("1991-1992 only", yr <= 1992)]:
        idx = yr.index[sel.values]
        if len(idx) > 3:
            s_, t_, _, _ = slope(h2.reindex(idx).values, ncre.reindex(idx).values / 10)
            print(f"      H2 {lab:26s}: n {len(idx):2d}, slope {s_:+.3f}, t {t_:+.2f}")

# ---------------- B1: shares from the raw Chicago Fed files ----------------
raw_dir = P4B / "tmp" / "raw"
files = sorted(raw_dir.glob("bhcf*.csv"))
print(f"[B1] raw Chicago Fed files on disk: {len(files)}")
if files:
    ycol = [c for c in b.columns if c.lower() in ("y9c_date", "report_date")][0]
    keys = b[["rssd9001", ycol]].drop_duplicates().sample(300, random_state=3)
    keys["rssd9001"] = keys.rssd9001.astype(int)
    keys["ymd"] = pd.to_datetime(keys[ycol]).dt.strftime("%y%m")
    ok = tot = 0
    for ymd, g in keys.groupby("ymd"):
        f = raw_dir / f"bhcf{ymd}.csv"
        if not f.exists():
            continue
        want = ["RSSD9001", "BHCK1763", "BHCK1764", "BHDM1415", "BHDM1460", "BHDM1480", "BHDM1797", "BHDM1798", "BHDM5367", "BHDM5368", "BHCK2008", "BHCK2011", "BHCK1975"]
        hdr = pd.read_csv(f, nrows=0, encoding="latin-1").columns
        use = [c for c in hdr if c.upper() in want]
        d = pd.read_csv(f, usecols=use, low_memory=False, encoding="latin-1")
        d.columns = [c.upper() for c in d.columns]
        d = d[d.RSSD9001.isin(g.rssd9001)]
        z = lambda c: pd.to_numeric(d[c], errors="coerce").fillna(0) if c in d else 0
        ci = z("BHCK1763") + z("BHCK1764")
        cre = z("BHDM1415") + z("BHDM1460") + z("BHDM1480")
        rre = z("BHDM1797") + (z("BHDM5367") + z("BHDM5368") if "BHDM5367" in d else z("BHDM1798"))
        cons = (z("BHCK2008") + z("BHCK2011")) if "BHCK2008" in d else z("BHCK1975")
        mine = pd.DataFrame({"rssd9001": d.RSSD9001.astype(int).values, "m_cre": (cre / (ci + cre + rre + cons)).values})
        ref = b[(b.rssd9001.astype(int).isin(g.rssd9001)) & (pd.to_datetime(b[ycol]).dt.strftime("%y%m") == ymd)].drop_duplicates("rssd9001")[["rssd9001", cre_col]]
        ref["rssd9001"] = ref.rssd9001.astype(int)
        c = mine.merge(ref, on="rssd9001")
        ok += int((np.abs(c.m_cre - c[cre_col]) < 1e-6).sum())
        tot += len(c)
    print(f"     CRE share recomputed from the raw files: {ok}/{tot} identical (|diff| < 1e-6)")

# ---------------- B2: returns from dsf_v2 ----------------
con = duckdb.connect()
con.execute("SET memory_limit='6GB'")
t0c = [c for c in b.columns if c.lower() in ("t0", "entry")][0]
exc = [c for c in b.columns if c.lower() in ("exit",)][0]
smp = m[m.R.notna()].sample(200, random_state=5)[["permno", t0c, exc, "R"]].copy()
smp["permno"] = smp.permno.astype(int)
smp["a"] = pd.to_datetime(smp[t0c]).dt.strftime("%Y-%m-%d")
smp["z"] = pd.to_datetime(smp[exc]).dt.strftime("%Y-%m-%d")
con.register("s", smp[["permno", "a", "z"]])
r = con.execute(f"""SELECT s.permno, s.a, s.z, exp(sum(ln(1 + TRY_CAST(d.dlyret AS DOUBLE)))) - 1 AS R2, count(*) n
                    FROM read_csv('{DUMP}/crsp_a_stock.dsf_v2.csv.gz', all_varchar=true, header=true, ignore_errors=true) d
                    JOIN s ON TRY_CAST(d.permno AS INTEGER) = s.permno AND d.dlycaldt > s.a AND d.dlycaldt <= s.z
                    WHERE d.dlycaldt >= '1990-06-01' AND d.dlycaldt <= '2000-12-31' GROUP BY 1, 2, 3""").df()
c = smp.merge(r, on=["permno", "a", "z"], how="left")
dif = (c.R - c.R2).abs()
print(f"[B2] returns recomputed from dsf_v2: matched {int(c.R2.notna().sum())}/200, |diff| < 1e-4 in {np.mean(dif[c.R2.notna()] < 1e-4):.3f}, max diff {dif.max():.5f}")

# ---------------- B3: CRE series from FRED ----------------
try:
    req = urllib.request.Request("https://fred.stlouisfed.org/graph/fredgraph.csv?id=DRTSCREL", headers={"User-Agent": "research-reverify/1.0"})
    fr = pd.read_csv(io.BytesIO(urllib.request.urlopen(req, timeout=60).read()))
    fr.columns = ["fred_date", "v"]
    fr["fred_date"] = pd.to_datetime(fr.fred_date)
    N = pd.read_csv(P4 / "out" / "s1_N_by_release.csv", parse_dates=["fred_date"])
    cmpn = N.merge(fr, on="fred_date")
    cmpn = cmpn[(cmpn.fred_date >= "1990-07-01") & (cmpn.fred_date <= "2013-07-01")]
    print(f"[B3] FRED DRTSCREL vs release table N_CRE: quarters {len(cmpn)}, max abs diff {np.abs(cmpn.N_CRE - pd.to_numeric(cmpn.v, errors='coerce')).max():.4f}")
except Exception as e:
    print("[B3] FRED download failed:", repr(e)[:150])

# ---------------- C: pooled 1991-2024 (+2025) ----------------
p4 = pd.read_csv(P4 / "out" / "s1_ls_periods.csv")
b4 = pd.read_parquet(P4 / "out" / "s1_bank_table.parquet")
m4 = b4[b4.screen & b4.R.notna()].copy()
cre4 = quintile_ls(m4, "share_CRE")
N4 = pd.read_csv(P4 / "out" / "s1_N_by_release.csv", parse_dates=["release_date"]).dropna(subset=["release_date"]).set_index("release_date").N_CRE
rel4 = m4.groupby("period").release_date.first()
ncre4 = rel4.map(N4).reindex(cre4.index)
ls_all = np.concatenate([h1.values, p4.LS.values])
print(f"[C] pooled, pre-fixed S1 statistic (BT long-short): 1991-2024 n {len(ls_all)}, mean {ls_all.mean():+.3f}% per period, NW(1) t {nw(ls_all)[1]:+.2f}, positive in {np.mean(ls_all > 0):.2f} of periods")
y_all = np.concatenate([h2.values, cre4.values])
x_all = np.concatenate([ncre.values, ncre4.values]) / 10
s_, t_, a_, ta_ = slope(y_all, x_all)
print(f"    pooled CRE slope 1991-2024: n {len(y_all)}, slope {s_:+.3f}% per 10pp (t {t_:+.2f}), intercept {a_:+.3f} (t {ta_:+.2f})")
yrs_all = np.concatenate([yr.reindex(h2.index).values if yr is not None else np.zeros(len(h2)), pd.to_datetime(rel4.reindex(cre4.index)).dt.year.values])
calm = ~np.isin(yrs_all, [1991, 1992, 2008, 2009])
s_, t_, _, _ = slope(y_all[calm], x_all[calm])
print(f"    pooled CRE slope without 1991-1992 and 2008-2009: n {int(calm.sum())}, slope {s_:+.3f} (t {t_:+.2f})")
try:
    p25 = pd.read_csv(P4B / "out" / "post2025_periods.csv")
    print("    2025 record:", p25.to_string(index=False)[:900])
except Exception as e:
    print("    (2025 record file not read:", repr(e)[:100], ")")
