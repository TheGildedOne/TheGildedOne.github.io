#!/usr/bin/env python3
"""Check that every modern book cited in the posts actually exists.

A fabricated citation is the one failure that would sink this site, and it is
exactly the failure an LLM is prone to. This queries Open Library for each
modern scholarly book and reports anything it cannot confirm.

Modern books go to Open Library. Journal articles go to Crossref, falling back to
OpenAlex: a plausible article title, journal and year is trivially invented and
impossible to catch by reading, so leaving those unchecked was the bigger hole.

Deliberately NOT checked, because no catalogue is the right instrument:
  - classical authors (Livy 39.8, Pausanias 1.38) — stable citations, not catalogue entries
  - a journal named with no article title — nothing falsifiable to look up
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
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import build  # noqa: E402

API = "https://openlibrary.org/search.json"
UA = ("VeiledAntiquity-CitationCheck/1.0 (https://veiledantiquity.com; "
      "mailto:hello@veiledantiquity.com)")   # mailto = Crossref polite pool
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
    "augustine", "lactantius", "eusebius", "zosimus", "procopius", "arnobius",
    "aelius aristides", "aristides", "diodorus siculus", "persius",
    "petronius",
}

# Real works the catalogues simply do not hold: Open Library for books, Crossref
# and OpenAlex for articles. Book chapters and pre-1990 European journals are the
# usual gaps. Each was confirmed elsewhere and the note records how, so a later
# run does not "fix" the citation by deleting it. Only add an entry after
# checking the work yourself.
#
# If the book has an ISBN that Open Library holds, it does not belong here: put
# it in ISBN_FOR below and let the script check it. Any ISBN quoted in a note
# here must at least have a valid check digit, and main() refuses to run if one
# does not.
VERIFIED_BY_HAND = {
    "The Curse Tablets":
        "R. S. O. Tomlin, chapter 4 of B. Cunliffe (ed.), 'The Temple of Sulis "
        "Minerva at Bath, II: Finds from the Sacred Spring' (Oxford University "
        "Committee for Archaeology monograph 16, 1988). A book chapter, which "
        "Crossref indexes poorly. Confirmed via a Journal of Roman Archaeology "
        "review of the volume. Checked 2026-08-15.",
    "Invida rumpantur pectora: The Iconography of Phthonos/Invidia in Graeco-Roman Art":
        "K. M. D. Dunbabin and M. W. Dickie, Jahrbuch fuer Antike und Christentum "
        "26 (1983) 7-37. Pre-digital German journal, absent from Crossref and "
        "OpenAlex. Confirmed via the Doelger-Institut's own JbAC contents index "
        "and the DAI Zenon catalogue. Checked 2026-08-15.",
    "Mixing the Kykeon":
        "P. Webster, D. M. Perrine and C. A. P. Ruck, ELEUSIS: Journal of "
        "Psychoactive Plants and Compounds, New Series 4 (2000). A small "
        "specialist journal that Crossref indexes erratically: the same title "
        "scored 1.00 on one run and 0.33 on the next, because a three-word title "
        "is fragile against fuzzy search. Confirmed via Academia.edu and "
        "ResearchGate copies. Checked 2026-08-22.",
    "Cursing Chariot Horses instead of Drivers in the Hippodromes of the Eastern Roman Empire":
        "Christopher Faraone, in C. Sanchez-Natalias (ed.), Litterae Magicae: "
        "Studies in Honor of Roger S.O. Tomlin (Zaragoza, 2019), 83-101. A "
        "conference-volume chapter published in Spain, which Crossref indexes "
        "poorly. Chapter confirmed via Faraone's own posting of it, which gives "
        "the page range as 83-101; the volume (Supplementa MHNH 2, Libros "
        "Portico, ISBN 978-84-7956-183-3) runs to 262pp. NOTE: an earlier version "
        "of this entry said 165-186 and claimed the CV confirmed that range. It "
        "did not. Corrected 2026-08-22 - check page numbers on anything added "
        "here, the note is written by the same run that adds the citation.",
    "Une nouvelle tablette magique d'Égypte. Musée du Louvre, Inv. E 27145":
        "Sophie Kambitsis, Bulletin de l'Institut francais d'archeologie "
        "orientale (BIFAO) 76 (1976), 213-223. A pre-1990 French Egyptology "
        "journal, absent from Crossref and OpenAlex. Confirmed via its "
        "Semantic Scholar record and a WorldCat/BnF catalogue entry, both "
        "giving the same journal, volume and page range. Checked 2026-08-22.",
    "Ritual Hexameters in the Getty Museum: Preliminary Edition":
        "David R. Jordan and Roy D. Kotansky, Zeitschrift fuer Papyrologie und "
        "Epigraphik 178 (2011), 54-62. ZPE is not in Crossref or OpenAlex. Not "
        "read directly. Volume and page range confirmed from three independent "
        "citations that agree: the bibliography of Janko, ZPE 193 (2015) 1-10 "
        "(read as PDF from the author's Michigan page), Battezzato, Cambridge "
        "Classical Journal 68 (2022), and Kotansky's own Oxford Classical "
        "Dictionary entry. Checked 2026-10-03.",
    "Die Beichtinschriften Westkleinasiens":
        "Georg Petzl, Epigraphica Anatolica 22, Rudolf Habelt, Bonn 1994, "
        "ISBN 3-7749-2653-0. A whole journal volume issued as a monograph; "
        "absent from Open Library (0.00, and no hit on the ISBN). Not read "
        "directly. Confirmed via WorldCat (OCLC 31675143) and a review in "
        "L'Antiquite Classique 65 (1996) on Persee, which gives the count of "
        "124 texts used in the post. Cited as a whole volume, no pages. "
        "Checked 2026-10-03.",
}

# Books the title search misses but Open Library does hold. Give the ISBN and
# this script looks it up itself, and passes the citation only if the record that
# comes back carries the cited title.
#
# This exists to shrink VERIFIED_BY_HAND, which is the gate's blind spot: an
# entry there is believed on the word of a note written by the same run that
# added the citation, and one of those notes has already been wrong. By
# 2026-10-03 eight of its sixteen entries were books Open Library held all
# along. The title search had missed them (a long subtitle, a French title,
# quotation marks in the title), each note said "confirmed by ISBN", and
# nothing checked that it had been. Now something does.
#
# A book belongs here, not in VERIFIED_BY_HAND, whenever Open Library has a
# record for its ISBN. VERIFIED_BY_HAND is for what no catalogue holds.
ISBN_FOR = {
    # The first entry VERIFIED_BY_HAND ever had, from 2026-08-10, and its note was
    # wrong twice: it gave the ISBN as 0-7885-0130-8, which fails its own check
    # digit, and said Open Library lacked the book, which it holds under this one.
    # Nobody could have caught either by reading the note. Found 2026-10-03.
    "The Epidaurian Miracle Inscriptions: Text, Translation, and Commentary": "0-7885-0104-6",
    "Litterae Magicae: Studies in Honor of Roger S.O. Tomlin": "978-84-7956-183-3",
    "Trophonios de Lébadée: Cultes et mythes d'une cité béotienne au miroir de la mentalité antique":
        "90-04-13102-7",
    "Greco-Roman Associations: Texts, Translations, and Commentary I: Attica, Central Greece, Macedonia, Thrace":
        "978-3-11-025345-0",
    "Magic in Apuleius' ‘Apologia’: Understanding the Charges and the "
    "Forensic Strategies in Apuleius' Speech": "978-3-11-061659-0",
    "Corpus Cultus Iovis Sabazii, Volume I: The Hands": "90-04-06951-8",
    "Corpus Cultus Iovis Sabazii, Volume III: Conclusions": "90-04-08974-8",
    "The Materiality of Magic": "978-3-7705-5725-7",
    "The Getty Hexameters: Poetry, Magic, and Mystery in Ancient Selinous": "978-0-19-966410-8",
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
    """book | ancient | journal | object — only 'book' is checkable here.

    Two things here were wrong until 2026-09-02, and both let real books through
    unverified, which is the exact failure this script exists to prevent.

    1. A quoted title was treated as proof of a journal article wherever it
       appeared in the entry. But the annotation after the em dash often quotes
       something too, so Edmonds' *Myths of the Underworld Journey* was skipped
       because its note mentions the 'Orphic' label, and Gruen's *Studies in Greek
       Culture and Roman Policy* was skipped because the entry names its chapter.
       Only a quoted title BEFORE the <em> says anything about the type.

    2. A chapter in an edited volume ("'Chapter', in Ed. (ed.), <em>Volume</em>")
       was filed as a journal, so the volume was never checked. The italicised
       part there is a book and is exactly as fabricable as any other.
    """
    head = clean(entry).split(",")[0].lower()
    if any(a in head for a in ANCIENT):
        return "ancient"
    if ABBREV_RE.match(title):
        return "journal"
    # A journal cited as "<em>Name</em> 12 (1999)" or "<em>Name</em> n.s. 4 (2000)".
    if re.search(r"</em>\s*(n\.s\.\s*)?\d+\s*\(\d{4}\)", entry):
        return "journal"

    em = entry.find("<em>")
    if em != -1 and ARTICLE_RE.search(entry[:em]):
        before = entry[:em]
        # "…, in Cunliffe (ed.), <em>Book</em>" or "…, in <em>Magika Hiera</em>".
        if "(ed" in before or re.search(r",\s*in\s*$", before):
            return "book"
        return "journal"

    if any(h in entry for h in OBJECT_HINTS) and "(" not in entry.split("&mdash;")[0]:
        return "object"
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


# ---- books by ISBN ----------------------------------------------------------
ISBN_API = "https://openlibrary.org/isbn/{}.json"


def isbn_valid(isbn):
    """True if the check digit is right. Catches a mistyped ISBN before it is
    mistaken for a book the catalogue lacks."""
    d = re.sub(r"[\s-]", "", isbn).upper()
    if len(d) == 10 and re.fullmatch(r"\d{9}[\dX]", d):
        return sum((10 - i) * (10 if c == "X" else int(c)) for i, c in enumerate(d)) % 11 == 0
    if len(d) == 13 and d.isdigit():
        return sum(int(c) * (3 if i % 2 else 1) for i, c in enumerate(d)) % 10 == 0
    return False


def _words(s):
    """Lower-case words with accents and punctuation stripped, short ones dropped."""
    import unicodedata
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return [w for w in re.sub(r"[^a-z0-9]+", " ", s.lower()).split() if len(w) > 2]


def isbn_match(title, isbn):
    """(score, error, what the catalogue calls it) for one ISBN at Open Library.

    A 404 is an answer, "no such record", and comes back as score 0 with no
    error. Anything else that stops us asking is an error, and says nothing
    about the book. Same distinction as everywhere else in this file."""
    if not isbn_valid(isbn):
        return 0.0, None, "the ISBN's check digit is wrong, so it was mistyped"
    req = urllib.request.Request(ISBN_API.format(re.sub(r"[\s-]", "", isbn)),
                                 headers={"User-Agent": UA})
    record, err = None, None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                record, err = json.load(r), None
                break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return 0.0, None, "Open Library has no record of that ISBN"
            err = str(e)
        except Exception as e:
            err = str(e)
        if attempt < 2:
            time.sleep(4 * (attempt + 1))
    if record is None:
        return 0.0, err, ""

    found = (record.get("title") or "").strip()
    full = f"{found}: {record.get('subtitle')}" if record.get("subtitle") else found
    score = max(similarity(title, found), similarity(title, full))
    # Catalogue titles are messy ("Corpus Cultus Lovis Sabazii"), so also count
    # how many of the catalogue's words the cited title contains. Needs three
    # words to count at all: a one-word catalogue title would match anything.
    theirs, ours = _words(found), set(_words(title))
    if len(theirs) >= 3:
        score = max(score, sum(w in ours for w in theirs) / len(theirs))
    return score, None, f"that ISBN is '{found}' at Open Library, not this title"


# ---- journal articles -------------------------------------------------------
# Books go to Open Library; that leaves journal articles unchecked, which is the
# larger fabrication risk because a plausible-looking article title, journal and
# year is trivial to invent and impossible to spot by reading. Crossref indexes
# most of the literature including small open-access classics journals, and
# OpenAlex covers some of what it misses. Both are free and need no key.
CROSSREF = "https://api.crossref.org/works"
OPENALEX = "https://api.openalex.org/works"
ARTICLE_TITLE_RE = re.compile(r"&lsquo;(.*?)&rsquo;", re.DOTALL)


def _fetch(url, params):
    req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params),
                                 headers={"User-Agent": UA})
    err = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r), None
        except Exception as e:
            err = str(e)
            if attempt < 2:
                time.sleep(4 * (attempt + 1))
    return None, err


def best_article_match(title):
    """Highest title similarity for an article, via Crossref then OpenAlex."""
    best, err = 0.0, None

    data, e = _fetch(CROSSREF, {"query.bibliographic": title, "rows": "5",
                                "select": "title"})
    if e:
        err = e
    elif data:
        for item in data.get("message", {}).get("items", []):
            for t in (item.get("title") or []):
                best = max(best, similarity(title, t))
    if best >= MATCH:
        return best, None

    time.sleep(0.6)
    data, e = _fetch(OPENALEX, {"search": title, "per_page": "5",
                                "select": "display_name"})
    if e:
        err = err or e
    elif data:
        for item in data.get("results", []):
            best = max(best, similarity(title, item.get("display_name") or ""))
    return best, (err if best < MATCH else None)


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
    counts = {"book": 0, "ancient": 0, "journal": 0, "object": 0, "article": 0, "isbn": 0}

    # A book in both lists would be waved through by the note and never looked
    # up, which defeats the point of having given its ISBN.
    both = sorted(set(ISBN_FOR) & set(VERIFIED_BY_HAND))
    if both:
        print("  In both ISBN_FOR and VERIFIED_BY_HAND; remove from VERIFIED_BY_HAND:")
        for t in both:
            print(f"    - {t}")
        sys.exit(1)

    # The notes are taken on trust, but an ISBN in one can still be checked for
    # being a real ISBN at all. Needs no network.
    bad = [(t, i) for t, note in VERIFIED_BY_HAND.items()
           for i in re.findall(r"ISBN\s+([\dXx][\dXx -]{8,16}[\dXx])", note) if not isbn_valid(i)]
    if bad:
        print("  ISBN with a wrong check digit in a VERIFIED_BY_HAND note (mistyped,")
        print("  or never looked up). Correct it before trusting the entry:")
        for t, i in bad:
            print(f"    - {i}  in the note for: {t}")
        sys.exit(1)

    for p in posts:
        for entry in p.get("sources", []):
            m = TITLE_RE.search(entry)
            if not m:
                continue
            title = clean(m.group(1))
            kind = classify(entry, title)
            counts[kind] += 1

            if kind == "journal":
                # Only a quoted article title is a checkable claim. A bare
                # journal name with a volume number is not, so leave those.
                am = ARTICLE_TITLE_RE.search(entry)
                if not am:
                    continue
                atitle = clean(am.group(1))
                counts["article"] += 1
                if atitle in VERIFIED_BY_HAND:
                    print(f"  hand  {atitle[:56]:58} verified offline")
                    continue
                score, err = best_article_match(atitle)
                if score >= MATCH:
                    print(f"  ok    {atitle[:56]:58} ({score:.2f}) article")
                elif err:
                    print(f"  net   {atitle[:56]:58} unreachable")
                    unreachable.append((p["slug"], atitle, err.split(":")[-1].strip()[:60]))
                else:
                    print(f"  ????  {atitle[:56]:58} ({score:.2f}) article")
                    missing.append((p["slug"], atitle, f"no article match {score:.2f}"))
                continue

            if kind != "book":
                continue

            author = re.sub(r"\((ed|eds|trans)\.?\)", "", clean(entry).split(",")[0], flags=re.I)
            surname = author.strip().split()[-1] if author.strip() else ""

            if title in VERIFIED_BY_HAND:
                print(f"  hand  {title[:56]:58} verified offline")
                continue

            if title in ISBN_FOR:
                counts["isbn"] += 1
                score, err, why = isbn_match(title, ISBN_FOR[title])
                time.sleep(0.6)
                if score >= MATCH:
                    print(f"  isbn  {title[:56]:58} ({score:.2f}) {ISBN_FOR[title]}")
                elif err:
                    print(f"  net   {title[:56]:58} unreachable")
                    unreachable.append((p["slug"], title, err.split(":")[-1].strip()[:60]))
                else:
                    print(f"  ????  {title[:56]:58} ({score:.2f}) isbn")
                    missing.append((p["slug"], title, f"ISBN {ISBN_FOR[title]}: {why}"))
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

    print(f"\n  books checked: {counts['book']} ({counts['isbn']} by ISBN)   "
          f"articles checked: {counts['article']}   "
          f"taken on a note: {len(VERIFIED_BY_HAND)}   "
          f"skipped — ancient: {counts['ancient']}, journal w/o title: "
          f"{counts['journal'] - counts['article']}, "
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
