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
    # Greek and Latin authors cited by book and section rather than by edition.
    # Open Library is the wrong instrument for these — an entry may or may not
    # exist for a given translation, so a miss says nothing about the citation.
    # Add to this list whenever a post cites an ancient author not already here.
    "livy", "pausanias", "herodotus", "homer", "cicero", "pliny", "plato",
    "suetonius", "apuleius", "thucydides", "strabo", "eunapius", "porphyry",
    "clement", "hippolytus", "dionysius", "aulus gellius", "cassius dio",
    "ammianus", "martianus capella", "rutilius namatianus", "seneca", "varro",
    "aristotle", "plutarch", "virgil", "horace", "ovid",
    "galen", "tertullian", "josephus", "flavius josephus", "valerius maximus",
    "diodorus", "jerome", "origen", "tacitus", "xenophon", "lucian", "arrian",
    "polybius", "quintilian", "martial", "juvenal", "lucretius", "celsus",
    "vitruvius", "macrobius", "festus", "servius", "athenaeus", "philostratus",
    "euripides", "sophocles", "aeschylus", "aristophanes", "pindar", "hesiod",
    "propertius", "tibullus", "columella", "cato", "sallust", "curtius",
    "aelian", "artemidorus", "iamblichus", "proclus", "libanius", "julian",
    "augustine", "lactantius", "eusebius", "zosimus", "procopius",
    "aelius aristides", "aristides", "diodorus siculus", "persius",
}

# Real books that Open Library simply does not hold. Each was confirmed against
# another catalogue; the note records how, so a later run does not "fix" the
# citation by deleting it. Only add an entry after checking the book yourself.
VERIFIED_BY_HAND = {
    "The Epidaurian Miracle Inscriptions: Text, Translation, and Commentary":
        "Lynn R. LiDonnici, Scholars Press, Atlanta 1995, ISBN 0-7885-0130-8 "
        "(Texts and Translations 36). Confirmed via Internet Archive and a 1997 "
        "review in the Journal for the Study of the New Testament. Checked 2026-08-10.",
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
    """One Open Library search, retried through transient network failures.

    Without the retry, Open Library timing out looks exactly like a citation that
    does not exist. Two runs of this script produced two different sets of
    'unconfirmed' titles, several of which had resolved cleanly minutes earlier —
    which is how a real fabrication could hide in the noise.
    """
    params.update({"limit": "8", "fields": "title,author_name,first_publish_year"})
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params),
                                 headers={"User-Agent": UA})
    err = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r).get("docs", []), None
        except Exception as e:
            err = str(e)
            if attempt < 2:
                time.sleep(4 * (attempt + 1))
    return [], err


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
    missing, unreachable = [], []
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

            if title in VERIFIED_BY_HAND:
                print(f"  hand  {title[:56]:58} verified offline")
                continue

            score, err = best_match(title, surname)
            if score >= MATCH:
                print(f"  ok    {title[:56]:58} ({score:.2f})")
            elif err:
                # Could not ask. Says nothing about the citation either way.
                print(f"  net   {title[:56]:58} unreachable")
                unreachable.append((p["slug"], title, err.split(":")[-1].strip()[:60]))
            else:
                # Open Library answered and had nothing close. This is the one
                # that might be an invented book.
                print(f"  ????  {title[:56]:58} ({score:.2f})")
                missing.append((p["slug"], title, f"best match {score:.2f}"))

    print(f"\n  books checked: {counts['book']}   "
          f"skipped — ancient: {counts['ancient']}, journal: {counts['journal']}, "
          f"object: {counts['object']}")

    if missing:
        print(f"\n  {len(missing)} NOT FOUND — Open Library answered and had no such book.")
        print("  Treat each as a possible fabrication. Confirm by hand or remove it.")
        for slug, title, why in missing:
            print(f"    - [{slug}] {title}  ({why})")

    if unreachable:
        print(f"\n  {len(unreachable)} UNREACHABLE — the lookup failed after 3 tries.")
        print("  This is a network result, not a verdict. Re-run before drawing conclusions.")
        for slug, title, why in unreachable:
            print(f"    - [{slug}] {title}  ({why})")

    if missing or unreachable:
        sys.exit(1)
    print("  Every book citation resolved.")


if __name__ == "__main__":
    main()
