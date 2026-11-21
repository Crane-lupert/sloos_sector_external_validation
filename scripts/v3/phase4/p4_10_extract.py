# v3 reference implementation - as run on 2026-11-21; absolute paths replaced by v3paths (see scripts/v3/README.md)
"""Phase 4 / step 10 - raw-data extraction from the read-only WRDS dump into phase4/cache (no outcome statistics).

  cache/link.parquet              bank_all.wrds_bank_crsp_link (typed)
  cache/dsenames.parquet          crsp_a_stock.dsenames (typed, all rows)
  cache/crsp_bank_dsf.parquet     legacy crsp_a_stock.dsf for permnos of linked permcos U bank-SIC permnos, 1995-01-01..2024-12-31
  cache/delist.parquet            crsp_a_stock.dsedelist (+ last exchcd)
  cache/dsi.parquet               crsp_a_stock.dsi vwretd / ewretd 1989..2024
  cache/ff5umd_monthly.parquet    ff_all.fivefactors_monthly (mktrf smb hml rmw cma rf umd)
  cache/ff5umd_daily.parquet      ff_all.fivefactors_daily
  cache/eu_company.parquet        comp_global_daily.g_company (gvkey, ggroup, gsector, loc) for EZ / UK universe gvkeys
  cache/eu_cap_formation.parquet  g_secd.stoxx600_2003plus prccd / cshoc / curcdd in the 10 calendar days up to each S3 formation date
  cache/eu_fx_formation.parquet   g_exrt_dly (GBP-based rates) on the same dates
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from v3paths import V3WORK, WRDS_DUMP, REPO_CACHE
import time
import duckdb
import numpy as np
import pandas as pd

DUMP = WRDS_DUMP + ""
W = V3WORK + ""
P4 = W + "phase4/"
C = P4 + "cache/"
S3C = REPO_CACHE
t = time.time()
log = lambda *a: print(f"[{time.time() - t:6.0f}s]", *a, flush=True)
con = duckdb.connect()
con.execute("SET threads=4"); con.execute("SET memory_limit='7GB'"); con.execute(f"SET temp_directory='{P4}tmp'")
con.execute("SET preserve_insertion_order=false")

# 1 link
lk = con.execute(f"""SELECT CAST(rssd9001 AS BIGINT) rssd9001, CAST(permco AS INTEGER) permco, name, inst_type,
    CAST(dt_start AS DATE) dt_start, CAST(dt_end AS DATE) dt_end
    FROM read_csv('{DUMP}bank_all.wrds_bank_crsp_link.csv.gz', header=true, all_varchar=true)""").fetchdf()
lk.to_parquet(C + "link.parquet", index=False)
log("link rows", len(lk))

# 2 dsenames
dn = con.execute(f"""SELECT CAST(permno AS INTEGER) permno, CAST(permco AS INTEGER) permco, CAST(namedt AS DATE) namedt,
    CAST(nameendt AS DATE) nameendt, TRY_CAST(shrcd AS INTEGER) shrcd, TRY_CAST(exchcd AS INTEGER) exchcd,
    TRY_CAST(siccd AS INTEGER) siccd, ncusip, ticker, comnam
    FROM read_csv('{DUMP}crsp_a_stock.dsenames.csv.gz', header=true, all_varchar=true)""").fetchdf()
dn.to_parquet(C + "dsenames.parquet", index=False)
log("dsenames rows", len(dn), "nameendt max", dn.nameendt.max())

# 3 permno set
sic = dn.siccd
p_sic = set(dn.loc[sic.between(6020, 6029) | sic.between(6710, 6712), "permno"])
p_lnk = set(dn.loc[dn.permco.isin(set(lk.permco)), "permno"])
P = sorted(p_sic | p_lnk)
log("permnos: bank SIC", len(p_sic), "linked permcos", len(p_lnk), "union", len(P))
con.register("pp", pd.DataFrame({"permno": np.array(P, dtype=np.int32)}))

# 4 legacy dsf
con.execute(f"""COPY (
    SELECT CAST(s.permno AS INTEGER) permno, CAST(s.date AS DATE) date, TRY_CAST(s.ret AS DOUBLE) ret,
           TRY_CAST(s.prc AS DOUBLE) prc, TRY_CAST(s.shrout AS DOUBLE) shrout,
           TRY_CAST(s.bid AS DOUBLE) bid, TRY_CAST(s.ask AS DOUBLE) ask, TRY_CAST(s.vol AS DOUBLE) vol
    FROM read_csv('{DUMP}crsp_a_stock.dsf.csv.gz', header=true, all_varchar=true) s
    JOIN pp ON CAST(s.permno AS INTEGER) = pp.permno
    WHERE CAST(s.date AS DATE) >= DATE '1995-01-01') TO '{C}crsp_bank_dsf.parquet' (FORMAT parquet, COMPRESSION zstd)""")
r = con.execute(f"SELECT count(*), count(distinct permno), min(date), max(date), avg(CASE WHEN ret IS NULL THEN 1 ELSE 0 END), "
                f"avg(CASE WHEN bid>0 AND ask>=bid THEN 1 ELSE 0 END) FROM '{C}crsp_bank_dsf.parquet'").fetchone()
log("bank dsf rows/permnos/min/max/share ret null/share valid quote", r)

# 5 delisting
dl = con.execute(f"""SELECT CAST(permno AS INTEGER) permno, CAST(dlstdt AS DATE) dlstdt, TRY_CAST(dlstcd AS INTEGER) dlstcd,
    TRY_CAST(dlret AS DOUBLE) dlret FROM read_csv('{DUMP}crsp_a_stock.dsedelist.csv.gz', header=true, all_varchar=true)""").fetchdf()
last_ex = dn.sort_values("namedt").drop_duplicates("permno", keep="last")[["permno", "exchcd"]]
dl = dl.merge(last_ex, on="permno", how="left")
dl.to_parquet(C + "delist.parquet", index=False)
log("delist rows", len(dl))

# 6 dsi
dsi = con.execute(f"""SELECT CAST(date AS DATE) date, TRY_CAST(vwretd AS DOUBLE) vwretd, TRY_CAST(ewretd AS DOUBLE) ewretd
    FROM read_csv('{DUMP}crsp_a_stock.dsi.csv.gz', header=true, all_varchar=true)
    WHERE CAST(date AS DATE) BETWEEN DATE '1989-01-01' AND DATE '2024-12-31' AND TRY_CAST(vwretd AS DOUBLE) IS NOT NULL ORDER BY 1""").fetchdf()
dsi.to_parquet(C + "dsi.parquet", index=False)
log("dsi rows", len(dsi), dsi.date.min(), dsi.date.max())

# 7 FF
for nm, f in [("ff5umd_monthly", "ff_all.fivefactors_monthly.csv.gz"), ("ff5umd_daily", "ff_all.fivefactors_daily.csv.gz")]:
    x = con.execute(f"SELECT * FROM read_csv('{DUMP}{f}', header=true, all_varchar=true)").fetchdf()
    keep = [c for c in ["date", "dateff", "mktrf", "smb", "hml", "rmw", "cma", "rf", "umd"] if c in x.columns]
    x = x[keep].copy()
    for c in ["mktrf", "smb", "hml", "rmw", "cma", "rf", "umd"]:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    x["date"] = pd.to_datetime(x.date)
    x.to_parquet(C + f"{nm}.parquet", index=False)
    log(nm, len(x), x.date.min(), x.date.max(), "umd null", int(x.umd.isna().sum()))

# 8 EU company GICS
uz = pd.read_parquet(S3C + "stoxx600_eurozone_universe_2026-05-06.parquet")
uk = pd.read_parquet(S3C + "stoxx600_uk_universe_2026-05-06.parquet")
gv = pd.DataFrame({"gvkey": sorted(set(uz.gvkey.astype(str)) | set(uk.gvkey.astype(str)))})
con.register("gv", gv)
gc = con.execute(f"""SELECT g.gvkey, g.conml, g.ggroup, g.gsector, g.gind, g.loc FROM read_csv('{DUMP}comp_global_daily.g_company.csv.gz',
    header=true, all_varchar=true) g JOIN gv USING (gvkey)""").fetchdf()
gc.to_parquet(C + "eu_company.parquet", index=False)
log("eu company rows", len(gc), "ggroup 4010:", int((gc.ggroup == "4010").sum()))

# 9 EU caps / FX near the S3 formation dates (first regional trading day strictly after each release date)
fd = []
for reg, rel in [("EZ", "release_dates_EZ_BLS.csv"), ("UK", "release_dates_UK_CCS.csv")]:
    cal = pd.DatetimeIndex(pd.read_csv(W + f"phase3/out/cal_{reg}.csv", parse_dates=["date"]).date)
    rr = pd.read_csv(W + f"out/{rel}", parse_dates=["release_date"]).dropna(subset=["release_date"])
    for R in rr.release_date:
        i = int(np.searchsorted(cal.values, np.datetime64(R), side="right"))
        if i < len(cal):
            fd.append(cal[i])
fd = sorted(set(fd))
win = pd.DataFrame({"hi": pd.to_datetime(fd)}); win["lo"] = win.hi - pd.Timedelta(days=10)
con.register("win", win)
con.execute(f"""COPY (SELECT DISTINCT s.gvkey, s.iid, CAST(s.datadate AS DATE) datadate, TRY_CAST(s.prccd AS DOUBLE) prccd,
        TRY_CAST(s.cshoc AS DOUBLE) cshoc, s.curcdd
    FROM read_csv('{DUMP}comp_global_daily.g_secd.stoxx600_2003plus.csv.gz', header=true, all_varchar=true) s
    JOIN win ON CAST(s.datadate AS DATE) BETWEEN CAST(win.lo AS DATE) AND CAST(win.hi AS DATE)) TO '{C}eu_cap_formation.parquet' (FORMAT parquet)""")
log("eu cap rows", con.execute(f"SELECT count(*), count(cshoc) FROM '{C}eu_cap_formation.parquet'").fetchone(), "formation dates", len(fd))
con.execute(f"""COPY (SELECT CAST(datadate AS DATE) datadate, fromcurd, tocurd, TRY_CAST(exratd AS DOUBLE) exratd
    FROM read_csv('{DUMP}comp_global_daily.g_exrt_dly.csv.gz', header=true, all_varchar=true) x
    JOIN win ON CAST(x.datadate AS DATE) BETWEEN CAST(win.lo AS DATE) AND CAST(win.hi AS DATE)) TO '{C}eu_fx_formation.parquet' (FORMAT parquet)""")
log("eu fx rows", con.execute(f"SELECT count(*) FROM '{C}eu_fx_formation.parquet'").fetchone())
log("done")
