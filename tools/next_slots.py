#!/usr/bin/env python3
"""Report the next free publishing slots and what the queue says goes in them.

Slots are Monday / Wednesday / Friday at 09:00, continuing from the latest post
already written. Run it before a writing session:

    python tools/next_slots.py          # next 3
    python tools/next_slots.py 6        # next 6
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import build  # noqa: E402

QUEUE = Path(__file__).parent.parent / "content" / "queue.json"
PUBLISH_DAYS = {0, 2, 4}          # Mon, Wed, Fri
PUBLISH_HOUR = 9


def next_slots(after: datetime, n: int):
    out, day = [], after.date()
    while len(out) < n:
        day += timedelta(days=1)
        if day.weekday() in PUBLISH_DAYS:
            out.append(datetime(day.year, day.month, day.day, PUBLISH_HOUR))
    return out


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3

    posts = build.load_posts()
    latest = max(p["dt"] for p in posts)
    written = {p["slug"] for p in posts}

    queue = json.loads(QUEUE.read_text(encoding="utf-8"))["posts"]
    pending = [q for q in queue if q["status"] == "pending" and q["slug"] not in written]

    print(f"  {len(posts)} posts written, latest {latest:%a %d %b %Y}")
    print(f"  {len(pending)} still pending in the queue\n")

    if not pending:
        print("  Queue empty — add entries to content/queue.json before the next run.")
        return

    for slot, item in zip(next_slots(latest, n), pending[:n]):
        print(f"  {slot:%a %d %b %Y}  {item['slug']}")
        print(f"    {item['title']}")
        print(f"    keyword: {item['keyword']}   category: {item['category']}")
        print(f"    angle: {item['angle']}\n")

    print(f'  Set "date": "{next_slots(latest, 1)[0]:%Y-%m-%d %H:%M:%S}" on the first one.')


if __name__ == "__main__":
    main()
