# v3 reference implementation - as run on 2026-11-21; absolute paths replaced by v3paths (see scripts/v3/README.md)
"""Phase 4 / step 03 - Step 0 item checks (no returns): duplicates, C&I split vs total, 2000 consumer items,
CRE overlap 2007, reg_vars for pre-2001 credit-card item, share-sum identity vs reported totals."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from v3paths import V3WORK, WRDS_DUMP, REPO_CACHE
import duckdb
import numpy as np
import pandas as pd

DUMP = WRDS_DUMP + ""
P4 = V3WORK + "phase4/"
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 120); pd.set_option("display.max_rows", 200)
con = duckdb.connect(); con.execute("SET threads=4"); con.execute("SET memory_limit='6GB'"); con.execute(f"SET temp_directory='{P4}tmp'")

rv = con.execute(f"SELECT * FROM read_csv('{DUMP}bank_all.wrds_bank_reg_vars.csv.gz', header=true, all_varchar=true)").fetchdf()
rv["vn"] = rv.variable_name.str.lower()
print(rv[rv.vn.isin(["bhck2008", "bhck2011", "bhckb538", "bhckb539", "bhck1766", "bhck2107", "bhck1545", "bhck1564", "bhck2165",
                     "bhck1590", "bhck1288", "bhck2081", "bhckj454", "bhckj451", "bhck1292", "bhck1296", "bhckf162", "bhckf163",
                     "bhck1797", "bhck5367", "bhck5368", "bhck1460", "bhck1415", "bhck1480", "bhck1420"])]
      [["vn", "item_name", "start_date", "end_date", "table"]].sort_values("vn").to_string(index=False))
f1 = f"{DUMP}bank_all.wrds_holding_bhck_1.csv.gz"
cols1 = [c.lower() for c in con.execute(f"SELECT * FROM read_csv('{f1}', header=true, all_varchar=true) LIMIT 1").fetchdf().columns]
for c in ["bhck2008", "bhck2107", "bhckf162", "bhckf163", "bhck1545", "bhck1564", "bhckj454", "bhckj451", "bhck1292", "bhck1296",
          "bhck1797", "bhck5367", "bhck5368", "bhck1460", "bhck1415", "bhck1480", "bhck1420"]:
    print(c, "in bhck_1:", c in cols1)

# duplicates in bhck_1
d = con.execute(f"""SELECT CAST(rssd9001 AS BIGINT) rssd9001, CAST(rssd9999 AS VARCHAR) rssd9999, wrdsdownloaddate,
    TRY_CAST(bhck1763 AS DOUBLE) bhck1763, TRY_CAST(bhck2122 AS DOUBLE) bhck2122_missing_in_file1,
    TRY_CAST(bhckb538 AS DOUBLE) bhckb538, TRY_CAST(bhck1410 AS DOUBLE) bhck1410
    FROM read_csv('{f1}', header=true, all_varchar=true)""").fetchdf() if "bhck2122" in cols1 else con.execute(f"""SELECT CAST(rssd9001 AS BIGINT) rssd9001,
    CAST(rssd9999 AS VARCHAR) rssd9999, wrdsdownloaddate, TRY_CAST(bhck1763 AS DOUBLE) bhck1763, TRY_CAST(bhckb538 AS DOUBLE) bhckb538,
    TRY_CAST(bhck1410 AS DOUBLE) bhck1410 FROM read_csv('{f1}', header=true, all_varchar=true)""").fetchdf()
dup = d[d.duplicated(["rssd9001", "rssd9999"], keep=False)].sort_values(["rssd9001", "rssd9999"])
print("bhck_1 duplicate rows:", len(dup), "keys:", dup[["rssd9001", "rssd9999"]].drop_duplicates().shape[0])
print("duplicate keys by date:", dup.rssd9999.value_counts().head(10).to_dict())
g = dup.groupby(["rssd9001", "rssd9999"])
nn = g[["bhck1763", "bhck1410"]].apply(lambda x: x.notna().sum()).reset_index()
print("non-null bhck1410 per duplicated key (value counts):", nn.bhck1410.value_counts().to_dict())
same = g.bhck1410.nunique(dropna=True)
print("duplicated keys with >1 distinct non-null bhck1410:", int((same > 1).sum()))
print(dup.head(12).to_string())

# Y-9C panel checks (from cache)
Y = pd.read_parquet(P4 + "cache/y9c_items.parquet")
Y["yr"] = Y.date.dt.year
# C&I split vs total
z = Y[Y.bhck1766.notna()]
both = z[z.bhck1763.notna() & z.bhck1764.notna()]
print("C&I: rows with 1766:", len(z), "with 1763 & 1764:", len(both),
      "max |1766-(1763+1764)|:", float((both.bhck1766 - both.bhck1763 - both.bhck1764).abs().max()),
      "share exact (<=1):", float(((both.bhck1766 - both.bhck1763 - both.bhck1764).abs() <= 1).mean()))
onlytot = z[z.bhck1763.isna()]
print("rows with 1766 but no 1763, by year:", onlytot.yr.value_counts().sort_index().to_dict())
print("rows with 1763 but no 1764, by year:", Y[Y.bhck1763.notna() & Y.bhck1764.isna()].yr.value_counts().sort_index().to_dict())
# 2007 CRE overlap: F-items vs BHDM items
o = Y[(Y.yr == 2007) & Y.bhckf158.notna() & Y.bhdm1415.notna()]
print("2007 overlap rows:", len(o), "constr F158+F159 vs BHDM1415 median ratio:", float(((o.bhckf158 + o.bhckf159) / o.bhdm1415).median()),
      "nonres F160+F161 vs BHDM1480 median ratio:", float(((o.bhckf160 + o.bhckf161) / o.bhdm1480).median()))
print("quarters with F158 present:", sorted(Y[Y.bhckf158.notna()].rssd9999.unique())[:3], "BHDM1415 last:", sorted(Y[Y.bhdm1415.notna()].rssd9999.unique())[-3:])
print("BHCKB538 first quarters:", sorted(Y[Y.bhckb538.notna()].rssd9999.unique())[:3], "K137 first:", sorted(Y[Y.bhckk137.notna()].rssd9999.unique())[:2],
      "2011 last:", sorted(Y[Y.bhck2011.notna()].rssd9999.unique())[-2:])
# consumer identity: 1975 vs B538+B539+2011 (2001-2010) and B538+B539+K137+K207 (2011+)
a = Y[(Y.yr.between(2001, 2010)) & Y.bhck1975.notna() & Y.bhckb538.notna()]
print("2001-10 consumer: median (B538+B539+2011)/1975:", float(((a.bhckb538 + a.bhckb539 + a.bhck2011) / a.bhck1975).replace([np.inf, -np.inf], np.nan).median()),
      "share |diff|<=1:", float(((a.bhckb538 + a.bhckb539 + a.bhck2011 - a.bhck1975).abs() <= 1).mean()))
b = Y[(Y.yr >= 2011) & Y.bhck1975.notna() & Y.bhckk137.notna()]
print("2011+ consumer: share |B538+B539+K137+K207-1975|<=1:", float(((b.bhckb538 + b.bhckb539 + b.bhckk137 + b.bhckk207 - b.bhck1975).abs() <= 1).mean()))
c = Y[(Y.yr == 2000) & Y.bhck1975.notna()]
print("2000: rows with 1975:", len(c), "with 2011:", int(c.bhck2011.notna().sum()), "median 2011/1975:", float((c.bhck2011 / c.bhck1975).median()))
# 1-4 family + other identity vs 1410 (domestic RE total)
e = Y[Y.bhdm1410.notna()]
print("BHCK1410 vs BHDM1410 median ratio:", float((e.bhck1410 / e.bhdm1410).replace([np.inf, -np.inf], np.nan).median()))
