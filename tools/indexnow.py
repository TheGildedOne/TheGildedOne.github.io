#!/usr/bin/env python3
"""Tell Bing and friends about published URLs the moment they go live.

Google finds pages on its own schedule and ignores this protocol. Bing, Yandex,
Naver and Seznam accept it — and Bing's index is what powers Copilot and a good
share of AI search, so it is worth the one HTTP call.

Reads the freshly built sitemap, so it always submits exactly what is public.
Run after the site is deployed:  python tools/indexnow.py
"""

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent
SITEMAP = ROOT / "dist" / "sitemap.xml"
KEY = "aa390cafeb737eb5780a3bd96c78c6f0"
ENDPOINT = "https://api.indexnow.org/indexnow"


def main():
    if not SITEMAP.exists():
        print("  no dist/sitemap.xml - run build.py first")
        sys.exit(1)

    urls = re.findall(r"<loc>(.*?)</loc>", SITEMAP.read_text(encoding="utf-8"))
    if not urls:
        print("  sitemap contains no URLs")
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
