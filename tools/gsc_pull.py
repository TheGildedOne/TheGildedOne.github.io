#!/usr/bin/env python3
"""Pull Search Console query data and bank it.

This is the plumbing half of the feedback loop: it fetches what people actually
searched to reach the site and writes it to search-data.json. The
interpretation half lives in gsc_topics.py and seo_review.py.

Since 2026-10-31 this runs weekly on GitHub, in the private repo
TheGildedOne/veiled-antiquity-data, not on Imran's machine. That repo's workflow
sets VA_DATA_DIR to its own checkout and GSC_KEY_FILE to the key it holds as a
secret, so the data and the credential never touch this public repo or the PC.
With VA_DATA_DIR set, each run also keeps a dated copy in snapshots/, which is
what lets seo_review.py measure whether a change to a page helped.

It is written to be harmless before there is anything to fetch. With no
credentials, or with an empty account, it prints what is missing and exits 0 —
it must never break a writing run.

Uses google.auth + requests directly rather than the Google API client library,
so it needs nothing that is not already installed.

Run:  python tools/gsc_pull.py
"""

import json
import os
import sys
import urllib.parse
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent

# Where the data lives. The weekly job points this at the private data repo; the
# fallback is the old in-repo location, which nothing writes to any more.
DATA_DIR = Path(os.environ.get("VA_DATA_DIR") or ROOT / "content")
STORE = DATA_DIR / "search-data.json"
SNAPSHOTS = DATA_DIR / "snapshots" if os.environ.get("VA_DATA_DIR") else None

# Path to the service-account key. On GitHub it is written from a repo secret to
# a temp file; the fallback is secrets/, which is gitignored. Either way this file
# is a credential and must never reach a repository.
KEY_FILE = Path(os.environ.get("GSC_KEY_FILE") or ROOT / "secrets" / "gsc-service-account.json")

# The window used to judge a change to one page: short enough that a change shows
# up a month later, long enough to smooth out a single odd week.
RECENT_DAYS = 28

# Domain properties are addressed as sc-domain:<domain>. A URL-prefix property
# would instead be the full URL, e.g. "https://veiledantiquity.com/".
SITE_URL = "sc-domain:veiledantiquity.com"

DAYS = 90          # Search Console lags ~2 days; 90 gives a stable window.
ROW_LIMIT = 25000

API = "https://searchconsole.googleapis.com/webmasters/v3/sites/{site}/searchAnalytics/query"
SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"

SETUP = """
  No Search Console credentials found.

  This is expected until the one-time setup is done. To enable it:

    1. console.cloud.google.com -> create (or pick) a project
    2. APIs & Services -> Library -> enable "Google Search Console API"
    3. APIs & Services -> Credentials -> Create credentials -> Service account
       Create a JSON key for it and download the file
    4. Copy the service account's email address (ends @...iam.gserviceaccount.com)
    5. In Search Console -> Settings -> Users and permissions -> Add user
       Paste that email, permission "Full"
    6. Save the JSON key as:
         {key}

  Nothing else changes. This script starts collecting on the next run.
"""


def fetch(creds, start, end, dimensions):
    import requests
    url = API.format(site=urllib.parse.quote(SITE_URL, safe=""))
    body = {
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "dimensions": dimensions,
        "rowLimit": ROW_LIMIT,
    }
    r = requests.post(url, json=body,
                      headers={"Authorization": f"Bearer {creds.token}"}, timeout=60)
    if r.status_code == 403:
        print("  403 from Search Console — the service account is authenticated but has")
        print("  not been added as a user on the property. See step 5 of the setup.")
        sys.exit(0)
    r.raise_for_status()
    return r.json().get("rows", [])


