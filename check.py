#!/usr/bin/env python3
"""Post-build validation: internal links, JSON-LD, and required SEO tags."""
import json
import re
import sys
from pathlib import Path

DIST = Path(__file__).parent / "dist"
errors, checked = [], 0

pages = sorted(DIST.rglob("*.html"))
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

    # 3. internal links resolve
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
        elif href in ("/", "/archive/", "/about/", "/feed.xml", "/sitemap.xml", "/robots.txt"):
            pass
        else:
            errors.append(f"{rel}: unrecognised internal link {href}")

# 4. every post is linked from the homepage
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
