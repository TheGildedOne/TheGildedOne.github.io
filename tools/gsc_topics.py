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
STORE = ROOT / "content" / "search-data.json"
QUEUE = ROOT / "content" / "queue.json"

sys.path.insert(0, str(ROOT))
import build  # noqa: E402

# --- tunables -------------------------------------------------------------
# Defaults set blind, before any real data existed. Revisit once there are a
# few months of history — these numbers are guesses, the logic around them is not.
MIN_IMPRESSIONS = 30        # below this, a query is noise
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


def main():
    if not STORE.exists():
        print("  No content/search-data.json — run tools/gsc_pull.py first.")
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

    proposals = []
    for q in queries:
        text, imp, pos = q["query"], q["impressions"], q["position"]
        if imp < MIN_IMPRESSIONS or blocked(text):
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
        print(f"  (min {MIN_IMPRESSIONS} impressions, not already covered, not blocked).")
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
