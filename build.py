#!/usr/bin/env python3
"""
Veiled Antiquity - static site builder.

Reads content/posts/*.html (each with a JSON metadata header) and emits:
  dist/                  a complete, deployable static site
  wordpress-import.xml   a WXR file importable into any WordPress install

Standard library only. Run:  python build.py
"""

import json
import os
import re
import shutil
import sys
import html
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent
POSTS_DIR = ROOT / "content" / "posts"
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"
PUBLIC = ROOT / "public"   # copied to the site root verbatim (verification files, etc.)
DIST = ROOT / "dist"

SITE = {
    "title": "Veiled Antiquity",
    "tagline": "The initiated history of the ancient world",
    "description": (
        "Mystery cults, forbidden rites and lost knowledge from the ancient world. "
        "Where the stories come from, and where the evidence runs out."
    ),
    "url": "https://veiledantiquity.com",
    "author": "Veiled Antiquity",
    "author_login": "admin",
    "author_email": "hello@veiledantiquity.com",
    "lang": "en-US",
    "locale": "en_US",
    "twitter": "@veiledantiquity",
}

# Revenue plumbing. Everything here is inert until an ID is filled in, so the
# site ships clean and switches on one line at a time when you're ready.
MONETISATION = {
    # Amazon Associates tag, e.g. "veiledantiq-21". Turns book titles in the
    # Sources list into affiliate links.
    "amazon_tag": "",
    # Amazon regional domain your tag belongs to.
    "amazon_domain": "amazon.co.uk",
    # Google AdSense publisher ID, e.g. "ca-pub-0000000000000000".
    "adsense_client": "",
    # Form POST endpoint from Buttondown / ConvertKit / Kit / Mailchimp.
    "newsletter_action": "https://buttondown.com/api/emails/embed-subscribe/veiled",
    # Google Analytics 4 measurement ID, e.g. "G-XXXXXXXXXX". Ad networks
    # expect to see analytics; you also cannot tune what you cannot measure.
    "ga4_id": "G-XFGE382VWT",
    # Plausible domain, if you prefer a cookie-free alternative to GA4.
    "plausible_domain": "",
    "contact_email": "hello@veiledantiquity.com",
}

IMAGES_FILE = ROOT / "content" / "images.json"
IMAGES = json.loads(IMAGES_FILE.read_text(encoding="utf-8")) if IMAGES_FILE.exists() else {}

CATEGORIES = {
    "mystery-cults": "Mystery Cults",
    "magic-and-ritual": "Magic & Ritual",
    "lost-and-suppressed": "Lost & Suppressed",
    "oracles-and-divination": "Oracles & Divination",
}

START_HERE = [
    # (heading, intro, [(slug, teaser line), ...], outro)
    #
    # Each teaser line belongs to exactly one article, and the page only shows the
    # lines for articles that are already live. Until 2026-09-14 every section had
    # one blurb written for its whole reading list, so while some of those articles
    # were still scheduled the page teased pieces readers could not click. Write
    # each line so it reads on its own, because any of them can be missing on a
    # given day. Never let a section grow past four articles.
    ("If you read one thing", "", [
        ("ancient-mystery-cults-guide",
         "Hundreds of thousands of people were initiated into secret rites over two "
         "thousand years, and essentially none of them talked. This is how that held."),
    ], ""),
    ("The secret that was genuinely kept",
     "Eleusis ran every year for close to two millennia, and the central rite was "
     "never written down.", [
        ("eleusinian-mysteries-telesterion", "The hall where it happened still stands."),
        ("eleusinian-kykeon-psychedelic",
         "Initiates drank something called the kykeon, and people still argue about what was in it."),
        ("orphic-gold-tablets", "Gold tablets buried with the dead tell them which way to go."),
    ], ""),
    ("Things everyone believes that aren&rsquo;t true", "", [
        ("library-of-alexandria-what-was-lost", "Nobody burned the Library of Alexandria."),
        ("oracle-of-the-dead-ephyra", "The famous Oracle of the Dead is probably a farmhouse."),
        ("delphi-pythia", "The Pythia worked nine days a year, to a published fee scale."),
    ], "These stories survive because they&rsquo;re better than the evidence."),
    ("Objects that outlived their meaning", "", [
        ("mithras-tauroctony-decoded", "A picture in four hundred temples that nobody can read."),
        ("piacenza-liver-etruscan", "A bronze liver mapping the sky."),
        ("liber-linteus", "A book that survived because somebody cut it up for bandages."),
        ("damnatio-memoriae", "A face scraped off a family portrait on an emperor&rsquo;s orders."),
    ], ""),
    ("What ordinary people actually did",
     "Ancient literature was written by a few thousand wealthy men. These were made by "
     "everybody else.", [
        ("ancient-curse-tablets", "Curses scratched into lead and dropped into graves and wells."),
        ("greek-magical-papyri", "Working spellbooks from Roman Egypt."),
        ("evil-eye-ancient-world", "Charms hung over a baby&rsquo;s cradle."),
    ], ""),
    ("Knowledge the state controlled", "", [
        ("sibylline-books-rome", "Books kept sealed and opened only by vote of the Senate."),
        ("books-augustus-burned", "Two thousand unlicensed prophecies burned in a single year."),
        ("numas-buried-books", "Books said to be a dead king&rsquo;s, dug up and burned."),
        ("villa-of-the-mysteries-frescoes",
         "A dining room painted with an initiation, a century after Rome tried to stamp it out."),
    ], ""),
]

CATEGORY_BLURBS = {
    "mystery-cults": "Secret initiations across the Greek and Roman world, from Eleusis to the "
                     "cults of Dionysus, Mithras and Isis, and how well the secrets actually held.",
    "magic-and-ritual": "The working documents of ancient magic: spellbooks from Roman Egypt, "
                        "curses scratched into lead, and what people actually asked for.",
    "lost-and-suppressed": "Books that were burned, names that were erased, and knowledge that "
                           "simply stopped being copied. What was lost, and how quietly it went.",
    "oracles-and-divination": "Reading the future in books, caves, lightning and livers, and "
                              "the institutions built around the answers.",
}

# ---------------------------------------------------------------- templating

def render(template: str, ctx: dict) -> str:
    """Minimal {{key}} substitution. Values are inserted raw."""
    # Analytics and ad scripts belong on every page, so they default in here
    # rather than being threaded through each call site.
    ctx = {"head_extra": analytics_head() + adsense_head(), "og_image": "", **ctx}

    def sub(m):
        key = m.group(1).strip()
        if key not in ctx:
            raise KeyError(f"template key not provided: {key}")
        return str(ctx[key])
    return re.sub(r"\{\{([a-z0-9_]+)\}\}", sub, template)


