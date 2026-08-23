#!/usr/bin/env python3
"""Fail loudly when the publishing schedule is running out.

The writing loop runs on Imran's machine. On 2026-08-22 its working folder had
been deleted, so it fired, could not start, and wrote nothing. The trigger still
recorded a run, the site kept publishing from its backlog, and nothing anywhere
said a word. It went unnoticed for a week.

That is the failure worth engineering against: not the loop breaking, but the
loop breaking quietly. This runs in GitHub Actions, which is independent of that
machine entirely, and fails the workflow when the runway gets short. A failed run
turns into an email from GitHub, which is the part a human actually sees.

Deliberately a separate job from the deploy: publishing must never be blocked by
a warning about the future.
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import build  # noqa: E402

# Steady state is three posts written and three published a week, so runway sits
# flat. A stalled writer shows up as this number falling by seven days a week.
# 35 days trips about three weeks into a stall: early enough to fix without any
# reader ever seeing a gap, late enough that a single skipped week stays quiet.
MIN_DAYS = 35


def main():
    now = datetime.now()
    future = sorted(p["dt"] for p in build.load_posts() if p["dt"] > now)

    if not future:
        print("RUNWAY EXHAUSTED: every written post has already published.")
        sys.exit(1)

    days = (future[-1] - now).days
    print(f"  {len(future)} posts scheduled, through {future[-1]:%a %d %b %Y} "
          f"({days} days of runway)")

    if days < MIN_DAYS:
        print(f"\nRUNWAY LOW: {days} days left, want {MIN_DAYS}+.")
        print("The Saturday writing loop has probably stopped producing.")
        print("Check that its working folder still exists and that it is")
        print("committing: the last failure was a deleted folder, which the")
        print("task reported as a completed run.")
        sys.exit(1)

    print("  Runway healthy.")


if __name__ == "__main__":
    main()
