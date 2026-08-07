#!/usr/bin/env python3
"""Check that every modern book cited in the posts actually exists.

A fabricated citation is the one failure that would sink this site, and it is
exactly the failure an LLM is prone to. This queries Open Library for each
modern scholarly book and reports anything it cannot confirm.

Deliberately NOT checked, because Open Library is the wrong instrument:
  - classical authors (Livy 39.8, Pausanias 1.38) — stable citations, not catalogue entries
  - journal articles — the italicised part is the journal, not a book
  - inscriptions, papyri and objects (CIL, PGM, the Piacenza Liver)

Run:  python tools/verify_sources.py
Exit 1 if a book cannot be confirmed, so it can gate an automated commit.
"""

import difflib
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import build  # noqa: E402

API = "https://openlibrary.org/search.json"
UA = "VeiledAntiquity-CitationCheck/1.0 (https://veiledantiquity.com)"
MATCH = 0.72

ANCIENT = {
    "livy", "pausanias", "herodotus", "homer", "cicero", "pliny", "plato",
    "suetonius", "apuleius", "thucydides", "strabo", "eunapius", "porphyry",
    "clement", "hippolytus", "dionysius", "aulus gellius", "cassius dio",
    "ammianus", "martianus capella", "rutilius namatianus", "seneca", "varro",
    "aristotle", "plutarch", "virgil", "horace", "ovid",
}

# Entries naming a physical object or document rather than a publication.
OBJECT_HINTS = ("CIL", "Papyrus", "papyrus", "Papyri Graecae", "tablet", "Tablet",
                "Liber Linteus", "mosaic", "Tondo", "Arch of", "PGM", "P. Oxy")

TITLE_RE = re.compile(r"<em>(.*?)</em>", re.DOTALL)
ARTICLE_RE = re.compile(r"&lsquo;.*?&rsquo;")          # 'Article Title', Journal 12 (1999)
ABBREV_RE = re.compile(r"^[A-Z]{2,6}$")                # JRS, AHR, PAPS


def clean(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def classify(entry, title):
    """book | ancient | journal | object — only 'book' is checkable here."""
    head = clean(entry).split(",")[0].lower()
    if any(a in head for a in ANCIENT):
        return "ancient"
    if ARTICLE_RE.search(entry) or ABBREV_RE.match(title):
        return "journal"
    if any(h in entry for h in OBJECT_HINTS) and "(" not in entry.split("&mdash;")[0]:
        return "object"
    # A journal cited as "<em>Name</em> n.s. 4 (2000)" has no publisher parenthesis.
    if re.search(r"</em>\s*(n\.s\.\s*)?\d+\s*\(\d{4}\)", entry):
        return "journal"
    return "book"


def similarity(a, b):
    a, b = a.lower().strip(), b.lower().strip()
    if not a or not b:
        return 0.0
    # Subtitles vary between editions and catalogues; containment counts as a hit.
    if a in b or b in a:
        return 1.0
    # Compare main titles either side of a colon.
    a_main, b_main = a.split(":")[0].strip(), b.split(":")[0].strip()
    if a_main and (a_main in b_main or b_main in a_main):
        return 0.95
    return difflib.SequenceMatcher(None, a, b).ratio()


def query(params):
    params.update({"limit": "8", "fields": "title,author_name,first_publish_year"})
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params),
                                 headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r).get("docs", []), None
    except Exception as e:
        return [], str(e)


def best_match(title, surname):
    """Try author+title, then title alone — Open Library's author index is patchy."""
    best, err = 0.0, None
    for params in ({"title": title, "author": surname} if surname else None, {"q": title}):
        if not params:
            continue
        docs, e = query(params)
        if e:
            err = e
            continue
        for d in docs:
            best = max(best, similarity(title, d.get("title") or ""))
        time.sleep(0.6)
        if best >= MATCH:
            break
    return best, err


def main():
    posts = build.load_posts()
    unconfirmed = []
    counts = {"book": 0, "ancient": 0, "journal": 0, "object": 0}

    for p in posts:
        for entry in p.get("sources", []):
            m = TITLE_RE.search(entry)
            if not m:
                continue
            title = clean(m.group(1))
            kind = classify(entry, title)
            counts[kind] += 1
            if kind != "book":
                continue

            author = re.sub(r"\((ed|eds|trans)\.?\)", "", clean(entry).split(",")[0], flags=re.I)
            surname = author.strip().split()[-1] if author.strip() else ""

            score, err = best_match(title, surname)
            if err and score < MATCH:
                print(f"  !!    {title[:56]:58} lookup failed")
                unconfirmed.append((p["slug"], title, f"lookup failed: {err}"))
            elif score >= MATCH:
                print(f"  ok    {title[:56]:58} ({score:.2f})")
            else:
                print(f"  ????  {title[:56]:58} ({score:.2f})")
                unconfirmed.append((p["slug"], title, f"best match {score:.2f}"))

    print(f"\n  books checked: {counts['book']}   "
          f"skipped — ancient: {counts['ancient']}, journal: {counts['journal']}, "
          f"object: {counts['object']}")

    if unconfirmed:
        print(f"\n  {len(unconfirmed)} UNCONFIRMED — check by hand before publishing:")
        for slug, title, why in unconfirmed:
            print(f"    - [{slug}] {title}  ({why})")
        sys.exit(1)
    print("  Every book citation resolved.")


if __name__ == "__main__":
    main()
