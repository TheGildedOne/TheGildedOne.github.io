#!/usr/bin/env python3
"""Draw the site mark as PNG, at the sizes things other than browsers want.

static/mark.svg is the favicon, and a modern browser needs nothing else. Three
things do: iPhones ignore SVG for the home-screen icon, Google's guidance asks
for a favicon in multiples of 48px, and the Organization logo in the structured
data should be an ordinary raster image.

The shapes are copied from mark.svg by hand, so if the mark ever changes, change
both. Drawn at four times the size and scaled down, which is what smooths the
edges. Run once; the output is committed.

  python tools/make_icons.py
"""

from pathlib import Path

from PIL import Image, ImageDraw

STATIC = Path(__file__).parent.parent / "static"
INK, GOLD = (11, 10, 13), (201, 162, 39)
SIZES = (512, 192, 180)

# mark.svg uses a 64-unit canvas.
STAR = [(32, 11), (37.5, 26.5), (53, 32), (37.5, 37.5), (32, 53), (26.5, 37.5),
        (11, 32), (26.5, 26.5)]


def draw(size: int) -> Image.Image:
    big = size * 4
    k = big / 64
    img = Image.new("RGB", (big, big), INK)
    d = ImageDraw.Draw(img)
    d.ellipse([(32 - 21) * k, (32 - 21) * k, (32 + 21) * k, (32 + 21) * k],
              outline=GOLD, width=max(1, round(1.6 * k)))
    d.polygon([(x * k, y * k) for x, y in STAR], fill=GOLD)
    d.ellipse([(32 - 4.2) * k, (32 - 4.2) * k, (32 + 4.2) * k, (32 + 4.2) * k], fill=INK)
    return img.resize((size, size), Image.LANCZOS)


def main():
    for size in SIZES:
        out = STATIC / f"icon-{size}.png"
        draw(size).save(out, optimize=True)
        print(f"  {out.name}  {out.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