def load_template(name: str) -> str:
    return (TEMPLATES / name).read_text(encoding="utf-8")


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def strip_unpublished_links(body: str, live_slugs: set) -> str:
    """Unwrap cross-links pointing at posts that have not published yet.

    Post bodies link to each other by hand. When the site is built with --live,
    future posts have no page, so those anchors would 404. Keep the sentence,
    drop the link."""
    def sub(m):
        return m.group(0) if m.group(1) in live_slugs else m.group(2)
    return re.sub(r'<a href="/posts/([a-z0-9-]+)/">(.*?)</a>', sub, body, flags=re.DOTALL)


# ------------------------------------------------------------------- parsing

META_RE = re.compile(r"^<!--META\s*(\{.*?\})\s*META-->\s*", re.DOTALL)


def load_posts() -> list:
    posts = []
    for path in sorted(POSTS_DIR.glob("*.html")):
        raw = path.read_text(encoding="utf-8")
        m = META_RE.match(raw)
        if not m:
            raise ValueError(f"{path.name}: missing <!--META ... META--> header")
        meta = json.loads(m.group(1))
        body = raw[m.end():].strip()

        meta["body"] = body
        meta["source_file"] = path.name
        meta["image"] = IMAGES.get(meta.get("slug", ""))
        meta["dt"] = datetime.strptime(meta["date"], "%Y-%m-%d %H:%M:%S")
        meta["url"] = f"{SITE['url']}/posts/{meta['slug']}/"
        meta["path"] = f"/posts/{meta['slug']}/"

        text = re.sub(r"<[^>]+>", " ", body)
        words = len(text.split())
        meta["word_count"] = words
        meta["read_minutes"] = max(1, round(words / 220))

        for required in ("slug", "title", "seo_title", "description", "category",
                         "focus_keyword", "tags", "date", "dek"):
            if required not in meta:
                raise ValueError(f"{path.name}: missing metadata field '{required}'")
        if meta["category"] not in CATEGORIES:
            raise ValueError(f"{path.name}: unknown category '{meta['category']}'")
        if len(meta["seo_title"]) > 62:
            print(f"  ! seo_title long ({len(meta['seo_title'])}): {meta['slug']}")
        if len(meta["description"]) > 158:
            print(f"  ! description long ({len(meta['description'])}): {meta['slug']}")

        posts.append(meta)

    posts.sort(key=lambda p: p["dt"])
    for i, p in enumerate(posts):
        p["post_id"] = i + 2  # 1 reserved for the About page
    return posts


# --------------------------------------------------------------- site pieces

def nav_html(active: str = "") -> str:
    items = [("/", "Home"), ("/start-here/", "Start Here"), ("/archive/", "Archive"),
             ("/about/", "About")]
    out = []
    for href, label in items:
        cur = ' aria-current="page"' if href == active else ""
        out.append(f'<a href="{href}"{cur}>{label}</a>')
    return "".join(out)


BOOK_RE = re.compile(r"<em>(.*?)</em>")


def affiliate_sources(sources: list) -> tuple:
    """Turn book titles in the Sources list into affiliate links.

    Returns (rendered_items, used_affiliate). Without a configured tag the
    sources render exactly as written, so nothing changes until you opt in."""
    tag = MONETISATION["amazon_tag"]
    if not tag:
        return sources, False

    domain = MONETISATION["amazon_domain"]
    out, used = [], False
    for item in sources:
        m = BOOK_RE.search(item)
        # Only link entries that look like books; skip ancient texts, which are
        # public domain and where an affiliate link is just noise.
        if not m or any(w in item for w in ("&mdash; the", "Papyrus", "papyrus")) and "(" not in item:
            out.append(item)
            continue
        title = re.sub(r"<[^>]+>", "", m.group(1))
        q = urllib.parse.quote_plus(title)
        url = f"https://www.{domain}/s?k={q}&tag={tag}"
        out.append(f'{item} <a class="aff" href="{url}" rel="sponsored nofollow noopener" '
                   f'target="_blank">Find a copy</a>')
        used = True
    return out, used


def disclosure_html() -> str:
    return ('<p class="disclosure">Some links above are affiliate links. If you buy through '
            'them this site earns a small commission at no extra cost to you, which pays for '
            'the hosting. It never affects which books get recommended. '
            '<a href="/disclosure/">Read the full disclosure</a>.</p>')


def ad_slot(position: str) -> str:
    """An AdSense unit. Renders nothing at all until a publisher ID is set."""
    client = MONETISATION["adsense_client"]
    if not client:
        return ""
    return f"""<aside class="ad ad-{position}" aria-label="Advertisement">
  <ins class="adsbygoogle" style="display:block" data-ad-client="{client}"
       data-ad-format="auto" data-full-width-responsive="true"></ins>
  <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
</aside>"""


def analytics_head() -> str:
    """Whichever analytics is configured. Nothing renders until one is set."""
    out = []
    if MONETISATION["ga4_id"]:
        gid = MONETISATION["ga4_id"]
        out.append(
            f'<script async src="https://www.googletagmanager.com/gtag/js?id={gid}"></script>\n'
            f"<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}"
            f"gtag('js',new Date());gtag('config','{gid}');</script>")
    if MONETISATION["plausible_domain"]:
        out.append(f'<script defer data-domain="{MONETISATION["plausible_domain"]}" '
                   f'src="https://plausible.io/js/script.js"></script>')
    return "\n".join(out)


def adsense_head() -> str:
    client = MONETISATION["adsense_client"]
    if not client:
        return ""
    return (f'<script async src="https://pagead2.googlesyndication.com/pagead/js/'
            f'adsbygoogle.js?client={client}" crossorigin="anonymous"></script>')


def newsletter_html() -> str:
    """Email capture. The list is the asset that survives algorithm changes."""
    action = MONETISATION["newsletter_action"]
    if not action:
        return ""
    return f"""<section class="signup" aria-labelledby="signup-h">
  <h2 id="signup-h">Three pieces a week, straight to you</h2>
  <p>Mystery cults, buried curses and the things antiquity deliberately kept quiet. No spam, and you can unsubscribe in one click.</p>
  <form action="{action}" method="post" target="_blank">
    <label class="visually-hidden" for="bd-email">Email address</label>
    <input id="bd-email" type="email" name="email" required placeholder="you@example.com" autocomplete="email">
    <button type="submit">Subscribe</button>
  </form>
  <p class="signup-credit">Powered by <a href="https://buttondown.com/refer/veiled" target="_blank" rel="noopener">Buttondown</a>.</p>
</section>"""


