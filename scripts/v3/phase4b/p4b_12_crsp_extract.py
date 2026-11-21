# v3 reference implementation - as run on 2026-11-21; absolute paths replaced by v3paths (see scripts/v3/README.md)
"""Phase 4B / step 12 - raw CRSP extraction from the read-only WRDS dump (row counts / coverage only; no return statistics).

  cache/crsp_bank_dsf_1990s.parquet   legacy crsp_a_stock.dsf, permnos of the phase-4 permno set, 1990-01-01..2000-12-31
  cache/crsp_bank_dsfv2_2024_25.parquet  crsp_a_stock.dsf_v2 (CIZ), same permnos, 2024-06-01..2025-12-31
  cache/dsi_1989_2025.parquet         crsp_a_stock.dsi (date, vwretd) 1989-01-01.. (no upper cap)
  cache/stkdelists.parquet            crsp_a_stock.stkdelists (CIZ delisting table), all rows of the permno set
  cache/stocknames_v2.parquet         crsp_a_stock.stocknames_v2 rows of the permno set (used only for a 2025 name-change check)
Permno set = phase-4 rule (phase4/scripts/p4_10_extract.py step 3): permnos of any linked permco U bank SIC 6020-6029 / 6710-6712.
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
P4C = W + "phase4/cache/"
P4B = W + "phase4b/"
C = P4B + "cache/"
t = time.time()
log = lambda *a: print(f"[{time.time() - t:6.0f}s]", *a, flush=True)
con = duckdb.connect()
con.execute("SET threads=4"); con.execute("SET memory_limit='7GB'"); con.execute(f"SET temp_directory='{P4B}tmp'")
con.execute("SET preserve_insertion_order=false")

lk = pd.read_parquet(P4C + "link.parquet")
dn = pd.read_parquet(P4C + "dsenames.parquet")
sic = dn.siccd
P = sorted(set(dn.loc[sic.between(6020, 6029) | sic.between(6710, 6712), "permno"]) | set(dn.loc[dn.permco.isin(set(lk.permco)), "permno"]))
log("permno set", len(P))
con.register("pp", pd.DataFrame({"permno": np.array(P, dtype=np.int32)}))

# dsi (calendar + market), no upper cap
con.execute(f"""COPY (SELECT CAST(date AS DATE) date, TRY_CAST(vwretd AS DOUBLE) vwretd FROM read_csv('{DUMP}crsp_a_stock.dsi.csv.gz',
    header=true, all_varchar=true) WHERE CAST(date AS DATE) >= DATE '1989-01-01' AND TRY_CAST(vwretd AS DOUBLE) IS NOT NULL ORDER BY 1)
    TO '{C}dsi_1989_2025.parquet' (FORMAT parquet)""")
log("dsi", con.execute(f"SELECT count(*), min(date), max(date) FROM '{C}dsi_1989_2025.parquet'").fetchone())

# CIZ delisting table and names (small)
x = con.execute(f"SELECT * FROM read_csv('{DUMP}crsp_a_stock.stkdelists.csv.gz', header=true, all_varchar=true) LIMIT 2").fetchdf()
log("stkdelists columns", list(x.columns))
con.execute(f"""COPY (SELECT s.* FROM read_csv('{DUMP}crsp_a_stock.stkdelists.csv.gz', header=true, all_varchar=true) s
    JOIN pp ON CAST(s.permno AS INTEGER) = pp.permno) TO '{C}stkdelists.parquet' (FORMAT parquet)""")
log("stkdelists rows (permno set)", con.execute(f"SELECT count(*) FROM '{C}stkdelists.parquet'").fetchone())
con.execute(f"""COPY (SELECT s.* FROM read_csv('{DUMP}crsp_a_stock.stocknames_v2.csv.gz', header=true, all_varchar=true) s
    JOIN pp ON CAST(s.permno AS INTEGER) = pp.permno) TO '{C}stocknames_v2.parquet' (FORMAT parquet)""")
log("stocknames_v2 rows (permno set), max nameenddt", con.execute(f"SELECT count(*), max(nameenddt) FROM '{C}stocknames_v2.parquet'").fetchone())

# legacy dsf 1990s
con.execute(f"""COPY (
    SELECT CAST(s.permno AS INTEGER) permno, CAST(s.date AS DATE) date, TRY_CAST(s.ret AS DOUBLE) ret,
           TRY_CAST(s.prc AS DOUBLE) prc, TRY_CAST(s.shrout AS DOUBLE) shrout,
           TRY_CAST(s.bid AS DOUBLE) bid, TRY_CAST(s.ask AS DOUBLE) ask, TRY_CAST(s.vol AS DOUBLE) vol
    FROM read_csv('{DUMP}crsp_a_stock.dsf.csv.gz', header=true, all_varchar=true) s
    JOIN pp ON CAST(s.permno AS INTEGER) = pp.permno
    WHERE CAST(s.date AS DATE) BETWEEN DATE '1990-01-01' AND DATE '2000-12-31') TO '{C}crsp_bank_dsf_1990s.parquet' (FORMAT parquet, COMPRESSION zstd)""")
r = con.execute(f"SELECT count(*), count(distinct permno), min(date), max(date), avg(CASE WHEN ret IS NULL THEN 1 ELSE 0 END), "
                f"avg(CASE WHEN prc IS NULL THEN 1 ELSE 0 END) FROM '{C}crsp_bank_dsf_1990s.parquet'").fetchone()
log("legacy dsf 1990s rows/permnos/min/max/share ret null/share prc null", r)

# dsf_v2 2024-06..2025-12
con.execute(f"""COPY (
    SELECT CAST(s.permno AS INTEGER) permno, CAST(s.dlycaldt AS DATE) date, TRY_CAST(s.dlyret AS DOUBLE) ret,
           TRY_CAST(s.dlyprc AS DOUBLE) prc, TRY_CAST(s.shrout AS DOUBLE) shrout, TRY_CAST(s.dlycap AS DOUBLE) dlycap,
           TRY_CAST(s.dlybid AS DOUBLE) bid, TRY_CAST(s.dlyask AS DOUBLE) ask, s.dlydelflg, s.dlyretmissflg, s.dlyprcflg,
           s.sharetype, s.securitytype, s.securitysubtype, s.usincflg, s.issuertype, s.primaryexch, s.conditionaltype,
           s.tradingstatusflg, TRY_CAST(s.siccd AS INTEGER) siccd, CAST(s.permco AS INTEGER) permco
    FROM read_csv('{DUMP}crsp_a_stock.dsf_v2.csv.gz', header=true, all_varchar=true) s
    JOIN pp ON CAST(s.permno AS INTEGER) = pp.permno
    WHERE CAST(s.dlycaldt AS DATE) BETWEEN DATE '2024-06-01' AND DATE '2025-12-31') TO '{C}crsp_bank_dsfv2_2024_25.parquet' (FORMAT parquet, COMPRESSION zstd)""")
r = con.execute(f"SELECT count(*), count(distinct permno), min(date), max(date), avg(CASE WHEN ret IS NULL THEN 1 ELSE 0 END) "
                f"FROM '{C}crsp_bank_dsfv2_2024_25.parquet'").fetchone()
log("dsf_v2 2024-06..2025-12 rows/permnos/min/max/share ret null", r)
log("dsf_v2 flags:", con.execute(f"SELECT dlydelflg, dlyretmissflg, count(*) FROM '{C}crsp_bank_dsfv2_2024_25.parquet' GROUP BY 1, 2 ORDER BY 3 DESC").fetchall())
log("dsf_v2 prc<=0 rows:", con.execute(f"SELECT count(*) FROM '{C}crsp_bank_dsfv2_2024_25.parquet' WHERE prc <= 0").fetchone(),
    "| dlycap vs prc*shrout max rel diff:", con.execute(f"SELECT max(abs(dlycap - prc*shrout)/nullif(dlycap,0)) FROM '{C}crsp_bank_dsfv2_2024_25.parquet' WHERE dlycap > 0").fetchone())
log("done")
