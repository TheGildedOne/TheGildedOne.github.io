#!/usr/bin/env python3
"""Encode responsive AVIF variants alongside every JPEG.

The hero image is roughly 85% of a post's page weight, so it is the whole
Largest Contentful Paint story. Two things fix it:

  format  - AVIF is ~45% smaller than the same JPEG at matched quality.
            (WebP was measured too and came out *larger* than these already
            optimised JPEGs on several images, so it is deliberately not shipped.)
  width   - the hero renders inside a 68ch column, about 700 CSS px. The 1400px
            file only ever serves high-DPI screens; a 1x display should not
            download four times the pixels it can show.

The original JPEG stays as the fallback for older browsers and as the social
preview format, since not every link scraper decodes AVIF.

Run after optimise_images.py:  python tools/modern_images.py
"""

import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).parent.parent
IMG = ROOT / "static" / "img"
MANIFEST = ROOT / "content" / "images.json"

AVIF_Q = 55          # visually indistinguishable from JPEG 80 on photographs
HALF_W = 700         # matches the article column; 1x displays stop here


def encode(src: Path):
    """Write full-width and half-width AVIF for one JPEG. Returns their sizes."""
    full = src.with_suffix(".avif")
    half = src.with_name(f"{src.stem}-700.avif")

    with Image.open(src) as im:
        im = im.convert("RGB")
        if not full.exists():
            im.save(full, "AVIF", quality=AVIF_Q)
        if not half.exists():
            if im.width > HALF_W:
                h = round(im.height * HALF_W / im.width)
                im.resize((HALF_W, h), Image.LANCZOS).save(half, "AVIF", quality=AVIF_Q)
            else:
                im.save(half, "AVIF", quality=AVIF_Q)

    return full.stat().st_size, half.stat().st_size


def main():
    if not MANIFEST.exists():
        print("  no content/images.json - run tools/fetch_images.py first")
        sys.exit(1)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    jpeg_total = avif_total = half_total = 0

    for slug, data in manifest.items():
        src = IMG / f"{slug}.jpg"
        if not src.exists():
            continue
        jpg = src.stat().st_size
        full, half = encode(src)
        jpeg_total += jpg
        avif_total += full
        half_total += half

        data["avif"] = f"/static/img/{slug}.avif"
        data["avif_700"] = f"/static/img/{slug}-700.avif"
        print(f"  {slug[:36]:38} jpg {jpg//1024:>4} -> avif {full//1024:>3} KB "
              f"(700px: {half//1024:>3} KB)")

    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    if jpeg_total:
        print(f"\n  full width : {jpeg_total//1024} KB jpeg -> {avif_total//1024} KB avif "
              f"({100 - avif_total * 100 // jpeg_total}% smaller)")
        print(f"  what a 1x phone actually downloads: {half_total//1024} KB "
              f"({100 - half_total * 100 // jpeg_total}% smaller than today)")


if __name__ == "__main__":
    main()
