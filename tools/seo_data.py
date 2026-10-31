#!/usr/bin/env python3
"""The writing loop's window onto the private SEO data repo.

Search Console data, the indexing status, the weekly report and the log of page
changes all live in TheGildedOne/veiled-antiquity-data, a private repo, so
none of it is public (this repo is) and none of it piles up on Imran's machine.
This reads and appends over the GitHub API through the `gh` command, which is
already signed in here, and saves nothing to disk.

  python tools/seo_data.py report
      Print this week's report: Search Console totals, indexing, topic ideas,
      pages to improve, and the results of earlier changes.

  python tools/seo_data.py log <slug> "<what changed, and the search phrase it targets>"
      Record a change to a live page, so the weekly report can say a month on
      whether it helped. Log every change the loop makes to a published post's
      search title, description, FAQ or body, and only those.
"""

import base64
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO = "TheGildedOne/veiled-antiquity-data"
POSTS = Path(__file__).parent.parent / "content" / "posts"
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def gh(*args, body=None):
    r = subprocess.run(["gh", "api", *args], input=json.dumps(body) if body else None,
                       capture_output=True, text=True, encoding="utf-8", timeout=60)
    if r.returncode != 0:
        sys.exit(f"  GitHub said no: {(r.stderr or r.stdout).strip()[:300]}\n"
                 f"  If gh is signed out, Imran needs to run: gh auth login")
    return r.stdout


def report():
    print(gh(f"repos/{REPO}/contents/report.txt", "-H", "Accept: application/vnd.github.raw"))


def log(slug, change):
    if not SLUG.match(slug) or not list(POSTS.glob(f"*-{slug}.html")):
        sys.exit(f"  '{slug}' is not the slug of any post in content/posts")
    if len(change.strip()) < 15:
        sys.exit("  Say what changed and which search phrase it targets; the result is useless without it.")

    meta = json.loads(gh(f"repos/{REPO}/contents/seo-log.json"))
    data = json.loads(base64.b64decode(meta["content"]).decode("utf-8"))
    entry = {"date": date.today().isoformat(), "page": slug, "change": change.strip()}
    data.setdefault("entries", []).append(entry)

    gh("-X", "PUT", f"repos/{REPO}/contents/seo-log.json", "--input", "-", body={
        "message": f"Log change to {slug}",
        "content": base64.b64encode(
            (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8")).decode("ascii"),
        "sha": meta["sha"],
    })
    print(f"  Logged: {entry['date']} {slug}: {entry['change']}")
    print(f"  {len(data['entries'])} changes on record. The result shows in the report about a month on.")


def main():
    args = sys.argv[1:]
    if args[:1] == ["report"] and len(args) == 1:
        report()
    elif args[:1] == ["log"] and len(args) == 3:
        log(args[1], args[2])
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
