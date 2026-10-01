#!/usr/bin/env python3
"""Does anybody actually type this phrase into Google?

A post's `focus_keyword` and `seo_title` are a bet on what people search for.
Until 2026-10-01 nothing tested the bet, and it went wrong quietly. The first 24
posts targeted real phrases ("eleusinian mysteries", "piacenza liver"). From the
25th on, the keywords became three topics glued together ("palladium rome vesta",
"cumaean sibyl cave cumae"), which nobody types, and 23 of the next 29 posts were
titled around them. The subjects were fine. The Cumaean Sibyl has plenty of
searchers; the title just never said "Cumaean Sibyl" the way they do.

The test is Google's own autocomplete. It completes phrases people really type,
so a phrase it knows is one with searchers, and a phrase it returns nothing for
is one almost nobody uses. This is a yes/no signal, not a volume figure: it
cannot tell 50 searches a month from 50,000. It is free, needs no account, and
is far better than guessing.

  python tools/keyword_demand.py "oracle of dodona" "dodona oracle lead tablets"
  python tools/keyword_demand.py --queue        # every pending queue entry
  python tools/keyword_demand.py --scheduled    # every post not yet published

Three answers, and the third is not the second:

  YES          Google completes it. Fine to target.
  no           Google answered and does not know the phrase. Find the phrase
               people do use (the suggestions printed for a shorter version are
               the place to look) before writing a title around this one.
  UNREACHABLE  The lookup failed. That says nothing about the phrase; run it again.

Always exits 0. It informs a choice, it does not gate a build.
"""

import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
ENDPOINT = "https://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q="


def suggestions(phrase: str):
    """Google's completions for a phrase, or None if the lookup itself failed."""
    req = urllib.request.Request(ENDPOINT + urllib.parse.quote(phrase),
                                 headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode("utf-8", errors="replace"))[1]
        except Exception:
            time.sleep(1 + attempt)
    return None


def known(phrase: str, found: list) -> bool:
    """True if Google completes the phrase itself, not merely something nearby."""
    p = phrase.lower().strip()
    return any(s.lower().startswith(p) for s in found)


def report(label: str, phrase: str) -> str:
    found = suggestions(phrase)
    time.sleep(0.4)                      # be polite; this is an unofficial endpoint
    if found is None:
        verdict = "UNREACHABLE"
    else:
        verdict = "YES" if known(phrase, found) else "no"
    shown = ", ".join(found[:4]) if found else ""
    print(f"  {verdict:<11} {phrase}")
    if label:
        print(f"              {label}")
    if shown:
        print(f"              Google suggests: {shown}")
    return verdict


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    checks = [("", a) for a in args]

    if "--queue" in sys.argv:
        queue = json.loads((ROOT / "content" / "queue.json").read_text(encoding="utf-8"))
        checks += [(f"queue: {e['slug']}", e["keyword"])
                   for e in queue["posts"] if e.get("status") == "pending"]

    if "--scheduled" in sys.argv:
        sys.path.insert(0, str(ROOT))
        import build
        checks += [(f"{p['dt']:%d %b}: {p['slug']}", p["focus_keyword"])
                   for p in build.load_posts() if p["dt"] > datetime.now()]

    if not checks:
        print(__doc__)
        return

    verdicts = [report(label, phrase) for label, phrase in checks]
    yes, no, down = (verdicts.count(v) for v in ("YES", "no", "UNREACHABLE"))
    print(f"\n  {yes} of {len(verdicts)} are phrases people type; {no} are not"
          + (f"; {down} could not be checked, run again" if down else "") + ".")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:               # advisory tool: never break a writing run
        print(f"  keyword check skipped: {e}")
    sys.exit(0)
