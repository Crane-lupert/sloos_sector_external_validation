# v3 reference implementation - as run on 2026-11-21; absolute paths replaced by v3paths (see scripts/v3/README.md)
"""Phase 4B / Step 0 - MDRM item definitions and validity periods (dump bank_all.wrds_bank_reg_vars) for the Y-9C loan items
used in the 1990s. No returns. Output: logs/p4b_02_reg_vars.log"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from v3paths import V3WORK, WRDS_DUMP, REPO_CACHE
import duckdb
import pandas as pd

pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 110); pd.set_option("display.max_rows", 200)
f = WRDS_DUMP + "bank_all.wrds_bank_reg_vars.csv.gz"
d = duckdb.connect().execute(f"SELECT * FROM read_csv('{f}', header=true, all_varchar=true)").fetchdf()
print("columns:", list(d.columns), "rows", len(d))
items = ["1763", "1764", "1766", "1415", "1420", "1460", "1480", "1797", "1798", "5367", "5368", "1410", "2008", "2011", "B538", "B539",
         "K137", "K207", "1975", "2122", "2170", "F158", "F159", "F160", "F161"]
want = {p + i for p in ("BHCK", "BHDM") for i in items}
x = d[(d.reporting_form == "FR Y-9C") & d.variable_name.str.upper().isin(want)]
print(x[["variable_name", "start_date", "end_date", "schedule", "item_name"]].sort_values("variable_name").to_string(index=False))
