#!/usr/bin/env python3
"""Generate 1200x630 social share cards for every post.

When a link is shared to Reddit, Bluesky, Facebook or Slack, the preview image
decides whether anyone clicks. A raw photo crop reads as generic; a card with
the headline on it reads as an article. This builds one per post from its hero
image, darkened, with the title and brand set over it.

Run after fetch/optimise:  python tools/make_share_images.py
"""

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

ROOT = Path(__file__).parent.parent
IMG = ROOT / "static" / "img"
MANIFEST = ROOT / "content" / "images.json"
POSTS = ROOT / "content" / "posts"

W, H = 1200, 630
MARGIN = 72
GOLD = (201, 162, 39)
CREAM = (237, 232, 240)
DIM = (150, 143, 158)

# Serif faces worth trying, best first. Falls back to PIL's bitmap font, which
# is ugly but never crashes the build.
FONT_CANDIDATES = [
    "C:/Windows/Fonts/georgiab.ttf", "C:/Windows/Fonts/georgia.ttf",
    "C:/Windows/Fonts/constanb.ttf", "C:/Windows/Fonts/times.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "/System/Library/Fonts/Georgia.ttf",
]
SANS_CANDIDATES = [
    "C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def load_font(candidates, size):
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def wrap(draw, text, font, max_w):
    words, lines, line = text.split(), [], []
    for word in words:
        trial = " ".join(line + [word])
        if draw.textlength(trial, font=font) <= max_w or not line:
            line.append(word)
        else:
            lines.append(" ".join(line))
            line = [word]
    if line:
        lines.append(" ".join(line))
    return lines


def titles_from_posts():
    """Read slug -> title straight from the post metadata headers."""
    import re
    out = {}
    for path in POSTS.glob("*.html"):
        m = re.match(r"^<!--META\s*(\{.*?\})\s*META-->", path.read_text(encoding="utf-8"), re.DOTALL)
        if m:
            meta = json.loads(m.group(1))
            out[meta["slug"]] = meta["title"]
    return out


def build_card(slug, title, hero_path, out_path):
    card = Image.new("RGB", (W, H), (11, 10, 13))

    if hero_path.exists():
        with Image.open(hero_path) as hero:
            hero = hero.convert("RGB")
            scale = max(W / hero.width, H / hero.height)
            hero = hero.resize((round(hero.width * scale), round(hero.height * scale)), Image.LANCZOS)
            left, top = (hero.width - W) // 2, (hero.height - H) // 3
            hero = hero.crop((left, top, left + W, top + H))
            hero = ImageEnhance.Brightness(ImageEnhance.Color(hero).enhance(0.55)).enhance(0.42)
            card.paste(hero, (0, 0))

    # Darken toward the bottom so the headline always has contrast to sit on.
    veil = Image.new("L", (1, H))
    for y in range(H):
        veil.putpixel((0, y), int(20 + 205 * (y / H) ** 1.5))
    veil = veil.resize((W, H))
    card = Image.composite(Image.new("RGB", (W, H), (8, 7, 10)), card, veil.point(lambda v: v // 2 + 40))

    d = ImageDraw.Draw(card)
    d.rectangle([0, 0, W, 5], fill=GOLD)

    kicker = load_font(SANS_CANDIDATES, 22)
    d.text((MARGIN, MARGIN - 8), "V E I L E D   A N T I Q U I T Y", font=kicker, fill=GOLD)

    # Shrink the headline until it fits three lines.
    for size in (66, 60, 54, 48, 43):
        title_font = load_font(FONT_CANDIDATES, size)
        lines = wrap(d, title, title_font, W - MARGIN * 2)
        if len(lines) <= 3:
            break
    lines = lines[:3]

    line_h = size + 14
    y = H - MARGIN - 46 - line_h * len(lines)
    for line in lines:
        d.text((MARGIN + 2, y + 2), line, font=title_font, fill=(0, 0, 0))   # shadow
        d.text((MARGIN, y), line, font=title_font, fill=CREAM)
        y += line_h

    foot = load_font(SANS_CANDIDATES, 21)
    d.text((MARGIN, H - MARGIN - 14), "veiledantiquity.com", font=foot, fill=DIM)

    card.save(out_path, "JPEG", quality=86, optimize=True, progressive=True)
    return out_path.stat().st_size


def main():
    if not MANIFEST.exists():
        print("  no content/images.json - run tools/fetch_images.py first")
        sys.exit(1)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    titles = titles_from_posts()
    total = 0

    for slug, data in manifest.items():
        title = titles.get(slug)
        if not title:
            print(f"  skip {slug} (no post found)")
            continue
        out = IMG / f"{slug}-share.jpg"
        total += build_card(slug, title, IMG / f"{slug}.jpg", out)
        data["share"] = f"/static/img/{slug}-share.jpg"
        print(f"  ok  {slug[:40]:42} {out.stat().st_size // 1024:>4} KB")

    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  {len(titles)} share cards, {total // 1024} KB total")


if __name__ == "__main__":
    main()
