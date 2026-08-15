#!/usr/bin/env python3
"""Post-build validation: internal links, JSON-LD, and required SEO tags."""
import json
import re
import sys
from pathlib import Path

DIST = Path(__file__).parent / "dist"
errors, checked = [], 0

# Files dropped in public/ land at the site root untouched (search-engine
# verification files and the like). They are not pages and have no SEO tags,
# so they are not validated as pages.
GENERATED_AT_ROOT = {"index.html", "404.html"}
pages = [p for p in sorted(DIST.rglob("*.html"))
         if p.parent != DIST or p.name in GENERATED_AT_ROOT]
posts_dir = DIST / "posts"
slugs = {p.name for p in posts_dir.iterdir() if p.is_dir()} if posts_dir.exists() else set()

for page in pages:
    rel = page.relative_to(DIST).as_posix()
    html = page.read_text(encoding="utf-8")

    # 1. required SEO tags
    for label, pattern in [
        ("<title>", r"<title>[^<]{10,}</title>"),
        ("meta description", r'<meta name="description" content="[^"]{20,}"'),
        ("canonical", r'<link rel="canonical" href="https://[^"]+"'),
        ("og:title", r'<meta property="og:title"'),
        ("h1", r"<h1[^>]*>"),
    ]:
        if not re.search(pattern, html):
            errors.append(f"{rel}: missing {label}")
        checked += 1

    # exactly one h1
    if len(re.findall(r"<h1[^>]*>", html)) != 1:
        errors.append(f"{rel}: expected exactly one <h1>")

    # 2. JSON-LD parses
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL):
        checked += 1
        try:
            json.loads(block)
        except json.JSONDecodeError as e:
            errors.append(f"{rel}: invalid JSON-LD ({e})")

    # 3. every image resolves, has alt, and is dimensioned (no layout shift)
    for tag in re.findall(r"<img\b[^>]*>", html):
        checked += 1
        src = re.search(r'src="([^"]+)"', tag)
        if not src:
            errors.append(f"{rel}: <img> with no src")
            continue
        if src.group(1).startswith("/"):
            if not (DIST / src.group(1).lstrip("/")).exists():
                errors.append(f"{rel}: missing image {src.group(1)}")
        if 'alt="' not in tag:
            errors.append(f"{rel}: <img> missing alt ({src.group(1)})")
        if 'width="' not in tag or 'height="' not in tag:
            errors.append(f"{rel}: <img> missing width/height ({src.group(1)})")

    # 3a. block tags balance. Browsers silently repair an unclosed <p>, so a
    # malformed post looks fine locally and ships broken structure to crawlers.
    for tag in ("p", "ul", "ol", "li", "figure", "section", "blockquote", "picture"):
        opens = len(re.findall(rf"<{tag}[\s>]", html))
        closes = len(re.findall(rf"</{tag}>", html))
        checked += 1
        if opens != closes:
            errors.append(f"{rel}: unbalanced <{tag}> ({opens} open, {closes} close)")

    # 3b. every srcset candidate resolves (a typo here fails silently in the browser)
    for srcset in re.findall(r'srcset="([^"]+)"', html):
        for candidate in srcset.split(","):
            url = candidate.strip().split()[0]
            checked += 1
            if url.startswith("/") and not (DIST / url.lstrip("/")).exists():
                errors.append(f"{rel}: missing srcset image {url}")

    # 3c. Post pages must actually use the derived image variants. These degrade
    # silently — if the manifest loses its avif/share keys the templates simply
    # stop emitting them, every other check still passes, and the site quietly
    # serves 8x heavier heroes and plain photos as social previews.
    if rel.startswith("posts/"):
        checked += 2
        if "image/avif" not in html:
            errors.append(f"{rel}: no AVIF <source> — image manifest is probably missing "
                          f"avif keys (re-run tools/modern_images.py)")
        og = re.search(r'<meta property="og:image" content="([^"]+)"', html)
        if og and not og.group(1).endswith("-share.jpg"):
            errors.append(f"{rel}: og:image is not a share card ({og.group(1).split('/')[-1]}) "
                          f"— re-run tools/make_share_images.py")

    # 4. social preview image is an absolute URL that exists locally
    og = re.search(r'<meta property="og:image" content="([^"]+)"', html)
    if og:
        checked += 1
        if not og.group(1).startswith("https://"):
            errors.append(f"{rel}: og:image is not absolute")
        else:
            local = og.group(1).split("/", 3)[-1]
            if not (DIST / local).exists():
                errors.append(f"{rel}: og:image target missing ({local})")

    # 5. internal links resolve
    for href in re.findall(r'href="(/[^"#?]*)', html):
        checked += 1
        if href.startswith("/static/"):
            target = DIST / href.lstrip("/")
            if not target.exists():
                errors.append(f"{rel}: dead asset {href}")
        elif href.startswith("/posts/"):
            slug = href.strip("/").split("/", 1)[1]
            if slug not in slugs:
                errors.append(f"{rel}: dead post link {href}")
        elif href in ("/", "/start-here/", "/archive/", "/about/", "/contact/", "/privacy/",
                      "/disclosure/", "/feed.xml", "/sitemap.xml", "/robots.txt"):
            pass
        elif href.startswith("/category/"):
            if not (DIST / href.strip("/")).exists():
                errors.append(f"{rel}: dead category link {href}")
        else:
            errors.append(f"{rel}: unrecognised internal link {href}")

