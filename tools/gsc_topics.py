#!/usr/bin/env python3
"""Turn Search Console data into topic proposals.

Two signals, in order of value:

  ORPHAN     a query pulling impressions onto a post that is not really about it.
             The archive telling us, empirically, that something mentioned in
             passing deserves its own piece. This is the good one.

  STRIKING   a query sitting around positions 5-20. On page two already; a
             dedicated post can often take page one.

Proposals are proposals. They still have to clear the five criteria in
WRITING-LOOP.md before anything gets written, and BLOCKED_TERMS below is a hard
stop so impressions can never drag the site toward content that would rank but
does not belong here.

Run:  python tools/gsc_topics.py
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
QUEUE = ROOT / "content" / "queue.json"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import build  # noqa: E402
import gsc_pull  # noqa: E402

STORE = gsc_pull.STORE

# --- tunables -------------------------------------------------------------
# Defaults set blind, before any real data existed. Revisit once there are a
# few months of history — these numbers are guesses, the logic around them is not.
#
# The impressions bar scales with the site. It was a flat 30 until 2026-10-31,
# when not one of the 105 queries on record reached it, so this tool proposed
# nothing and topics were being chosen on autocomplete alone. It is now the top
# fifth of the site's own queries, never below a floor that keeps one-off
# searches out, so it says something now and grows stricter as traffic grows.
MIN_FLOOR = 5
TOP_SHARE = 0.2
STRIKING_LOW, STRIKING_HIGH = 4.0, 20.0
COVERED_OVERLAP = 0.6       # token overlap at which a post already covers a query
TOP_N = 15

# The editorial gate, enforced rather than trusted. A query containing any of
# these must never become a topic, however many impressions it carries.
BLOCKED_TERMS = {
    "alien", "aliens", "atlantis", "annunaki", "anunnaki", "nephilim",
    "lemuria", "hyperborea", "pyramid power", "ancient technology",
    "suppressed", "forbidden knowledge they", "illuminati", "reptilian",
    "flat earth", "giants skeleton", "nibiru", "lost civilization",
    "lost civilisation",
}

STOP = {"the", "of", "a", "an", "in", "and", "to", "for", "what", "was", "is",
        "were", "did", "who", "how", "why", "ancient", "roman", "greek"}


def tokens(text):
    return {w for w in re.findall(r"[a-z]+", (text or "").lower()) if w not in STOP}


def blocked(query):
    q = query.lower()
    return any(term in q for term in BLOCKED_TERMS)


def noise(query):
    """A short single word ("yes", "both") is a stray search, not a subject.

    These turned up in the October 2026 data near the top of page one, which made
    them score as striking-distance topics.
    """
    words = query.split()
    return len(words) == 1 and len(words[0]) < 5


def main():
    if not STORE.exists():
        print(f"  No {STORE} - run tools/gsc_pull.py first.")
        return

    data = json.loads(STORE.read_text(encoding="utf-8"))
    queries = data.get("queries", [])

    if not queries:
        print(f"  Search data is empty (window {data.get('start')} to {data.get('end')}).")
        print("  Nothing to propose yet. This is normal until posts have been")
        print("  indexed and are collecting impressions.")
        return

    posts = build.load_posts()
    covered = [
        (p["slug"], tokens(f"{p['focus_keyword']} {p['title']} {' '.join(p.get('tags', []))}"))
        for p in posts
    ]
    queued = {q["slug"] for q in json.loads(QUEUE.read_text(encoding="utf-8"))["posts"]}

    # Which page each query actually lands on, for the orphan signal.
    landing = {}
    for row in data.get("query_pages", []):
        landing.setdefault(row["query"], row["page"])

    ranked = sorted((q["impressions"] for q in queries), reverse=True)
    bar = max(MIN_FLOOR, ranked[min(int(len(ranked) * TOP_SHARE), len(ranked) - 1)])

    proposals = []
    for q in queries:
        text, imp, pos = q["query"], q["impressions"], q["position"]
        if imp < bar or blocked(text) or noise(text):
            continue

        qt = tokens(text)
        if not qt:
            continue

        best_slug, best_overlap = None, 0.0
        for slug, pt in covered:
            overlap = len(qt & pt) / len(qt)
            if overlap > best_overlap:
                best_slug, best_overlap = slug, overlap

        if best_overlap >= COVERED_OVERLAP:
            continue                                   # we already have this post

        slugified = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
        if any(slugified in s or s in slugified for s in queued):
            continue                                   # already waiting in the queue

        # An orphan is a query the site already earns impressions for through a
        # page that is not about it — the strongest signal there is. A landing
        # page proves that directly; token overlap is the weaker fallback.
        kind = "ORPHAN" if (text in landing or best_overlap > 0.2) else "NEW"
        if STRIKING_LOW <= pos <= STRIKING_HIGH:
            kind += "/STRIKING"

        # Impressions matter, and so does being close enough to act on.
        score = imp * (2.0 if STRIKING_LOW <= pos <= STRIKING_HIGH else 1.0)
        proposals.append({
            "query": text, "impressions": imp, "clicks": q["clicks"],
            "position": pos, "kind": kind, "score": score,
            "nearest": best_slug, "overlap": round(best_overlap, 2),
            "landing": landing.get(text, ""),
        })

    proposals.sort(key=lambda p: -p["score"])

    if not proposals:
        print(f"  {len(queries)} queries in the window, none above the bar")
        print(f"  (min {bar} impressions, not already covered, not blocked).")
        return

    print(f"  {len(proposals)} topic opportunities from {len(queries)} queries "
          f"({data['start']} to {data['end']})\n")
    for p in proposals[:TOP_N]:
        print(f"  [{p['kind']:15}] {p['query']}")
        print(f"    {p['impressions']:>5} impressions, {p['clicks']:>3} clicks, "
              f"position {p['position']}")
        if p["nearest"]:
            print(f"    closest existing post: {p['nearest']} (overlap {p['overlap']})")
        print()

    print("  These are candidates, not decisions. Each must still clear the five")
    print("  criteria in WRITING-LOOP.md before it goes in the queue.")


if __name__ == "__main__":
    main()
