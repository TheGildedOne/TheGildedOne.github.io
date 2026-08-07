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

    # 3b. every srcset candidate resolves (a typo here fails silently in the browser)
    for srcset in re.findall(r'srcset="([^"]+)"', html):
        for candidate in srcset.split(","):
            url = candidate.strip().split()[0]
            checked += 1
            if url.startswith("/") and not (DIST / url.lstrip("/")).exists():
                errors.append(f"{rel}: missing srcset image {url}")

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

print(f"{len(pages)} pages, {checked} assertions.")
if errors:
    print(f"\n{len(errors)} PROBLEM(S):")
    for e in errors:
        print("  -", e)
    sys.exit(1)
print("All checks passed.")
