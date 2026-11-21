# v3 reference implementation - as run on 2026-11-21; absolute paths replaced by v3paths (see scripts/v3/README.md)
"""Phase 4 / step 00 - probe FRED HTML for SLOOS series IDs and titles (no raw HTML is stored).

Fetches public FRED pages with a generic User-Agent (research-reverify/1.0), <= 1 request per second,
stops on 403 / 429. Prints only the extracted (series id, title) pairs.
Usage: python p4_00_fred_probe.py <url> [<url> ...]
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from v3paths import V3WORK, WRDS_DUMP, REPO_CACHE
import re
import sys
import time
import urllib.request
import urllib.error
import html as htmlmod

UA = {"User-Agent": "research-reverify/1.0"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""


for url in sys.argv[1:]:
    st, txt = get(url)
    print(f"## {url} -> HTTP {st}, {len(txt)} chars", flush=True)
    if st in (403, 429):
        print("STOP: blocked", flush=True)
        sys.exit(2)
    # title tag
    m = re.search(r"<title>(.*?)</title>", txt, re.S)
    if m:
        print("TITLE:", htmlmod.unescape(m.group(1).strip()))
    # series links with anchor text
    pairs = re.findall(r'href="/series/([A-Z0-9]+)"[^>]*>\s*([^<]{5,300}?)\s*<', txt)
    seen = set()
    for sid, ttl in pairs:
        ttl = htmlmod.unescape(ttl.strip())
        if (sid, ttl) in seen:
            continue
        seen.add((sid, ttl))
        print(f"  {sid}\t{ttl}")
    # links of other forms
    ids = sorted(set(re.findall(r"/series/([A-Z0-9]{4,})", txt)))
    print("  ALL_IDS:", " ".join(ids))
    time.sleep(1.2)
