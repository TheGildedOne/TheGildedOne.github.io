#!/usr/bin/env python3
"""Ask Google, page by page, whether it has actually indexed the site.

Every other check in this repo looks at our side: the post is scheduled, the
build is valid, the page is live. None of them asks whether Google has the page,
and for eight weeks nobody did. On 2026-10-01 the answer for 10 of 24 live posts
was no:

  * Seven were indexed only at the newsletter's tracking address
    (.../posts/mithras-tauroctony-decoded/?utm_source=veiled&utm_medium=email...).
    Buttondown's public archive links to posts with those tags, Google found the
    tagged link first, indexed that, and never fetched the real address at all,
    despite the canonical tag, the sitemap and every internal link pointing at it.
  * Three more had not been picked up in any form.

The posts still showed impressions in Search Console, under the tagged address,
which is why the totals looked ordinary and nothing seemed wrong.

This asks Search Console's URL Inspection API about every URL in the live
sitemap, and looks in the search data for any other address Google is showing in
its place. It reads the live sitemap, not the repo, so it checks what is public.

  python tools/check_indexing.py

What the statuses mean:

  indexed         Google has this address. Nothing to do.
  WRONG ADDRESS   Google is showing a different address for this page. Request
                  indexing of the real one in Search Console (URL Inspection,
                  paste the address, Request indexing).
  NOT INDEXED     Google knows the page or has never seen it, and is showing
                  nothing. Request indexing the same way.
  waiting         Not indexed, but published in the last two weeks. Normal.

Uses the same service-account key as gsc_pull.py, and like it prints what is
missing and exits 0 when the key is absent. Results go to
content/index-status.json so the next run can say what changed.
"""

import json
import re
import sys
import urllib.request
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
import gsc_pull  # noqa: E402

ROOT = Path(__file__).parent.parent
STORE = ROOT / "content" / "index-status.json"
SITEMAP = "https://veiledantiquity.com/sitemap.xml"
INSPECT = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"

# Google routinely takes days to pick up a new page. Younger than this and
# unindexed is a page still in the queue, not a fault.
GRACE_DAYS = 14


def publish_dates() -> dict:
    """{url: publish date} for posts, so a brand-new page is not reported as a fault."""
    try:
        import build
        return {p["url"]: p["dt"].date() for p in build.load_posts()}
    except Exception:
        return {}


def main():
    if not gsc_pull.KEY_FILE.exists():
        print(gsc_pull.SETUP.format(key=gsc_pull.KEY_FILE))
        return

    try:
        import requests
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account
    except ImportError:
        print("  google-auth is not installed:  pip install google-auth requests")
        return

    creds = service_account.Credentials.from_service_account_file(
        str(gsc_pull.KEY_FILE), scopes=[gsc_pull.SCOPE])
    creds.refresh(Request())
    headers = {"Authorization": f"Bearer {creds.token}"}

    with urllib.request.urlopen(SITEMAP, timeout=30) as r:
        urls = re.findall(r"<loc>(.*?)</loc>", r.read().decode("utf-8"))
    if not urls:
        print(f"  {SITEMAP} lists no URLs - cannot check anything")
        return

    # Every address Google has shown for the site lately. An address that is not
    # in the sitemap but shares a path with one that is, is a stand-in.
    # Ninety days, not the last month: a stand-in that has stopped earning
    # impressions is still the copy Google holds.
    end = date.today() - timedelta(days=2)
    shown = gsc_pull.fetch(creds, end - timedelta(days=90), end, ["page"])
    stand_ins = {}
    for row in shown:
        addr = row["keys"][0]
        clean = "https://" + addr.split("://", 1)[1].split("?", 1)[0]
        if addr != clean:
            stand_ins.setdefault(clean, []).append((addr, row.get("impressions", 0)))

    published = publish_dates()
    previous = {}
    if STORE.exists():
        try:
            previous = json.loads(STORE.read_text(encoding="utf-8")).get("pages", {})
        except Exception:
            previous = {}

    pages, counts = {}, {"indexed": 0, "WRONG ADDRESS": 0, "NOT INDEXED": 0, "waiting": 0}
    for url in urls:
        r = requests.post(INSPECT, headers=headers, timeout=60,
                          json={"inspectionUrl": url, "siteUrl": gsc_pull.SITE_URL})
        if r.status_code != 200:
            # Do not guess. A partial answer written to disk would read as "the
            # rest are fine" on the next run.
            print(f"  URL Inspection returned HTTP {r.status_code} for {url}")
            print(f"  {r.text[:200]}")
            print("  Stopping without saving: this run says nothing about the site.")
            return
        idx = r.json().get("inspectionResult", {}).get("indexStatusResult", {})
        coverage = idx.get("coverageState", "unknown")
        google_canonical = idx.get("googleCanonical", "")

        if idx.get("verdict") == "PASS" and google_canonical in ("", url):
            status = "indexed"
        elif stand_ins.get(url) or (google_canonical and google_canonical != url):
            status = "WRONG ADDRESS"
        elif url in published and (date.today() - published[url]).days < GRACE_DAYS:
            status = "waiting"
        else:
            status = "NOT INDEXED"

        counts[status] += 1
        pages[url] = {
            "status": status,
            "coverage": coverage,
            "last_crawl": idx.get("lastCrawlTime", "")[:10],
            "google_shows": [a for a, _ in sorted(stand_ins.get(url, []), key=lambda x: -x[1])]
                            or ([google_canonical] if google_canonical not in ("", url) else []),
        }

    STORE.write_text(json.dumps({"checked": date.today().isoformat(), "counts": counts,
                                 "pages": pages}, indent=2), encoding="utf-8")

    short = lambda u: u.replace("https://veiledantiquity.com", "") or "/"   # noqa: E731
    for status in ("WRONG ADDRESS", "NOT INDEXED", "waiting"):
        rows = [(u, p) for u, p in pages.items() if p["status"] == status]
        if not rows:
            continue
        print(f"\n  {status} ({len(rows)})")
        for u, p in rows:
            was = previous.get(u, {}).get("status")
            note = f"   [was {was}]" if was and was != status else ""
            print(f"    {short(u)}{note}")
            print(f"        Google says: {p['coverage']}"
                  + (f", last crawled {p['last_crawl']}" if p["last_crawl"] else ", never crawled"))
            for other in p["google_shows"][:2]:
                print(f"        showing instead: {short(other)[:110]}")

    fixed = [u for u, p in pages.items()
             if p["status"] == "indexed" and previous.get(u, {}).get("status") not in (None, "indexed")]
    if fixed:
        print(f"\n  Newly indexed since the last check ({len(fixed)}):")
        for u in fixed:
            print(f"    {short(u)}")

    faults = counts["WRONG ADDRESS"] + counts["NOT INDEXED"]
    print(f"\n  INDEXING  {counts['indexed']} of {len(urls)} pages indexed at the right address, "
          f"{faults} need attention, {counts['waiting']} new and waiting.")
    if faults:
        print("  To fix one: Search Console -> paste the address in the top search bar ->")
        print("  Request indexing. About ten a day are allowed.")
    print(f"  written to {STORE.relative_to(ROOT)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:               # a report, not a gate: never break a writing run
        print(f"  indexing check skipped: {e}")
    sys.exit(0)
