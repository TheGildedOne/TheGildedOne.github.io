#!/usr/bin/env python3
"""Which existing page to improve this week, and whether past changes worked.

The other half of the feedback loop. gsc_topics.py asks "what new post should
we write?"; this asks the cheaper question for a site this size: which page is
already close to page one, and what are people typing to find it?

It also closes the loop. Every change the writing run makes to a live page is
logged in seo-log.json (via `python tools/seo_data.py log`). This compares each
logged page's 28 days before the change with the 28 days starting a month after
it, using the dated snapshots gsc_pull.py keeps, and says whether it helped.
Without that, a tweak that does nothing looks exactly like one that worked.

Runs weekly on GitHub in the private data repo, after gsc_pull.py. Reads only
from VA_DATA_DIR; prints a report and writes nothing.

  python tools/seo_review.py
"""

import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import gsc_pull  # noqa: E402
import gsc_topics  # noqa: E402

DATA = gsc_pull.DATA_DIR
SITE = "https://veiledantiquity.com"

# A page in this band is on page one's doorstep or the top of page two. Above
# it there is little to gain; below it a snippet tweak will not be enough.
BAND_LOW, BAND_HIGH = 4.0, 20.0
MIN_IMPRESSIONS = 5       # fewer than this in 90 days and the position is noise
SHOW = 5
# A page changed recently is left alone until its result is in, so two changes
# never blur into one measurement.
REST_DAYS = 42
# The "after" window starts a month on, so it holds no days from before the change.
SETTLE_DAYS = 30
# Below this many impressions in both windows, a difference is chance, not a result.
JUDGE_MIN = 20


def clean(url):
    """Every address Google shows for a page, folded onto the real one."""
    url = url.split("?", 1)[0].split("#", 1)[0]
    return url if url.endswith("/") else url + "/"


def slug_of(url):
    path = clean(url).replace(SITE, "")
    return path.strip("/").split("/")[-1] if path.startswith("/posts/") else path


def fold(rows):
    """{clean url: {clicks, impressions, position}} with the position weighted by impressions."""
    out = {}
    for r in rows:
        p = out.setdefault(clean(r["page"]), {"clicks": 0, "impressions": 0, "_w": 0.0})
        p["clicks"] += r["clicks"]
        p["impressions"] += r["impressions"]
        p["_w"] += r["position"] * r["impressions"]
    for p in out.values():
        p["position"] = round(p.pop("_w") / p["impressions"], 1) if p["impressions"] else 0.0
    return out


def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def snapshots():
    folder = DATA / "snapshots"
    snaps = []
    for f in sorted(folder.glob("*.json")) if folder.exists() else []:
        s = load(f, None)
        if s and "recent" in s:          # the oldest copies predate the 28-day window
            snaps.append((date.fromisoformat(s["pulled"]), s))
    return snaps


def trend(snaps):
    print("  WEEKLY TREND (last 28 days, as of each pull)")
    if not snaps:
        print("    No weekly snapshots yet. The first lands with the next weekly run.")
        return
    for d, s in snaps[-8:]:
        t = s["recent"]["totals"]
        print(f"    {d}  {t['clicks']:>4} clicks  {t['impressions']:>6} impressions")


def candidates(data, log):
    pages = fold(data.get("pages", []))
    rested = {e["page"] for e in log
              if date.fromisoformat(e["date"]) > date.today() - timedelta(days=REST_DAYS)}

    # The same query often shows on a page's real and tracking-tagged addresses;
    # fold those together so it is listed once with its full count.
    queries = {}
    for r in data.get("query_pages", []):
        if gsc_topics.noise(r["query"]):
            continue
        q = queries.setdefault(clean(r["page"]), {}).setdefault(
            r["query"], {"query": r["query"], "impressions": 0, "position": r["position"]})
        q["impressions"] += r["impressions"]
        q["position"] = min(q["position"], r["position"])

    picks = []
    for url, p in pages.items():
        slug = slug_of(url)
        if "/posts/" not in url or slug in rested or p["impressions"] < MIN_IMPRESSIONS:
            continue
        if BAND_LOW <= p["position"] <= BAND_HIGH:
            reason = "close to page one"
        elif p["position"] < BAND_LOW and p["impressions"] >= 20 and p["clicks"] == 0:
            reason = "seen near the top but nobody clicks: the snippet is the problem"
        else:
            continue
        picks.append((p["impressions"] / max(p["position"], 1.0), slug, p, reason,
                      sorted(queries.get(url, {}).values(), key=lambda q: -q["impressions"])[:3]))

    print("\n  PAGES TO IMPROVE (best first; pick the top one)")
    if not picks:
        print("    None qualify this week.")
        return
    for _, slug, p, reason, top in sorted(picks, key=lambda x: -x[0])[:SHOW]:
        print(f"    {slug}")
        print(f"      {p['impressions']} impressions, {p['clicks']} clicks, "
              f"position {p['position']} over 90 days. {reason}")
        for q in top:
            print(f"      people typed: \"{q['query']}\" ({q['impressions']} impr., pos {q['position']})")
        if not top:
            print("      Google withheld the queries (too rare to name); work from the page's subject.")


def results(snaps, log):
    print("\n  RESULTS OF EARLIER CHANGES")
    if not log:
        print("    Nothing logged yet.")
        return

    def window(when, after):
        """The page numbers from the snapshot that covers the right 28 days."""
        if after:
            later = [s for d, s in snaps if d >= when + timedelta(days=SETTLE_DAYS)]
            return later[0] if later else None
        earlier = [s for d, s in snaps if d <= when]
        return earlier[-1] if earlier else None

    for e in log:
        when = date.fromisoformat(e["date"])
        url = f"{SITE}/posts/{e['page']}/"
        print(f"    {e['date']}  {e['page']}: {e['change']}")
        before, after = window(when, False), window(when, True)
        if before is None:
            print("      no snapshot from before the change, so it cannot be judged")
            continue
        if after is None:
            print(f"      result due from {when + timedelta(days=SETTLE_DAYS)}")
            continue
        b = fold(before["recent"]["pages"]).get(url, {"clicks": 0, "impressions": 0, "position": 0})
        a = fold(after["recent"]["pages"]).get(url, {"clicks": 0, "impressions": 0, "position": 0})
        print(f"      before: {b['impressions']} impr., {b['clicks']} clicks, pos {b['position']}"
              f"   after: {a['impressions']} impr., {a['clicks']} clicks, pos {a['position']}")
        if max(a["impressions"], b["impressions"]) < JUDGE_MIN:
            verdict = "too little traffic to judge"
        elif a["clicks"] > b["clicks"] or a["impressions"] > b["impressions"] * 1.2:
            verdict = "HELPED"
        elif a["impressions"] < b["impressions"] * 0.8:
            verdict = "HURT"
        else:
            verdict = "no clear change"
        print(f"      verdict: {verdict}")


def main():
    data = load(DATA / "search-data.json", {})
    log = load(DATA / "seo-log.json", {}).get("entries", [])
    snaps = snapshots()
    if not data.get("pages"):
        print("  No page-level data yet. It arrives with the next weekly pull.")
    trend(snaps)
    if data.get("pages"):
        candidates(data, log)
    results(snaps, log)


if __name__ == "__main__":
    main()
