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
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent
POSTS_DIR = ROOT / "content" / "posts"
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"
DIST = ROOT / "dist"

SITE = {
    "title": "Veiled Antiquity",
    "tagline": "The initiated history of the ancient world",
    "description": (
        "Mystery cults, forbidden rites and lost knowledge from the ancient world "
        "— researched carefully, told honestly, and never tidier than the evidence allows."
    ),
    "url": "https://thegildedone.github.io",
    "author": "Veiled Antiquity",
    "author_login": "admin",
    "author_email": "hello@veiledantiquity.com",
    "lang": "en-US",
    "locale": "en_US",
    "twitter": "@veiledantiquity",
}

CATEGORIES = {
    "mystery-cults": "Mystery Cults",
    "magic-and-ritual": "Magic & Ritual",
    "lost-and-suppressed": "Lost & Suppressed",
    "oracles-and-divination": "Oracles & Divination",
}

# ---------------------------------------------------------------- templating

def render(template: str, ctx: dict) -> str:
    """Minimal {{key}} substitution. Values are inserted raw."""
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
    items = [("/", "Home"), ("/archive/", "Archive"), ("/about/", "About")]
    out = []
    for href, label in items:
        cur = ' aria-current="page"' if href == active else ""
        out.append(f'<a href="{href}"{cur}>{label}</a>')
    return "".join(out)


def card_html(p: dict) -> str:
    cat = CATEGORIES[p["category"]]
    date_h = p["dt"].strftime("%d %B %Y")
    return f"""<article class="card">
  <a class="card-link" href="{p['path']}">
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
    rows = "\n".join(f"<li>{s}</li>" for s in p["sources"])
    return f'<section class="sources" aria-labelledby="src-h"><h2 id="src-h">Sources &amp; further reading</h2><ul>{rows}</ul></section>'


# ----------------------------------------------------------------- rendering

def build_site(posts: list):
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    shutil.copytree(STATIC, DIST / "static")

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
            "toc": toc,
            "body": body,
            "faq": faq_html(p),
            "sources": sources_html(p),
            "related": related_html(p, posts),
            "tags": " ".join(f'<span class="tag">{esc(t)}</span>' for t in p["tags"]),
        })

        page = render(base, {
            "lang": SITE["lang"],
            "page_title": esc(p["seo_title"]) + " | " + esc(SITE["title"]),
            "description": esc(p["description"]),
            "canonical": p["url"],
            "og_type": "article",
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
        lead, rest = posts[0], posts[1:]
        home += f"""
<section class="lead" aria-labelledby="lead-h">
  <p class="section-label" id="lead-h">Start here</p>
  <a class="lead-link" href="{lead['path']}">
    <h2>{esc(lead['title'])}</h2>
    <p>{esc(lead['dek'])}</p>
    <p class="card-more">Read the guide<span class="arrow">&rarr;</span><span class="rt">{lead['read_minutes']} min</span></p>
  </a>
</section>"""
        if rest:
            home += f"""
<section aria-labelledby="recent-h">
  <p class="section-label" id="recent-h">The archive, in order of descent</p>
  <div class="grid">{"".join(card_html(p) for p in rest)}</div>
</section>"""
    else:
        home += '<p class="section-label">The first piece publishes shortly.</p>'

    (DIST / "index.html").write_text(render(base, {
        "lang": SITE["lang"], "page_title": f"{SITE['title']} — {SITE['tagline']}",
        "description": esc(SITE["description"]), "canonical": SITE["url"] + "/",
        "og_type": "website", "og_title": esc(SITE["title"]), "site_name": esc(SITE["title"]),
        "twitter": SITE["twitter"], "locale": SITE["locale"],
        "jsonld": json.dumps({
            "@context": "https://schema.org", "@type": "Blog",
            "@id": SITE["url"] + "#website", "name": SITE["title"], "url": SITE["url"],
            "description": SITE["description"], "inLanguage": SITE["lang"],
            "blogPost": [{"@type": "BlogPosting", "headline": p["title"], "url": p["url"],
                          "datePublished": p["dt"].isoformat()} for p in posts],
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
            f'<span class="arch-title">{esc(p["title"])}</span></a></li>' for p in group
        )
        blocks.append(f'<section id="{cslug}"><h2>{esc(cname)}</h2><ul class="arch">{rows}</ul></section>')

    (DIST / "archive").mkdir(parents=True, exist_ok=True)
    (DIST / "archive" / "index.html").write_text(render(base, {
        "lang": SITE["lang"], "page_title": f"Archive | {SITE['title']}",
        "description": "Every piece published on Veiled Antiquity, grouped by theme: mystery cults, magic and ritual, suppressed knowledge, and oracles.",
        "canonical": SITE["url"] + "/archive/", "og_type": "website",
        "og_title": "Archive", "site_name": esc(SITE["title"]), "twitter": SITE["twitter"],
        "locale": SITE["locale"], "jsonld": "{}", "nav": nav_html("/archive/"),
        "body_class": "is-page",
        "content": f'<header class="page-head"><h1>Archive</h1><p class="hero-dek">Everything published so far, grouped by theme.</p></header>{"".join(blocks)}',
        "year": datetime.now().year, "site_url": SITE["url"], "tagline": esc(SITE["tagline"]),
    }), encoding="utf-8")

    # ---- about
    about_body = """<header class="page-head"><h1>About Veiled Antiquity</h1></header>