def legal_pages() -> list:
    """Privacy, disclosure and contact pages.

    Ad networks check for these before approving a site, and the affiliate
    disclosure is an FTC requirement rather than a nicety. These are a sound
    starting point written for how this site actually works &mdash; they are not
    legal advice, and should be reviewed before you rely on them."""
    email = MONETISATION["contact_email"]

    # The third-party list is built from MONETISATION so this page cannot drift
    # from what the site actually loads. Until 2026-09-14 it was hand-written and
    # wrong three ways: it said fonts came from Google Fonts (they are self-hosted),
    # said EEA/UK visitors saw a consent prompt (no consent tool exists), and never
    # mentioned Google Analytics, which was live on every page.
    #
    # Before switching on AdSense: personalised ads to EEA/UK visitors need a
    # certified consent platform. Do not add a line here claiming one exists
    # until it actually does.
    #
    # The "Last updated" date below is fixed on purpose. It used to be
    # datetime.now(), which stamped the build date, so the page claimed to have
    # been revised every single day. Change it by hand when the policy changes.
    third_party = [
        "<li><strong>Hosting.</strong> The site is served by GitHub Pages, which logs "
        "requests, including IP addresses, for security and abuse prevention.</li>",
    ]
    if MONETISATION["ga4_id"]:
        third_party.append(
            "<li><strong>Analytics.</strong> Google Analytics counts visits and shows which "
            "pages get read. Google sets cookies to do this and receives technical details "
            "about your visit, such as your browser and rough location. Most ad blockers stop "
            "it, or you can use Google&rsquo;s "
            '<a href="https://tools.google.com/dlpage/gaoptout" rel="noopener">opt-out add-on</a>.</li>')
    if MONETISATION["adsense_client"]:
        third_party.append(
            "<li><strong>Advertising.</strong> Google AdSense and its partners may set cookies "
            "and use identifiers to serve and measure ads. You can review your settings at "
            '<a href="https://adssettings.google.com" rel="noopener">Google Ads Settings</a>.</li>')
    if MONETISATION["amazon_tag"]:
        third_party.append(
            "<li><strong>Affiliate links.</strong> Links to booksellers carry a referral code "
            "showing the visit came from this site. That tells the retailer where you came "
            "from, not who you are.</li>")
    if MONETISATION["newsletter_action"]:
        third_party.append(
            "<li><strong>Email.</strong> If you subscribe, your address is held by our email "
            "provider, Buttondown, only to send the newsletter. Every email has an unsubscribe "
            "link.</li>")
    third_party_html = "\n  ".join(third_party)

    privacy = f"""<header class="page-head"><h1>Privacy</h1></header>
<p class="lede">The short version: this site collects as little as it can, and sells nothing about you to anyone.</p>
<h2>What we collect ourselves</h2>
<p>Nothing. There are no accounts and no comment forms, so there&rsquo;s nowhere for us to keep your details. The site is a set of static pages, and its fonts are served from here too, so loading them doesn&rsquo;t tell anyone else you visited.</p>
<h2>What other companies may collect</h2>
<p>A few things are out of our hands, and it&rsquo;s more useful to list them than to pretend otherwise:</p>
<ul>
  {third_party_html}
</ul>
<h2>Your rights</h2>
<p>If you&rsquo;re in the UK, EEA or California you have rights over personal data held about you, including access, correction and deletion. The only personal data this site itself can hold is an email address you chose to give, so the quickest route is usually to unsubscribe. For anything else, write to <a href="mailto:{email}">{email}</a> and we&rsquo;ll act on it.</p>
<h2>Children</h2>
<p>This site isn&rsquo;t aimed at children under 13 and doesn&rsquo;t knowingly collect their data.</p>
<h2>Changes</h2>
<p>Material changes to this page will be noted here with a date. Last updated 14 September 2026.</p>"""

    disclosure = f"""<header class="page-head"><h1>Disclosure</h1></header>
<p class="lede">How this site pays for itself, so you don&rsquo;t have to wonder.</p>
<h2>Affiliate links</h2>
<p>The reading list at the end of an article may include affiliate links to booksellers. If you buy something through one, this site gets a small commission and you pay exactly the same price.</p>
<p>Books are listed because the article actually relies on them. The reading lists were written before any affiliate programme existed, and nothing has been added, moved up or praised because it pays better. If the best source earns nothing, it still gets listed.</p>
<h2>Advertising</h2>
<p>The site may show ads. Advertisers get no say in what&rsquo;s written, no early look at articles, and no way to have anything changed or taken down.</p>
<h2>Sponsorship and gifts</h2>
<p>Nothing here has been sponsored. If that ever changes, the article will say so in its first paragraph, not in a footnote. The same goes for any free review copy or access.</p>
<h2>What stays the same</h2>
<p>None of this changes what gets written. Plenty of articles here argue against the popular version of their subject, which isn&rsquo;t how you&rsquo;d write if you were chasing clicks. That won&rsquo;t change.</p>
<p>Questions: <a href="mailto:{email}">{email}</a>.</p>"""

    contact = f"""<header class="page-head"><h1>Contact</h1></header>
<p class="lede">Corrections especially welcome.</p>
<p>Email: <a href="mailto:{email}">{email}</a></p>
<h2>Corrections</h2>
<p>If something here is wrong, say so and point at the evidence. Errors get fixed, and the correction is noted on the article rather than quietly patched. Given how often the scholarship on these subjects disagrees with itself, that isn&rsquo;t a formality.</p>
<h2>Republishing</h2>
<p>Text on this site is the author&rsquo;s own. Short quotations with a link are fine without asking. For anything longer, ask first.</p>
<p>The images come from Wikimedia Commons and are either public domain or Creative Commons licensed. Each one is credited under the image with its licence, and that licence applies to the image, not to this site.</p>"""

    return [
        ("privacy", "Privacy", "What Veiled Antiquity collects, what third parties collect, and your rights over it.", privacy),
        ("disclosure", "Disclosure", "How this site makes money: affiliate links, advertising, and what none of it changes.", disclosure),
        ("contact", "Contact", "Get in touch with Veiled Antiquity, especially with corrections.", contact),
    ]


def og_image(p: dict = None) -> str:
    """Absolute URL for social preview cards.

    Prefers the generated share card (headline set over the hero image) — a
    plain photo crop reads as generic in a feed and gets fewer clicks."""
    img = (p or {}).get("image")
    if not img and IMAGES:
        img = next(iter(IMAGES.values()))
    if not img:
        return SITE["url"] + "/static/mark.svg"
    return SITE["url"] + (img.get("share") or img["file"])