# 6. every post is linked from the homepage
home = (DIST / "index.html").read_text(encoding="utf-8")
for slug in slugs:
    if f'href="/posts/{slug}/"' not in home:
        errors.append(f"index.html: post not linked from homepage: {slug}")

# 7. no em dashes in posts written from now on.
#
# Imran flagged the em dash as an overused tic on 2026-08-13: 461 of them across
# the 29 posts written by then. Those are grandfathered deliberately - rewriting
# live and scheduled posts would churn a lot of prose for a stylistic preference.
# The rule applies to everything written afterwards.
#
# Gated on the post's own date rather than a slug list, so it needs no upkeep:
# the last post written under the old rule is dated 12 Oct 2026, and any post
# written from here on necessarily gets a later slot.
#
# Catches the &mdash; entity and a literal em dash. En dashes are untouched -
# they carry number and date ranges ("440-430 BCE"), which is correct typography
# and not the habit being complained about.
EM_DASH_FREE_FROM = "2026-10-13"
META_RE = re.compile(r"^<!--META\s*(\{.*?\})\s*META-->", re.DOTALL)
IMAGES_MANIFEST = {}
_img = Path(__file__).parent / "content" / "images.json"
if _img.exists():
    IMAGES_MANIFEST = json.loads(_img.read_text(encoding="utf-8"))
CAPTIONS = {k: (v.get("caption") or "") for k, v in IMAGES_MANIFEST.items()}

for source in sorted((Path(__file__).parent / "content" / "posts").glob("*.html")):
    m = META_RE.match(source.read_text(encoding="utf-8"))
    if not m:
        continue
    meta = json.loads(m.group(1))
    if meta.get("date", "") < EM_DASH_FREE_FROM:
        continue

    checked += 1
    body = source.read_text(encoding="utf-8")
    hits = body.count("&mdash;") + body.count("—")
    if hits:
        errors.append(f"{source.name}: {hits} em dash(es) - not allowed in posts "
                      f"from {EM_DASH_FREE_FROM}. Recast with a comma, colon, "
                      f"bracket or full stop; do not swap in a hyphen or en dash.")

    caption = CAPTIONS.get(meta.get("slug"), "")
    checked += 1
    if "&mdash;" in caption or "—" in caption:
        errors.append(f"{meta['slug']}: em dash in image caption (tools/fetch_images.py PICKS)")

# 8. hero images must be big enough for the slot they fill.
#
# The article column renders the hero at 700px CSS, so a retina screen wants
# 1400px of pixels. Nothing checked this, and the Saturday run of 15 Aug picked
# a 500px coin photo: fine on the Commons page, soft on the site. Two older
# posts have the same problem.
#
# Cutoff is set past the 15 Aug batch on purpose. This is here to stop the
# problem recurring, not to invalidate posts already written and committed, and
# re-sourcing those is a judgement call rather than something a gate should force.
MIN_HERO_W = 1200
BIG_ENOUGH_FROM = "2026-10-20"

for source in sorted((Path(__file__).parent / "content" / "posts").glob("*.html")):
    m = META_RE.match(source.read_text(encoding="utf-8"))
    if not m:
        continue
    meta = json.loads(m.group(1))
    if meta.get("date", "") < BIG_ENOUGH_FROM:
        continue
    img = IMAGES_MANIFEST.get(meta.get("slug"))
    if not img:
        continue
    checked += 1
    w = int(img.get("width") or 0)
    if w < MIN_HERO_W:
        errors.append(f"{meta['slug']}: hero image is only {w}px wide, needs "
                      f"{MIN_HERO_W}px+ (it renders at 700px CSS, so half that "
                      f"is visibly soft on a phone). Pick a larger Commons file.")

print(f"{len(pages)} pages, {checked} assertions.")
if errors:
    print(f"\n{len(errors)} PROBLEM(S):")
    for e in errors:
        print("  -", e)
    sys.exit(1)
print("All checks passed.")
