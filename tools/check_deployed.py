#!/usr/bin/env python3
"""Assert that every post whose date has arrived is actually live on the site.

The gap this closes. On 2026-08-28 the Damnatio Memoriae post was due, committed,
correct, and not on the site: GitHub had silently dropped the scheduled publish
run. Every check in the repo still reported healthy, because they all inspected
what was *intended*. check_runway.py verifies posts are scheduled. check.py
verifies the built output is well formed. Nothing verified that the thing readers
actually load had changed. The only reason anyone noticed was Imran spotting that
the newsletter email had not arrived, which is a monitor that requires a human to
remember the publishing schedule.

So this one deliberately does not trust the repo. It fetches the live sitemap and
compares it against what should be published by now.

**It must run in its own workflow, not the publish one.** A check that lives
inside the job that failed cannot report that the job did not run. monitor.yml
exists for this reason and is scheduled after both publish windows, so a failure
here means the post is genuinely late rather than in flight.

  python tools/check_deployed.py
  python tools/check_deployed.py --grace-hours 2
  python tools/check_deployed.py --url http://localhost:8000

Exit 1 if a due post is missing, or if the site cannot be reached at all.
"""

import argparse
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import build  # noqa: E402

UA = "VeiledAntiquity-DeployCheck/1.0 (https://veiledantiquity.com)"
DEFAULT_URL = "https://veiledantiquity.com"

# A post dated 09:00 is published by a cron at 09:05, so "due" and "should be
# visible" are not the same instant. The grace period stops the check firing at
# the exact moment a deploy is legitimately in flight.
DEFAULT_GRACE_HOURS = 2


def fetch_sitemap(base):
    """Sitemap text, retried. A site that cannot be reached is itself an incident."""
    url = base.rstrip("/") + "/sitemap.xml"
    err = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8"), None
        except Exception as e:  # noqa: BLE001 - any failure is the same signal here
            err = f"{type(e).__name__}: {e}"
            if attempt < 2:
                time.sleep(5 * (attempt + 1))
    return None, err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--grace-hours", type=float, default=DEFAULT_GRACE_HOURS)
    args = ap.parse_args()

    # build.py --live uses a naive datetime.now(), which on the GitHub runner is
    # UTC. Match that exactly rather than inventing a second notion of "due".
    now = datetime.now()
    cutoff = now - timedelta(hours=args.grace_hours)

    posts = build.load_posts()
    due = [p for p in posts if p["dt"] <= cutoff]
    pending = [p for p in posts if p["dt"] > cutoff]

    sitemap, err = fetch_sitemap(args.url)
    if sitemap is None:
        print(f"  UNREACHABLE  {args.url}/sitemap.xml after 3 tries")
        print(f"  {err}")
        print("\n  Cannot confirm anything is live. Treating as a failure: if the")
        print("  site is genuinely down that is worth knowing immediately.")
        sys.exit(1)

    live = set(re.findall(r"/posts/([^/<]+)/", sitemap))
    missing = [p for p in due if p["slug"] not in live]

    print(f"  {len(live)} post(s) live, {len(due)} due by "
          f"{cutoff:%Y-%m-%d %H:%M} ({args.grace_hours}h grace), "
          f"{len(pending)} scheduled ahead.")

    # Not an error, but worth surfacing: something is live that the repo does not
    # think is due. Usually a clock or timezone drift rather than a real problem.
    unexpected = live - {p["slug"] for p in posts}
    if unexpected:
        print(f"  note: {len(unexpected)} live URL(s) not in the repo: "
              f"{', '.join(sorted(unexpected))}")

    if missing:
        print(f"\n  {len(missing)} POST(S) DUE BUT NOT LIVE:")
        for p in sorted(missing, key=lambda p: p["dt"]):
            secs = (now - p["dt"]).total_seconds()
            when = f"{int(secs // 3600)}h late" if secs >= 0 else "not yet due"
            print(f"    - {p['slug']}  due {p['dt']:%a %d %b %H:%M}  ({when})")
        print("\n  The publish workflow has probably been dropped or has failed.")
        print("  Fix now with:  gh workflow run publish.yml")
        sys.exit(1)

    print("  Everything due is live.")


if __name__ == "__main__":
    main()
