#!/usr/bin/env python3
"""Add in-body internal links to posts that are missing them.

Links here are hand-written at write time, so a post can only ever link to posts
that existed when it was written. The August posts can never link forward to the
October ones, and that gap widens every week. This closes it.

**The safety property that makes this runnable unattended.** Backfilled links go
into posts that are already public, so they miss the future-date buffer that makes
the writing loop safe. This tool compensates by being physically unable to write
prose: the only edit it can make is wrapping text that is already on the page in an
anchor tag. After every edit it strips all tags from the before and after and
asserts the visible text is byte-identical. If a single word changed, it refuses to
save. The worst case is therefore a link that is a poor fit, never altered writing.

Other guards, in descending order of how much they matter:

  * Never links inside an existing <a>, inside a heading, or in the META block.
  * Only the FIRST occurrence of a phrase, and only one link per target per post,
    so a common phrase cannot carpet a post.
  * Respects a per-post ceiling (default 4 total in-body links, matching the
    house rule) and adds at most 2 per run.
  * Never links a post to itself.

Dry run by default. Nothing is written without --apply.

  python tools/backfill_links.py                 # show what it would do
  python tools/backfill_links.py --apply         # write the changes
  python tools/backfill_links.py --max-add 1     # be more conservative
"""

import argparse
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import build  # noqa: E402

POSTS = Path(__file__).parent.parent / "content" / "posts"
CEILING = 4          # house rule: 2-4 in-body internal links per post
DEFAULT_MAX_ADD = 2  # per post, per run

# Hand-curated anchor phrases, slug -> extra phrases.
#
# This is the judgement half of the tool, and it is deliberately written once by a
# human rather than inferred per-run. Titles alone match almost nothing: posts
# discuss the Pythia or the kykeon without ever saying "Delphi: What the Pythia
# Actually Did". Each phrase here must point at exactly one post and be the term a
# reader would expect to click.
#
# Ambiguity is the thing to avoid. Bare "Delphi" is not here because two posts are
# about Delphi; "the Pythia" and "ethylene" separate them cleanly. Add to this list
# whenever a post introduces a term that later posts will reach for.
ALIASES = {
    "eleusinian-mysteries-telesterion": ["Telesterion", "Eleusis"],
    "eleusinian-kykeon-psychedelic": ["kykeon"],
    "orphic-gold-tablets": ["gold tablets", "Orphic tablets"],
    "mithras-tauroctony-decoded": ["tauroctony"],
    "mithraism-seven-grades": ["seven grades"],
    "villa-of-the-mysteries-frescoes": ["Villa of the Mysteries"],
    "greek-magical-papyri": ["magical papyri"],
    "ancient-curse-tablets": ["curse tablets", "defixiones"],
    "sibylline-books-rome": ["Sibylline Books"],
    "damnatio-memoriae": ["damnatio memoriae"],
    "library-of-alexandria-what-was-lost": ["Library of Alexandria"],
    "oracle-of-the-dead-ephyra": ["Nekromanteion"],
    "piacenza-liver-etruscan": ["Piacenza Liver", "bronze liver"],
    "samothrace-great-gods": ["Samothrace"],
    "bacchanalia-186-bce": ["Bacchanalia"],
    "cult-of-isis-rome": ["cult of Isis"],
    "ancient-binding-spells-law": ["binding spells"],
    "evil-eye-ancient-world": ["evil eye"],
    "ancient-necromancy": ["necromancy"],
    "greek-magical-gems": ["magical gems"],
    "books-augustus-burned": ["unlicensed prophecy"],
    "liber-linteus": ["Liber Linteus"],
    "etruscan-language-lost": ["Etruscan language"],
    "claudius-etruscan-history": ["Tyrrhenica"],
    "delphi-pythia": ["the Pythia"],
    "delphi-gases-hypothesis": ["ethylene"],
    "dream-incubation-asclepius": ["Epidaurus", "dream incubation"],
    "etruscan-lightning-doctrine": ["libri fulgurales", "lightning books"],
    "numas-buried-books": ["books of Numa"],
    "roman-augury-sacred-chickens": ["sacred chickens"],
    "cult-of-cybele-taurobolium": ["taurobolium"],
    "apuleius-trial-magic": ["Apologia"],
    "chariot-race-curse-tablets": ["circus curses"],
    "love-spell-doll-louvre": ["Louvre doll"],
}

# Phrases too generic to be a good anchor even when they match a post's keyword.
# A link is a promise that the destination is about this; these break that.
STOPWORDS = {
    "ancient", "rome", "roman", "greek", "greece", "magic", "ritual", "cult",
    "cults", "mystery", "mysteries", "oracle", "oracles", "divination", "etruscan",
    "etruscans", "the", "and", "of", "in", "a",
}

