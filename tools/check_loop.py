#!/usr/bin/env python3
"""Fail if the Saturday writing loop has stopped producing posts.

The loop runs on Imran's machine as a scheduled task, and the app reports a run
that wrote nothing exactly the way it reports one that wrote three posts:
"succeeded". On 2026-10-10 the run stalled on its fourth command, waiting for a
permission approval with nobody at the machine, and was recorded as a success
five seconds after it started. Nothing noticed for four days.

check_runway.py would have noticed eventually, but only once the scheduled
backlog fell under 35 days, which is three to four missed Saturdays. This asks
the sharper question: when did a new post last arrive in the repo? A healthy
loop adds posts every Saturday, so more than eight days means a run was missed.

Runs in monitor.yml on GitHub's machines, not on the machine that failed, and
a failed run emails Imran.

  python tools/check_loop.py
  python tools/check_loop.py --now=2026-10-12   # pretend it is that date
"""

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent

# One missed Saturday is enough to say so. Eight rather than seven so a run
# that fires a few hours late does not raise a false alarm.
MAX_DAYS = 8


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                          timeout=60, check=True).stdout.strip()


def main():
    now = datetime.now(timezone.utc)
    for arg in sys.argv[1:]:
        if arg.startswith("--now="):
            now = datetime.strptime(arg.split("=", 1)[1], "%Y-%m-%d").replace(tzinfo=timezone.utc)

    # A shallow clone only knows its newest commit, which would make the last
    # post look as new as whatever was pushed last. Refuse rather than guess.
    if git("rev-parse", "--is-shallow-repository") != "false":
        print("  Cannot tell: this is a shallow clone. Check out with fetch-depth: 0.")
        sys.exit(1)

    # The newest commit that ADDED a post file. Edits to existing posts (link
    # backfills, retitling) do not count: only the loop's real output does.
    line = git("log", "-1", "--diff-filter=A", "--format=%ct|%h %s", "--", "content/posts")
    if not line:
        print("  No commit has ever added a post. Nothing to measure.")
        sys.exit(1)
    stamp, what = line.split("|", 1)
    added = datetime.fromtimestamp(int(stamp), timezone.utc)
    age = (now - added).total_seconds() / 86400

    print(f"  Newest post added {added:%a %d %b %Y %H:%M} UTC, {age:.1f} days ago")
    print(f"    ({what})")
    if age > MAX_DAYS:
        print(f"\n  The writing loop has not added a post in {age:.0f} days, so at least one")
        print("  Saturday run did nothing. Its run history will probably still say")
        print("  'succeeded'. Open the routine's latest run in the Claude app to see where")
        print("  it stopped (usually a permission prompt), then press Run now.")
        sys.exit(1)
    print("  Writing loop is producing.")


if __name__ == "__main__":
    main()