<p class="lede">This site is about the parts of the ancient world that were deliberately kept quiet.</p>
<p>Not the evil parts &mdash; the closed ones. The rites you had to be admitted to. The books that were kept sealed and consulted only by permission of the Senate. The names chiselled off monuments by people who wanted them forgotten. The spells written on lead and buried where no one was meant to dig.</p>
<p>Ancient people were not naive, and they were not us in costume. They built enormous institutions around secrecy, and they were disciplined enough that some of those secrets have genuinely never been recovered. That is the interesting part, and it is the part most writing on this subject rushes past on the way to a theory.</p>
<h2>How this is written</h2>
<p>Three rules, applied to every piece:</p>
<ol>
  <li><strong>The evidence comes first, and it is named.</strong> Where a claim rests on a single line of Pausanias, or on one excavation report, the piece says so.</li>
  <li><strong>&ldquo;We don't know&rdquo; is an acceptable ending.</strong> The Eleusinian secret was kept. No amount of atmosphere changes that, and pretending otherwise would be a worse story than the truth.</li>
  <li><strong>Speculation is labelled as speculation.</strong> Where a hypothesis is contested &mdash; and in this field many are &mdash; the disagreement is part of the article, not an inconvenience buried in a footnote.</li>
</ol>
<h2>Schedule</h2>
<p>New pieces publish Monday, Wednesday and Friday.</p>"""

    (DIST / "about").mkdir(parents=True, exist_ok=True)
    (DIST / "about" / "index.html").write_text(render(base, {
        "lang": SITE["lang"], "page_title": f"About | {SITE['title']}",
        "description": "Veiled Antiquity covers the deliberately hidden parts of ancient history — mystery cults, sealed books, buried curses — with sources named and uncertainty kept intact.",
        "canonical": SITE["url"] + "/about/", "og_type": "website", "og_title": "About",
        "site_name": esc(SITE["title"]), "twitter": SITE["twitter"], "locale": SITE["locale"],
        "jsonld": "{}", "nav": nav_html("/about/"), "body_class": "is-page",
        "content": about_body, "year": datetime.now().year, "site_url": SITE["url"],
        "tagline": esc(SITE["tagline"]),
    }), encoding="utf-8")

    # ---- 404
    (DIST / "404.html").write_text(render(base, {
        "lang": SITE["lang"], "page_title": f"Not found | {SITE['title']}",
        "description": "That page could not be found.", "canonical": SITE["url"] + "/404.html",
        "og_type": "website", "og_title": "Not found", "site_name": esc(SITE["title"]),
        "twitter": SITE["twitter"], "locale": SITE["locale"], "jsonld": "{}",
        "nav": nav_html(), "body_class": "is-page",
        "content": '<header class="page-head"><h1>Nothing here</h1><p class="hero-dek">Some things were meant to stay lost. This one probably wasn\'t. <a href="/">Return to the entrance</a>.</p></header>',
        "year": datetime.now().year, "site_url": SITE["url"], "tagline": esc(SITE["tagline"]),
    }), encoding="utf-8")

    # ---- sitemap
    urls = [(SITE["url"] + "/", "1.0"), (SITE["url"] + "/archive/", "0.6"),
            (SITE["url"] + "/about/", "0.5")]
    urls += [(p["url"], "0.8") for p in posts]
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

    items = "\n".join(f"""  <item>
    <title>{esc(p['title'])}</title>
    <link>{p['url']}</link>
    <guid isPermaLink="true">{p['url']}</guid>
    <pubDate>{rfc822(p['dt'])}</pubDate>
    <category>{esc(CATEGORIES[p['category']])}</category>
    <description>{esc(p['description'])}</description>
  </item>""" for p in reversed(posts))

    (DIST / "feed.xml").write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
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
