#!/usr/bin/env python3
"""Pull Search Console query data and bank it locally.

This is the plumbing half of the feedback loop: it fetches what people actually
searched to reach the site and appends it to content/search-data.json. The
interpretation half lives in gsc_topics.py.

It is written to be harmless before there is anything to fetch. With no
credentials, or with an empty account, it prints what is missing and exits 0 —
it must never break a writing run.

Uses google.auth + requests directly rather than the Google API client library,
so it needs nothing that is not already installed.

Run:  python tools/gsc_pull.py
"""

import json
import sys
import urllib.parse
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
STORE = ROOT / "content" / "search-data.json"

# Path to the service-account key. Kept under secrets/, which is gitignored —
# this file is a credential and must never reach the repository.
KEY_FILE = ROOT / "secrets" / "gsc-service-account.json"

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

    queries = fetch(creds, start, end, ["query"])
    pages = fetch(creds, start, end, ["query", "page"])

    if not queries:
        print(f"  Connected, but no data yet for {start} to {end}.")
        print("  Search Console has nothing to report until pages are indexed and")
        print("  receiving impressions. Re-run in a few weeks.")
        # Still write the file so downstream tools have a valid shape to read.
        STORE.write_text(json.dumps(
            {"pulled": date.today().isoformat(), "start": start.isoformat(),
             "end": end.isoformat(), "queries": [], "query_pages": []},
            indent=2), encoding="utf-8")
        return

    data = {
        "pulled": date.today().isoformat(),
        "start": start.isoformat(),
        "end": end.isoformat(),
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
    }
    STORE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    total_i = sum(q["impressions"] for q in data["queries"])
    total_c = sum(q["clicks"] for q in data["queries"])
    print(f"  {start} to {end}")
    print(f"  {len(data['queries'])} queries, {total_i:,} impressions, {total_c:,} clicks")
    print(f"  written to {STORE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