def hero_html(p: dict) -> str:
    """Lead image for a post, with the attribution its licence requires."""
    img = p.get("image")
    if not img:
        return ""
    credit = f'{esc(img["credit"])}, {esc(img["licence"])}' if img["credit"] else esc(img["licence"])
    link = f' &middot; <a href="{img["source"]}" rel="noopener nofollow">Wikimedia Commons</a>' if img["source"] else ""

    # AVIF at two widths, JPEG as the fallback. The article column is ~700px, so
    # a 1x display never needs the 1400px file — that alone is most of the saving.
    sources = ""
    if img.get("avif") and img.get("avif_700"):
        # Descriptors must state the width the file actually has. These were
        # hardcoded to 700w/1400w, so a 500px source advertised a 1400w
        # candidate: a retina browser dutifully picked it and upscaled three
        # times over. Where the source is under 700px the two AVIFs are byte
        # identical, so offer only one.
        full_w = int(img.get("width") or 1400)
        srcset = (f'{img["avif"]} {full_w}w' if full_w <= 700
                  else f'{img["avif_700"]} 700w, {img["avif"]} {full_w}w')
        sources = (f'<source type="image/avif" srcset="{srcset}" '
                   f'sizes="(max-width: 760px) 100vw, 700px">')

    picture = (f'<picture>{sources}'
               f'<img src="{img["file"]}" alt="{esc(img["alt"])}" '
               f'width="{img["width"]}" height="{img["height"]}" '
               f'fetchpriority="high" decoding="async"></picture>')

    return f"""<figure class="hero-figure">
  {picture}
  <figcaption>{img['caption']} <span class="credit">{credit}{link}</span></figcaption>
</figure>"""


def card_html(p: dict) -> str:
    cat = CATEGORIES[p["category"]]
    date_h = p["dt"].strftime("%d %B %Y")
    img = p.get("image")
    thumb = (f'<img class="card-img" src="{img["card"]}" alt="" width="520" height="300" '
             f'loading="lazy" decoding="async">') if img and img.get("card") else ""
    return f"""<article class="card">
  <a class="card-link" href="{p['path']}">
    {thumb}
    <p class="card-meta"><span class="cat">{esc(cat)}</span><time datetime="{p['dt'].date()}">{date_h}</time></p>
    <h3 class="card-title">{esc(p['title'])}</h3>
    <p class="card-dek">{esc(p['dek'])}</p>
    <p class="card-more">Read<span class="arrow">&rarr;</span><span class="rt">{p['read_minutes']} min</span></p>
  </a>
</article>"""


def related_html(post: dict, posts: list) -> str:
    """Pick up to 3 related posts: explicit `related` slugs first, then same category."""
    by_slug = {p["slug"]: p for p in posts}
    chosen, seen = [], {post["slug"]}
    for slug in post.get("related", []):
        if slug in by_slug and slug not in seen:
            chosen.append(by_slug[slug]); seen.add(slug)
    for p in posts:
        if len(chosen) >= 3:
            break
        if p["slug"] not in seen and p["category"] == post["category"]:
            chosen.append(p); seen.add(p["slug"])
    for p in posts:
        if len(chosen) >= 3:
            break
        if p["slug"] not in seen:
            chosen.append(p); seen.add(p["slug"])

    if not chosen:
        return ""
    cards = "\n".join(
        f'<li><a href="{p["path"]}"><span class="rel-cat">{esc(CATEGORIES[p["category"]])}</span>'
        f'<span class="rel-title">{esc(p["title"])}</span></a></li>'
        for p in chosen[:3]
    )
    return f'<nav class="related" aria-labelledby="rel-h"><h2 id="rel-h">Continue the descent</h2><ul>{cards}</ul></nav>'


def prevnext_html(p: dict, posts: list) -> str:
    """Older/newer links. Cheap, and the single best lever on pages per session —
    ad revenue is priced per pageview, so a second post read doubles the visit."""
    i = posts.index(p)
    prev = posts[i - 1] if i > 0 else None
    nxt = posts[i + 1] if i < len(posts) - 1 else None
    if not prev and not nxt:
        return ""
    left = (f'<a class="pn-prev" href="{prev["path"]}"><span class="pn-label">Previous</span>'
            f'<span class="pn-title">{esc(prev["title"])}</span></a>') if prev else "<span></span>"
    right = (f'<a class="pn-next" href="{nxt["path"]}"><span class="pn-label">Next</span>'
             f'<span class="pn-title">{esc(nxt["title"])}</span></a>') if nxt else "<span></span>"
    return f'<nav class="prevnext" aria-label="More posts">{left}{right}</nav>'


def jsonld_post(p: dict) -> str:
    data = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "BlogPosting",
                "@id": p["url"] + "#article",
                "headline": p["title"],
                "description": p["description"],
                "articleSection": CATEGORIES[p["category"]],
                "keywords": ", ".join(p["tags"]),
                "wordCount": p["word_count"],
                "inLanguage": SITE["lang"],
                "datePublished": p["dt"].isoformat(),
                "dateModified": p["dt"].isoformat(),
                "mainEntityOfPage": {"@type": "WebPage", "@id": p["url"]},
                "author": {"@type": "Organization", "name": SITE["author"], "url": SITE["url"]},
                "publisher": {"@id": SITE["url"] + "#org"},
                "isPartOf": {"@id": SITE["url"] + "#website"},
                **({"image": {
                    "@type": "ImageObject",
                    "url": SITE["url"] + p["image"]["file"],
                    "width": p["image"]["width"],
                    "height": p["image"]["height"],
                    "caption": re.sub(r"<[^>]+>", "", p["image"]["caption"]),
                }} if p.get("image") else {}),
            },
            {
                "@type": "Organization",
                "@id": SITE["url"] + "#org",
                "name": SITE["title"],
                "url": SITE["url"],
                "description": SITE["description"],
            },
            {
                "@type": "WebSite",
                "@id": SITE["url"] + "#website",
                "url": SITE["url"],
                "name": SITE["title"],
                "publisher": {"@id": SITE["url"] + "#org"},
                "inLanguage": SITE["lang"],
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE["url"] + "/"},
                    {"@type": "ListItem", "position": 2, "name": CATEGORIES[p["category"]],
                     "item": f"{SITE['url']}/archive/#{p['category']}"},
                    {"@type": "ListItem", "position": 3, "name": p["title"], "item": p["url"]},
                ],
            },
        ],
    }
    if p.get("faq"):
        data["@graph"].append({
            "@type": "FAQPage",
            "@id": p["url"] + "#faq",
            "mainEntity": [
                {"@type": "Question", "name": q,
                 "acceptedAnswer": {"@type": "Answer", "text": a}}
                for q, a in p["faq"]
            ],
        })
    return json.dumps(data, ensure_ascii=False, indent=2)


