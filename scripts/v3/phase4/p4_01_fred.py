# v3 reference implementation - as run on 2026-11-21; absolute paths replaced by v3paths (see scripts/v3/README.md)
"""Phase 4 / step 01 - SLOOS category series from FRED (public, no key).

For every candidate series (IDs taken from the FRED search-results page for
"Net Percentage of Domestic Banks Tightening Standards", logs/p4_00_fred_probe_a.log) this script
  (a) fetches the FRED series page and extracts only the <title> text (raw HTML is not stored),
  (b) fetches https://fred.stlouisfed.org/graph/fredgraph.csv?id=<ID> and stores the observations
      (date, value) in cache/fred/<ID>.csv,
  (c) writes cache/fred_meta.csv (id, title, title_ok, first_obs, last_obs, n_obs).
A series is usable only if its title starts with "Net Percentage of Domestic Banks Tightening Standards for".
User-Agent research-reverify/1.0, about 1 request per second, stop on 403 / 429. Cached files are reused.
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from v3paths import V3WORK, WRDS_DUMP, REPO_CACHE
import os
import re
import sys
import time
import html as htmlmod
import urllib.request
import urllib.error
import pandas as pd
from io import StringIO

P4 = V3WORK + "phase4/"
CD = P4 + "cache/fred/"
os.makedirs(CD, exist_ok=True)
UA = {"User-Agent": "research-reverify/1.0"}
PREFIX = "Net Percentage of Domestic Banks Tightening Standards for"
CANDIDATES = [
    # C&I
    "DRTSCILM", "DRTSCIS",
    # CRE
    "DRTSCREL", "SUBLPDRCSC", "SUBLPDRCSN", "SUBLPDRCSM",
    # RRE
    "DRTSPM", "DRTSNT", "DRTSSP", "SUBLPDHMSENQ", "SUBLPDHMSGNQ", "SUBLPDHMSQNQ", "SUBLPDHMSJNQ",
    "SUBLPDHMSKNQ", "SUBLPDHMSMNQ", "SUBLPDCLHSNQ",
    # credit card
    "DRTSCLCC",
    # other consumer
    "STDSAUTO", "STDSOTHCONS", "DRTSCOCL", "SUBLPDCLOSNQ",
    # documentation only: found by a second search (logs/p4_00_fred_probe_c.log); title is
    # "Net Percentage of Banks Tightening Standards for Mortgage Loans" -> fails the title rule, not used
    "H0SUBLPDHMSNQ",
]


def get(url, tries=4):
    """GET with retry on empty body / transient 5xx; returns (status, text). 403 / 429 returned at once."""
    st, txt = None, ""
    for k in range(tries):
        req = urllib.request.Request(url, headers=UA)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                st, txt = r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            st, txt = e.code, ""
        except Exception as e:  # timeouts, connection resets
            st, txt = -1, ""
            print(f"  [warn] {url}: {type(e).__name__}", flush=True)
        if st in (403, 429):
            return st, txt
        if st == 200 and txt.strip():
            return st, txt
        print(f"  [retry {k + 1}] {url} HTTP {st}, {len(txt)} chars", flush=True)
        time.sleep(3 * (k + 1))
    return st, txt


rows = []
for sid in CANDIDATES:
    f = CD + f"{sid}.csv"
    ft = CD + f"{sid}.title.txt"
    if os.path.exists(f) and os.path.exists(ft):
        title = open(ft, encoding="utf-8").read().strip()
        d = pd.read_csv(f)
        rows.append(dict(id=sid, title=title, title_ok=title.startswith(PREFIX), first_obs=d.date.min(), last_obs=d.date.max(), n_obs=len(d)))
        print(f"[cache] {sid}", flush=True)
        continue
    st, txt = get(f"https://fred.stlouisfed.org/series/{sid}")
    if st in (403, 429):
        print(f"STOP: HTTP {st} on series page {sid}", flush=True)
        sys.exit(2)
    m = re.search(r"<title>(.*?)</title>", txt, re.S)
    title = htmlmod.unescape(m.group(1).strip()) if m else ""
    title = re.sub(r"\s*\|\s*FRED\s*\|\s*St\. Louis Fed\s*$", "", title)
    title = re.sub(r"\s*\(" + re.escape(sid) + r"\)\s*$", "", title)
    time.sleep(1.1)
    st2, csv = get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}")
    if st2 in (403, 429):
        print(f"STOP: HTTP {st2} on fredgraph {sid}", flush=True)
        sys.exit(2)
    if st2 != 200 or not csv.strip():
        print(f"[FAIL] {sid}: fredgraph HTTP {st2}, empty body after retries", flush=True)
        rows.append(dict(id=sid, title=title, title_ok=title.startswith(PREFIX), first_obs=None, last_obs=None, n_obs=0))
        continue
    d = pd.read_csv(StringIO(csv))
    d.columns = ["date", "value"]
    d["value"] = pd.to_numeric(d.value, errors="coerce")
    d = d.dropna()
    d.to_csv(f, index=False)
    open(ft, "w", encoding="utf-8").write(title + "\n")
    rows.append(dict(id=sid, title=title, title_ok=title.startswith(PREFIX), first_obs=d.date.min(), last_obs=d.date.max(), n_obs=len(d)))
    print(f"[fetch] {sid} HTTP {st}/{st2} | {title} | {d.date.min()}..{d.date.max()} n={len(d)}", flush=True)
    time.sleep(1.1)
M = pd.DataFrame(rows)
M.to_csv(P4 + "cache/fred_meta.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 140)
print(M.to_string(index=False))
