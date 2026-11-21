# v3 reference implementation - as run on 2026-11-21; absolute paths replaced by v3paths (see scripts/v3/README.md)
"""Phase 4B / step 02 - download Chicago Fed BHCF quarterly CSV files (public FR Y-9C data).

Source page: https://www.chicagofed.org/banking/financial-institution-reports/bhc-data (static links bhcfYYMM.csv)
File URL   : https://www.chicagofed.org/~/media/others/banking/financial-institution-reports/bhc-data/bhcfYYMM.csv
Rules      : User-Agent 'research-reverify/1.0' only (no personal or contact data), >= 2 s between requests (<= 0.5/s),
             stop at the first HTTP 403 or 429 (no retry, no workaround). Files already on disk (or already extracted to
             cache/bhcf/<yymm>.parquet) are skipped.
Usage      : python -E -P p4b_02_download.py <outdir> <yymm> [<yymm> ...]
Writes     : <outdir>/bhcf<yymm>.csv and appends one line per request to logs/p4b_02_download.log (status, bytes, sha256).
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from v3paths import V3WORK, WRDS_DUMP, REPO_CACHE
import hashlib
import os
import sys
import time
import urllib.error
import urllib.request

BASE = "https://www.chicagofed.org/~/media/others/banking/financial-institution-reports/bhc-data/bhcf{}.csv"
P4B = V3WORK + "phase4b/"
LOG = P4B + "logs/p4b_02_download.log"
UA = "research-reverify/1.0"


def log(msg):
    line = time.strftime("%Y-%m-%d %H:%M:%S ") + msg
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main():
    outdir = sys.argv[1]
    os.makedirs(outdir, exist_ok=True)
    last = 0.0
    for yymm in sys.argv[2:]:
        dst = os.path.join(outdir, f"bhcf{yymm}.csv")
        if os.path.exists(dst) or os.path.exists(P4B + f"cache/bhcf/{yymm}.parquet"):
            log(f"skip {yymm} (already present)")
            continue
        wait = 2.0 - (time.time() - last)
        if wait > 0:
            time.sleep(wait)
        url = BASE.format(yymm)
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        last = time.time()
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                body = r.read()
                status, ctype = r.status, r.headers.get("Content-Type")
        except urllib.error.HTTPError as e:
            log(f"{yymm} HTTP {e.code} {url}")
            if e.code in (403, 429):
                log("STOP: HTTP 403/429 received - no retry, no workaround (protocol)")
                sys.exit(2)
            continue
        except Exception as e:  # network error: log and continue with the next file
            log(f"{yymm} ERROR {type(e).__name__}: {e}")
            continue
        with open(dst, "wb") as f:
            f.write(body)
        log(f"{yymm} HTTP {status} {ctype} bytes {len(body)} sha256 {hashlib.sha256(body).hexdigest()} {url}")


if __name__ == "__main__":
    main()
