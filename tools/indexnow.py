#!/usr/bin/env python3
"""Tell Bing and friends about published URLs the moment they go live.

Google finds pages on its own schedule and ignores this protocol. Bing, Yandex,
Naver and Seznam accept it — and Bing's index is what powers Copilot and a good
share of AI search, so it is worth the one HTTP call.

Reads the freshly built sitemap, so it only ever submits what is public, and
submits only the pages whose <lastmod> is recent. Until 2026-10-01 it sent every
URL on every deploy, three times a day: IndexNow is for pages that changed, and
announcing thirty-five unchanged ones daily teaches Bing to ignore the signal.

Run after the site is deployed:  python tools/indexnow.py
                                 python tools/indexnow.py --all   # everything
"""

import json
import re
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
SITEMAP = ROOT / "dist" / "sitemap.xml"
KEY = "aa390cafeb737eb5780a3bd96c78c6f0"
ENDPOINT = "https://api.indexnow.org/indexnow"

# A page counts as changed for this many days. More than one, because the two
# daily publish runs can both be dropped (2026-08-28) and the next day's run
# should still announce yesterday's post.
RECENT_DAYS = 3


def main():
    if not SITEMAP.exists():
        print("  no dist/sitemap.xml - run build.py first")
        sys.exit(1)

    entries = re.findall(r"<loc>(.*?)</loc><lastmod>(.*?)</lastmod>",
                         SITEMAP.read_text(encoding="utf-8"))
    if not entries:
        print("  sitemap contains no dated URLs")
        return

    cutoff = (date.today() - timedelta(days=RECENT_DAYS)).isoformat()
    everything = "--all" in sys.argv
    urls = [loc for loc, lastmod in entries if everything or lastmod >= cutoff]
    if not urls:
        print(f"  nothing changed since {cutoff} - nothing to submit "
              f"({len(entries)} URLs unchanged)")
        return

    host = re.sub(r"^https?://", "", urls[0]).split("/")[0]
    payload = {
        "host": host,
        "key": KEY,
        "keyLocation": f"https://{host}/{KEY}.txt",
        "urlList": urls[:10000],
    }

    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"  submitted {len(urls)} URLs to IndexNow - HTTP {r.status}")
    except urllib.error.HTTPError as e:
        # 422 usually means the key file is not reachable yet on a first deploy.
        print(f"  IndexNow returned HTTP {e.code}: {e.reason}")
        if e.code == 422:
            print(f"  check that https://{host}/{KEY}.txt is live and contains the key")
        sys.exit(0)          # never fail the deploy over a notification
    except Exception as e:
        print(f"  IndexNow submission skipped: {e}")
        sys.exit(0)


if __name__ == "__main__":
    main()