def main():
    if not KEY_FILE.exists():
        print(SETUP.format(key=KEY_FILE))
        sys.exit(0)

    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request
    except ImportError:
        print("  google-auth is not installed:  pip install google-auth requests")
        sys.exit(0)

    creds = service_account.Credentials.from_service_account_file(
        str(KEY_FILE), scopes=[SCOPE])
    creds.refresh(Request())

    end = date.today() - timedelta(days=2)      # Search Console lags
    start = end - timedelta(days=DAYS)

    # Fetched with NO dimensions, and this is not redundant with the query rows.
    #
    # Google withholds rare queries from any query-dimensioned report, because a
    # search only a handful of people made could identify them. Those impressions
    # and clicks still exist; they are simply absent from the breakdown. On a small
    # site almost everything is rare, so the gap is enormous rather than marginal:
    # on 2026-09-02 the query rows summed to 64 impressions and 0 clicks while the
    # true totals were 275 and 6. Summing the rows had been reporting 23% of
    # impressions and none of the clicks, and it was the only number anyone looked at.
    totals = fetch(creds, start, end, [])
    queries = fetch(creds, start, end, ["query"])
    pages = fetch(creds, start, end, ["query", "page"])

    # Page-level rows are complete in a way the query rows are not (see above):
    # every impression lands on some page even when its query is withheld. These
    # are what seo_review.py ranks and measures pages by.
    recent_start = end - timedelta(days=RECENT_DAYS)
    page_totals = fetch(creds, start, end, ["page"])
    recent_totals = fetch(creds, recent_start, end, [])
    recent_pages = fetch(creds, recent_start, end, ["page"])

    if not queries:
        print(f"  Connected, but no data yet for {start} to {end}.")
        print("  Search Console has nothing to report until pages are indexed and")
        print("  receiving impressions. Re-run in a few weeks.")
        # Still write the file so downstream tools have a valid shape to read.
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        STORE.write_text(json.dumps(
            {"pulled": date.today().isoformat(), "start": start.isoformat(),
             "end": end.isoformat(), "queries": [], "query_pages": []},
            indent=2), encoding="utf-8")
        return

    t = totals[0] if totals else {}
    data = {
        "pulled": date.today().isoformat(),
        "start": start.isoformat(),
        "end": end.isoformat(),
        # Site-wide truth. Read these for "how is the site doing"; the query rows
        # below are a filtered subset and always undercount.
        "totals": {
            "clicks": t.get("clicks", 0),
            "impressions": t.get("impressions", 0),
            "ctr": round(t.get("ctr", 0), 4),
            "position": round(t.get("position", 0), 1),
        },
        "queries": [
            {"query": r["keys"][0], "clicks": r.get("clicks", 0),
             "impressions": r.get("impressions", 0),
             "ctr": round(r.get("ctr", 0), 4),
             "position": round(r.get("position", 0), 1)}
            for r in queries
        ],
        "query_pages": [
            {"query": r["keys"][0], "page": r["keys"][1],
             "clicks": r.get("clicks", 0), "impressions": r.get("impressions", 0),
             "position": round(r.get("position", 0), 1)}
            for r in pages
        ],
        "pages": page_rows(page_totals),
        "recent": {
            "start": recent_start.isoformat(),
            "end": end.isoformat(),
            "totals": {
                "clicks": (recent_totals[0] if recent_totals else {}).get("clicks", 0),
                "impressions": (recent_totals[0] if recent_totals else {}).get("impressions", 0),
            },
            "pages": page_rows(recent_pages),
        },
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STORE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    if SNAPSHOTS:
        SNAPSHOTS.mkdir(exist_ok=True)
        (SNAPSHOTS / f"{data['pulled']}.json").write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    shown_i = sum(q["impressions"] for q in data["queries"])
    shown_c = sum(q["clicks"] for q in data["queries"])
    tot_i, tot_c = data["totals"]["impressions"], data["totals"]["clicks"]
    pct = (shown_i / tot_i * 100) if tot_i else 0

    print(f"  {start} to {end}")
    print(f"  SITE TOTAL   {tot_c:,} clicks, {tot_i:,} impressions, "
          f"avg position {data['totals']['position']}")
    print(f"  named queries {len(data['queries'])}: {shown_c:,} clicks, "
          f"{shown_i:,} impressions ({pct:.0f}% of impressions)")
    if tot_i and pct < 60:
        print("  The rest are queries Google withholds as too rare to name. That is")
        print("  normal for a small site; judge the site by SITE TOTAL, and use the")
        print("  named queries only to see which topics are landing.")
    rc, ri = data["recent"]["totals"]["clicks"], data["recent"]["totals"]["impressions"]
    print(f"  LAST {RECENT_DAYS} DAYS {rc:,} clicks, {ri:,} impressions")


def page_rows(rows):
    return [{"page": r["keys"][0], "clicks": r.get("clicks", 0),
             "impressions": r.get("impressions", 0),
             "position": round(r.get("position", 0), 1)} for r in rows]


if __name__ == "__main__":
    main()