TAG_RE = re.compile(r"<[^>]+>")
PARA_RE = re.compile(r"(<p>)(.*?)(</p>)", re.DOTALL)


def visible(s):
    """Tag-stripped, entity-decoded text. The invariant is computed on this."""
    return html.unescape(TAG_RE.sub("", s))


def phrases_for(post):
    """Candidate anchor phrases for a target post, longest first.

    Kept deliberately narrow: the focus keyword and distinctive fragments of the
    title. Anything short or generic is dropped rather than guessed at.
    """
    out = set()
    kw = (post.get("focus_keyword") or "").strip().lower()
    if kw and len(kw.split()) >= 2:
        out.add(kw)

    title = (post.get("title") or "").split(":")[0].strip()
    title = re.sub(r"^(the|a|an)\s+", "", title, flags=re.I).strip()
    if len(title.split()) >= 2:
        out.add(title.lower())

    cleaned = set()
    for p in out:
        words = [w for w in re.findall(r"[a-z']+", p) if w not in STOPWORDS]
        if len(p) >= 10 and words:
            cleaned.add(p)

    # Curated aliases bypass the generic-phrase filter: they were chosen by hand
    # precisely because they are the term a reader would click.
    cleaned.update(a.lower() for a in ALIASES.get(post["slug"], []))
    return sorted(cleaned, key=len, reverse=True)


def linkable_spans(body):
    """Character ranges of body text that are safe to link into.

    Paragraph interiors only, minus any region already inside an anchor. Headings
    and everything outside <p> are excluded entirely.
    """
    spans = []
    for m in PARA_RE.finditer(body):
        start, end = m.start(2), m.end(2)
        inner = m.group(2)
        blocked = [(start + a.start(), start + a.end())
                   for a in re.finditer(r"<a\b.*?</a>", inner, re.DOTALL)]
        cur = start
        for b0, b1 in sorted(blocked):
            if cur < b0:
                spans.append((cur, b0))
            cur = max(cur, b1)
        if cur < end:
            spans.append((cur, end))
    return spans


def find_match(body, phrase):
    """First case-insensitive whole-phrase match inside a linkable span."""
    pat = re.compile(r"(?<![\w-])" + re.escape(phrase).replace(r"\ ", r"[\s]+")
                     + r"(?![\w-])", re.I)
    for s0, s1 in linkable_spans(body):
        m = pat.search(body, s0, s1)
        if m and "<" not in body[m.start():m.end()]:
            return m.start(), m.end()
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write the changes")
    ap.add_argument("--max-add", type=int, default=DEFAULT_MAX_ADD,
                    help=f"new links per post per run (default {DEFAULT_MAX_ADD})")
    args = ap.parse_args()

    posts = build.load_posts()
    by_slug = {p["slug"]: p for p in posts}
    targets = {p["slug"]: phrases_for(p) for p in posts}

    total_added, touched, refused = 0, 0, 0

    for post in posts:
        path = POSTS / post["source_file"]
        raw = path.read_text(encoding="utf-8")
        head, body = raw.split("META-->", 1)

        existing = set(re.findall(r'href="/posts/([^/"]+)/"', body))
        room = CEILING - len(re.findall(r'href="/posts/', body))
        if room <= 0:
            continue

        before_visible = visible(body)
        added = []

        for slug, phrases in targets.items():
            if len(added) >= min(args.max_add, room):
                break
            if slug == post["slug"] or slug in existing:
                continue
            for phrase in phrases:
                hit = find_match(body, phrase)
                if not hit:
                    continue
                a, b = hit
                anchor = body[a:b]
                body = f'{body[:a]}<a href="/posts/{slug}/">{anchor}</a>{body[b:]}'
                added.append((slug, anchor))
                existing.add(slug)
                break

        if not added:
            continue

        # The invariant. If the visible text moved at all, discard this post's
        # edits entirely rather than trying to work out which one was at fault.
        if visible(body) != before_visible:
            print(f"  REFUSED {post['slug']}: visible text changed, discarding")
            refused += 1
            continue

        touched += 1
        total_added += len(added)
        print(f"  {post['slug']}  ({post['date'][:10]})")
        for slug, anchor in added:
            print(f"      \"{anchor}\"  ->  /posts/{slug}/")

        if args.apply:
            path.write_text(head + "META-->" + body, encoding="utf-8")

    verb = "added" if args.apply else "would add"
    print(f"\n  {verb} {total_added} link(s) across {touched} post(s).")
    if refused:
        print(f"  {refused} post(s) refused on the text-unchanged check.")
    if not args.apply and total_added:
        print("  Dry run. Re-run with --apply to write, then build.py && check.py.")


if __name__ == "__main__":
    main()