def faq_html(p: dict) -> str:
    if not p.get("faq"):
        return ""
    rows = "\n".join(
        f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>"
        for q, a in p["faq"]
    )
    return f'<section class="faq" aria-labelledby="faq-h"><h2 id="faq-h">Questions people actually ask</h2>{rows}</section>'


def sources_html(p: dict) -> str:
    if not p.get("sources"):
        return ""
    items, used_affiliate = affiliate_sources(p["sources"])
    rows = "\n".join(f"<li>{s}</li>" for s in items)
    note = disclosure_html() if used_affiliate else ""
    return (f'<section class="sources" aria-labelledby="src-h">'
            f'<h2 id="src-h">Sources &amp; further reading</h2><ul>{rows}</ul>{note}</section>')


# ----------------------------------------------------------------- rendering

def build_site(posts: list):
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    shutil.copytree(STATIC, DIST / "static")
    if PUBLIC.exists():
        shutil.copytree(PUBLIC, DIST, dirs_exist_ok=True)

    base = load_template("base.html")
    post_tpl = load_template("post.html")
    live = {p["slug"] for p in posts}

    # ---- posts
    for p in posts:
        body = strip_unpublished_links(p["body"], live)
        toc = ""
        heads = re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', body, re.DOTALL)
        if len(heads) >= 3:
            items = "\n".join(
                f'<li><a href="#{hid}">{re.sub(r"<[^>]+>", "", htxt)}</a></li>' for hid, htxt in heads
            )
            toc = f'<nav class="toc" aria-labelledby="toc-h"><h2 id="toc-h">In this piece</h2><ol>{items}</ol></nav>'

        article = render(post_tpl, {
            "title": esc(p["title"]),
            "dek": esc(p["dek"]),
            "category": esc(CATEGORIES[p["category"]]),
            "category_slug": p["category"],
            "date_iso": str(p["dt"].date()),
            "date_human": p["dt"].strftime("%d %B %Y"),
            "read_minutes": p["read_minutes"],
            "word_count": f"{p['word_count']:,}",
            "hero": hero_html(p),
            "toc": toc,
            "body": body,
            "faq": faq_html(p),
            "sources": sources_html(p),
            "ad_bottom": ad_slot("bottom"),
            "newsletter": newsletter_html(),
            "prevnext": prevnext_html(p, posts),
            "related": related_html(p, posts),
            "tags": " ".join(f'<span class="tag">{esc(t)}</span>' for t in p["tags"]),
        })

        page = render(base, {
            "lang": SITE["lang"],
            "page_title": esc(p["seo_title"]) + " | " + esc(SITE["title"]),
            "description": esc(p["description"]),
            "canonical": p["url"],
            "og_type": "article",
            "og_image": og_image(p),
            "og_title": esc(p["title"]),
            "site_name": esc(SITE["title"]),
            "twitter": SITE["twitter"],
            "locale": SITE["locale"],
            "jsonld": jsonld_post(p),
            "nav": nav_html(),
            "body_class": "is-post",
            "content": article,
            "year": datetime.now().year,
            "site_url": SITE["url"],
            "tagline": esc(SITE["tagline"]),
        })
        out = DIST / "posts" / p["slug"]
        out.mkdir(parents=True, exist_ok=True)
        (out / "index.html").write_text(page, encoding="utf-8")

    # ---- home
    home = f"""<header class="hero">
  <p class="hero-kicker">{esc(SITE['tagline'])}</p>
  <h1>Veiled<span class="hero-break"> </span>Antiquity</h1>
  <p class="hero-dek">{esc(SITE['description'])}</p>
</header>"""

    if posts:
        lead, rest = posts[0], list(reversed(posts[1:]))  # pillar guide stays first; the rest run newest first
        lead_img = lead.get("image")
        lead_thumb = (f'<img class="lead-img" src="{lead_img["file"]}" alt="{esc(lead_img["alt"])}" '
                      f'width="{lead_img["width"]}" height="{lead_img["height"]}" '
                      f'fetchpriority="high" decoding="async">') if lead_img else ""
        home += f"""
<section class="lead" aria-labelledby="lead-h">
  <p class="section-label" id="lead-h">If you read one thing</p>
  <a class="lead-link" href="{lead['path']}">
    {lead_thumb}
    <div class="lead-text">
      <h2>{esc(lead['title'])}</h2>
      <p>{esc(lead['dek'])}</p>
      <p class="card-more">Read the guide<span class="arrow">&rarr;</span><span class="rt">{lead['read_minutes']} min</span></p>
    </div>
  </a>
</section>"""
        if rest:
            home += f"""
<section aria-labelledby="recent-h">
  <p class="section-label" id="recent-h">Latest pieces</p>
  <div class="grid">{"".join(card_html(p) for p in rest)}</div>
</section>"""
    else:
        home += '<p class="section-label">The first piece publishes shortly.</p>'

    home += newsletter_html()

    (DIST / "index.html").write_text(render(base, {
        "lang": SITE["lang"], "page_title": f"{SITE['title']}: {SITE['tagline']}",
        "description": esc(SITE["description"]), "canonical": SITE["url"] + "/",
        "og_type": "website", "og_image": og_image(), "og_title": esc(SITE["title"]), "site_name": esc(SITE["title"]),
        "twitter": SITE["twitter"], "locale": SITE["locale"],
        "jsonld": json.dumps({
            "@context": "https://schema.org", "@type": "Blog",
            "@id": SITE["url"] + "#website", "name": SITE["title"], "url": SITE["url"],
            "description": SITE["description"], "inLanguage": SITE["lang"],
            "blogPost": [{"@type": "BlogPosting", "headline": p["title"], "url": p["url"],
                          "datePublished": p["dt"].isoformat()} for p in reversed(posts)],
        }, ensure_ascii=False, indent=2),
        "nav": nav_html("/"), "body_class": "is-home", "content": home,
        "year": datetime.now().year, "site_url": SITE["url"], "tagline": esc(SITE["tagline"]),
    }), encoding="utf-8")

    # ---- archive, grouped by category
    blocks = []
    for cslug, cname in CATEGORIES.items():
        group = [p for p in posts if p["category"] == cslug]
        if not group:
            continue
        rows = "\n".join(
            f'<li><a href="{p["path"]}"><time datetime="{p["dt"].date()}">{p["dt"].strftime("%d %b")}</time>'
            f'<span class="arch-title">{esc(p["title"])}</span></a></li>' for p in reversed(group)
        )
        blocks.append(f'<section id="{cslug}"><h2><a href="/category/{cslug}/">{esc(cname)}</a></h2>'
                      f'<ul class="arch">{rows}</ul></section>')

    (DIST / "archive").mkdir(parents=True, exist_ok=True)
    (DIST / "archive" / "index.html").write_text(render(base, {
        "lang": SITE["lang"], "page_title": f"Archive | {SITE['title']}",
        "description": "Every piece published on Veiled Antiquity, grouped by theme: mystery cults, magic and ritual, suppressed knowledge, and oracles.",
        "canonical": SITE["url"] + "/archive/", "og_type": "website", "og_image": og_image(),
        "og_title": "The Veiled Antiquity Archive", "site_name": esc(SITE["title"]), "twitter": SITE["twitter"],
        "locale": SITE["locale"], "jsonld": json.dumps({"@context": "https://schema.org", "@type": "CollectionPage", "name": "Archive", "url": SITE["url"] + "/archive/", "isPartOf": {"@id": SITE["url"] + "#website"}}, ensure_ascii=False), "nav": nav_html("/archive/"),
        "body_class": "is-page",
        "content": f'<header class="page-head"><h1>Archive</h1><p class="hero-dek">Everything published so far, grouped by theme, newest first.</p></header>{"".join(blocks)}',
        "year": datetime.now().year, "site_url": SITE["url"], "tagline": esc(SITE["tagline"]),
    }), encoding="utf-8")

    # ---- about
    about_body = """<header class="page-head"><h1>About Veiled Antiquity</h1></header>
<p class="lede">Among the curse tablets pulled out of the sacred spring at Bath is a small sheet of lead inscribed by a man called Docilianus. Someone had stolen his hooded cloak. He asked the goddess Sulis to make the thief suffer, with no sleep and no children, until the cloak was brought back to her temple.</p>
<p>He never meant for anyone else to read it. That&rsquo;s the kind of thing this site is about.</p>
<h2>What you&rsquo;ll find here</h2>
<p>Veiled Antiquity is about the parts of ancient history that were meant to stay private. Mystery cults you had to be initiated into, and then never talk about. Prophecy books kept under lock and key, consulted only when the Roman Senate ordered it. Curses buried with the dead. Names chiselled off monuments by people who wanted someone forgotten.</p>
<p>A surprising amount of that secrecy held. People went through the Mysteries at Eleusis for centuries, and no initiate ever left a clear account of what happened inside. We still don&rsquo;t know.</p>
<h2>How the pieces work</h2>
<p>Each one starts with something real: an object, a place, a person, a line in an old book. From there it follows the evidence as far as it goes and stops where it runs out. When the experts disagree, you get the argument rather than a tidy verdict, and every source is listed at the end.</p>
<p>Honestly, &ldquo;nobody knows&rdquo; tends to make a better story than whatever gets invented to fill the gap.</p>
<h2>When new pieces come out</h2>
<p>Every Monday, Wednesday and Friday. If you&rsquo;d rather not keep checking, <a href="/#signup-h">sign up on the home page</a> and they&rsquo;ll come straight to your inbox, or follow along by <a href="/feed.xml">RSS</a>.</p>"""

    (DIST / "about").mkdir(parents=True, exist_ok=True)
    (DIST / "about" / "index.html").write_text(render(base, {
        "lang": SITE["lang"], "page_title": f"About | {SITE['title']}",
        "description": "Veiled Antiquity is a blog about the hidden side of ancient history: mystery cults, forbidden rites, sealed prophecy books and curses buried with the dead.",
        "canonical": SITE["url"] + "/about/", "og_type": "website", "og_image": og_image(),
        "og_title": "About Veiled Antiquity",
        "site_name": esc(SITE["title"]), "twitter": SITE["twitter"], "locale": SITE["locale"],
        "jsonld": json.dumps({"@context": "https://schema.org", "@type": "AboutPage", "name": "About Veiled Antiquity", "url": SITE["url"] + "/about/", "isPartOf": {"@id": SITE["url"] + "#website"}}, ensure_ascii=False), "nav": nav_html("/about/"), "body_class": "is-page",
        "content": about_body, "year": datetime.now().year, "site_url": SITE["url"],
        "tagline": esc(SITE["tagline"]),
    }), encoding="utf-8")

    # ---- category pages
    # Real indexable pages per theme rather than anchors on one archive: more
    # surface for Google, and a genuine internal-linking hub per topic.
    for cslug, cname in CATEGORIES.items():
        group = [p for p in posts if p["category"] == cslug]
        if not group:
            continue
        blurb = CATEGORY_BLURBS[cslug]
        content = (f'<header class="page-head"><h1>{esc(cname)}</h1>'
                   f'<p class="hero-dek">{blurb}</p></header>'
                   f'<div class="grid">{"".join(card_html(p) for p in reversed(group))}</div>')
        out = DIST / "category" / cslug
        out.mkdir(parents=True, exist_ok=True)
        (out / "index.html").write_text(render(base, {
            "lang": SITE["lang"],
            "page_title": f"{cname} | {SITE['title']}",
            "description": esc(blurb),
            "canonical": f"{SITE['url']}/category/{cslug}/",
            "og_type": "website", "og_image": og_image(group[0]), "og_title": esc(cname),
            "site_name": esc(SITE["title"]), "twitter": SITE["twitter"], "locale": SITE["locale"],
            "jsonld": json.dumps({
                "@context": "https://schema.org", "@type": "CollectionPage",
                "name": cname, "description": blurb,
                "url": f"{SITE['url']}/category/{cslug}/",
                "isPartOf": {"@id": SITE["url"] + "#website"},
            }, ensure_ascii=False, indent=2),
            "nav": nav_html(), "body_class": "is-page", "content": content,
            "year": datetime.now().year, "site_url": SITE["url"], "tagline": esc(SITE["tagline"]),
        }), encoding="utf-8")

    # ---- start here
    # A curated entry point. New readers landing on one post from search have no
    # reason to click a second; giving them routes with a stated payoff is the
    # cheapest way to lift pages per session.
    live = {p["slug"]: p for p in posts}
    sections = []
    for heading, intro, items, outro in START_HERE:
        # Only live articles, and only their own teaser lines. See START_HERE.
        # A bare slug is accepted too, so an entry added the old way renders its
        # article without a teaser line instead of crashing the whole build.
        items = [(item, "") if isinstance(item, str) else item for item in items]
        picks = [(live[slug], hook) for slug, hook in items if slug in live]
        if not picks:
            continue
        blurb = " ".join(part for part in (intro, *(hook for _, hook in picks), outro) if part)
        rows = "\n".join(
            f'<li><a href="{p["path"]}"><span class="sh-title">{esc(p["title"])}</span>'
            f'<span class="sh-dek">{esc(p["dek"])}</span></a></li>' for p, _ in picks)
        sections.append(f'<section class="sh-block"><h2>{heading}</h2>'
                        f'<p class="sh-why">{blurb}</p><ul class="sh-list">{rows}</ul></section>')

    if sections:
        out = DIST / "start-here"
        out.mkdir(parents=True, exist_ok=True)
        (out / "index.html").write_text(render(base, {
            "lang": SITE["lang"], "page_title": f"Start Here | {SITE['title']}",
            "description": "New to Veiled Antiquity? Start with these: the secret that was "
                           "actually kept, the famous stories that turn out wrong, and "
                           "what ordinary people really did.",
            "canonical": SITE["url"] + "/start-here/", "og_type": "website",
            "og_image": og_image(posts[0]), "og_title": "Where to Start with Veiled Antiquity",
            "site_name": esc(SITE["title"]), "twitter": SITE["twitter"], "locale": SITE["locale"],
            "jsonld": json.dumps({"@context": "https://schema.org", "@type": "CollectionPage", "name": "Start Here", "url": SITE["url"] + "/start-here/", "isPartOf": {"@id": SITE["url"] + "#website"}}, ensure_ascii=False), "nav": nav_html("/start-here/"), "body_class": "is-page",
            "content": '<header class="page-head"><h1>Start here</h1><p class="hero-dek">'
                       'Not sure where to begin? These are the pieces we&rsquo;d hand a friend '
                       'first.</p></header>' + "".join(sections),
            "year": datetime.now().year, "site_url": SITE["url"], "tagline": esc(SITE["tagline"]),
        }), encoding="utf-8")

    # ---- legal pages (AdSense and most ad networks will not accept a site without these)
    for slug, title, desc, body in legal_pages():
        out = DIST / slug
        out.mkdir(parents=True, exist_ok=True)
        (out / "index.html").write_text(render(base, {
            "lang": SITE["lang"], "page_title": f"{title} | {SITE['title']}",
            "description": esc(desc), "canonical": f"{SITE['url']}/{slug}/",
            "og_type": "website", "og_image": og_image(), "og_title": esc(title),
            "site_name": esc(SITE["title"]), "twitter": SITE["twitter"],
            "locale": SITE["locale"], "jsonld": "{}", "nav": nav_html(),
            "body_class": "is-page", "content": body,
            "year": datetime.now().year, "site_url": SITE["url"], "tagline": esc(SITE["tagline"]),
        }), encoding="utf-8")

    # ---- 404
    (DIST / "404.html").write_text(render(base, {
        "lang": SITE["lang"], "page_title": f"Not found | {SITE['title']}",
        "description": "That page could not be found.", "canonical": SITE["url"] + "/404.html",
        "og_type": "website", "og_image": og_image(), "og_title": "Not found", "site_name": esc(SITE["title"]),
        "twitter": SITE["twitter"], "locale": SITE["locale"], "jsonld": "{}",
        "nav": nav_html(), "body_class": "is-page",
        "content": '<header class="page-head"><h1>Nothing here</h1><p class="hero-dek">Some things were meant to stay lost. This one probably wasn\'t. <a href="/">Return to the entrance</a>.</p></header>',
        "year": datetime.now().year, "site_url": SITE["url"], "tagline": esc(SITE["tagline"]),
    }), encoding="utf-8")

    # ---- sitemap
    urls = [(SITE["url"] + "/", "1.0"), (SITE["url"] + "/start-here/", "0.9"),
            (SITE["url"] + "/archive/", "0.6"), (SITE["url"] + "/about/", "0.5")]
    urls += [(p["url"], "0.8") for p in posts]
    urls += [(f"{SITE['url']}/category/{c}/", "0.7") for c in CATEGORIES
             if any(p["category"] == c for p in posts)]
    urls += [(f"{SITE['url']}/{s}/", "0.3") for s, *_ in legal_pages()]
    lastmod = max((p["dt"] for p in posts), default=datetime.now()).date()
    entries = "\n".join(
        f"  <url><loc>{u}</loc><lastmod>{lastmod}</lastmod><priority>{pr}</priority></url>"
        for u, pr in urls
    )
    (DIST / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{entries}\n</urlset>\n',
        encoding="utf-8")

    (DIST / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {SITE['url']}/sitemap.xml\n", encoding="utf-8")

    # ---- RSS
    def rfc822(dt):
        return dt.replace(tzinfo=timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

    def feed_item(p):
        # The feed drives the subscriber email, so it carries the dek (written
        # for a reader) rather than the meta description (written for Google),
        # plus the share image. Deliberately a teaser and a link, not the full
        # post — a subscriber who reads the whole piece in their inbox never
        # reaches the site.
        img = p.get("image") or {}
        share = SITE["url"] + img["share"] if img.get("share") else ""
        enclosure = ""
        picture = ""
        if share:
            local = STATIC / "img" / Path(img["share"]).name
            size = local.stat().st_size if local.exists() else 0
            enclosure = f'\n    <enclosure url="{share}" type="image/jpeg" length="{size}"/>'
            picture = (f'<p><a href="{p["url"]}">'
                       f'<img src="{share}" alt="" style="max-width:100%;height:auto;"></a></p>')

        body = (f'{picture}<p>{p["dek"]}</p>'
                f'<p><a href="{p["url"]}">Read it on Veiled Antiquity &#8594;</a></p>')

        return f"""  <item>
    <title>{esc(p['title'])}</title>
    <link>{p['url']}</link>
    <guid isPermaLink="true">{p['url']}</guid>
    <pubDate>{rfc822(p['dt'])}</pubDate>
    <category>{esc(CATEGORIES[p['category']])}</category>{enclosure}
    <description>{esc(p['dek'])}</description>
    <content:encoded><![CDATA[{body}]]></content:encoded>
  </item>"""

    items = "\n".join(feed_item(p) for p in reversed(posts))

    (DIST / "feed.xml").write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"
     xmlns:content="http://purl.org/rss/1.0/modules/content/">
<channel>
  <title>{esc(SITE['title'])}</title>
  <link>{SITE['url']}/</link>
  <description>{esc(SITE['description'])}</description>
  <language>en-us</language>
  <atom:link href="{SITE['url']}/feed.xml" rel="self" type="application/rss+xml"/>
{items}
</channel>
</rss>
""", encoding="utf-8")

    (DIST / ".nojekyll").write_text("", encoding="utf-8")


# ------------------------------------------------------------------ wordpress

def build_wxr(posts: list):
    def cd(s):
        return f"<![CDATA[{s}]]>"

    cats = "\n".join(
        f'  <wp:category><wp:term_id>{i+10}</wp:term_id>'
        f'<wp:category_nicename>{cslug}</wp:category_nicename>'
        f'<wp:category_parent></wp:category_parent>'
        f'<wp:cat_name>{cd(cname)}</wp:cat_name></wp:category>'
        for i, (cslug, cname) in enumerate(CATEGORIES.items())
    )

    all_tags = sorted({t for p in posts for t in p["tags"]})
    tags = "\n".join(
        f'  <wp:tag><wp:term_id>{i+100}</wp:term_id>'
        f'<wp:tag_slug>{re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")}</wp:tag_slug>'
        f'<wp:tag_name>{cd(t)}</wp:tag_name></wp:tag>'
        for i, t in enumerate(all_tags)
    )

    items = []
    for p in posts:
        gmt = p["dt"]  # treat authored times as UTC for simplicity
        body = p["body"]
        if p.get("faq"):
            body += "\n\n<h2>Questions people actually ask</h2>\n" + "\n".join(
                f"<h3>{esc(q)}</h3>\n<p>{esc(a)}</p>" for q, a in p["faq"])
        if p.get("sources"):
            body += "\n\n<h2>Sources &amp; further reading</h2>\n<ul>\n" + "\n".join(
                f"<li>{s}</li>" for s in p["sources"]) + "\n</ul>"

        tag_els = "\n      ".join(
            f'<category domain="post_tag" nicename="{re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")}">{cd(t)}</category>'
            for t in p["tags"])

        meta = [
            ("_yoast_wpseo_title", p["seo_title"] + " %%sep%% %%sitename%%"),
            ("_yoast_wpseo_metadesc", p["description"]),
            ("_yoast_wpseo_focuskw", p["focus_keyword"]),
            ("rank_math_title", p["seo_title"] + " %sep% %sitename%"),
            ("rank_math_description", p["description"]),
            ("rank_math_focus_keyword", p["focus_keyword"]),
        ]
        meta_els = "\n      ".join(
            f"<wp:postmeta><wp:meta_key>{cd(k)}</wp:meta_key><wp:meta_value>{cd(v)}</wp:meta_value></wp:postmeta>"
            for k, v in meta)

        items.append(f"""  <item>
    <title>{esc(p['title'])}</title>
    <link>{p['url']}</link>
    <pubDate>{gmt.strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>
    <dc:creator>{cd(SITE['author_login'])}</dc:creator>
    <guid isPermaLink="false">{SITE['url']}/?p={p['post_id']}</guid>
    <description></description>
    <content:encoded>{cd(body)}</content:encoded>
    <excerpt:encoded>{cd(p['dek'])}</excerpt:encoded>
    <wp:post_id>{p['post_id']}</wp:post_id>
    <wp:post_date>{cd(p['dt'].strftime('%Y-%m-%d %H:%M:%S'))}</wp:post_date>
    <wp:post_date_gmt>{cd(gmt.strftime('%Y-%m-%d %H:%M:%S'))}</wp:post_date_gmt>
    <wp:comment_status>{cd('open')}</wp:comment_status>
    <wp:ping_status>{cd('open')}</wp:ping_status>
    <wp:post_name>{cd(p['slug'])}</wp:post_name>
    <wp:status>{cd('future')}</wp:status>
    <wp:post_parent>0</wp:post_parent>
    <wp:menu_order>0</wp:menu_order>
    <wp:post_type>{cd('post')}</wp:post_type>
    <wp:post_password>{cd('')}</wp:post_password>
    <wp:is_sticky>0</wp:is_sticky>
    <category domain="category" nicename="{p['category']}">{cd(CATEGORIES[p['category']])}</category>
      {tag_els}
      {meta_els}
  </item>""")

    xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0"
  xmlns:excerpt="http://wordpress.org/export/1.2/excerpt/"
  xmlns:content="http://purl.org/rss/1.0/modules/content/"
  xmlns:wfw="http://wellformedweb.org/CommentAPI/"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:wp="http://wordpress.org/export/1.2/">
<channel>
  <title>{esc(SITE['title'])}</title>
  <link>{SITE['url']}</link>
  <description>{esc(SITE['description'])}</description>
  <pubDate>{datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>
  <language>en-US</language>
  <wp:wxr_version>1.2</wp:wxr_version>
  <wp:base_site_url>{SITE['url']}</wp:base_site_url>
  <wp:base_blog_url>{SITE['url']}</wp:base_blog_url>
  <wp:author><wp:author_id>1</wp:author_id>
    <wp:author_login>{cd(SITE['author_login'])}</wp:author_login>
    <wp:author_email>{cd(SITE['author_email'])}</wp:author_email>
    <wp:author_display_name>{cd(SITE['author'])}</wp:author_display_name>
    <wp:author_first_name>{cd('')}</wp:author_first_name>
    <wp:author_last_name>{cd('')}</wp:author_last_name></wp:author>
{cats}
{tags}
{chr(10).join(items)}
</channel>
</rss>
"""
    (ROOT / "wordpress-import.xml").write_text(xml, encoding="utf-8")


# ----------------------------------------------------------------------- main

def main():
    # --live builds only posts whose date has arrived; this is what the scheduled
    # workflow uses. Without it everything is built, which is what you want locally.
    live_mode = "--live" in sys.argv
    # --now=YYYY-MM-DD pretends it is that date, so you can preview what the site
    # will look like partway through the schedule.
    now = datetime.now()
    for arg in sys.argv:
        if arg.startswith("--now="):
            now = datetime.strptime(arg.split("=", 1)[1], "%Y-%m-%d")

    all_posts = load_posts()
    posts = [p for p in all_posts if p["dt"] <= now] if live_mode else all_posts
    pending = [p for p in all_posts if p not in posts]

    print(f"Loaded {len(all_posts)} posts, {sum(p['word_count'] for p in all_posts):,} words total.")
    if live_mode:
        print(f"Live mode: {len(posts)} published, {len(pending)} scheduled.")

    build_site(posts)
    build_wxr(all_posts)  # WordPress schedules its own; give it everything

    print(f"\n  dist/                  {sum(1 for _ in DIST.rglob('*') if _.is_file())} files")
    print(f"  wordpress-import.xml   {(ROOT / 'wordpress-import.xml').stat().st_size:,} bytes")

    print("\nSchedule:")
    for p in all_posts:
        state = "live " if p in posts else "sched"
        print(f"  [{state}] {p['dt'].strftime('%a %d %b')}  {p['title'][:56]}")


if __name__ == "__main__":
    main()
