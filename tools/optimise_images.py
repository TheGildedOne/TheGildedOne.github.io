#!/usr/bin/env python3
"""Resize and recompress the downloaded images, and update their manifest dimensions.

Page weight is a ranking signal and these arrive from Commons far larger than a
blog needs. Run after fetch_images.py:  python tools/optimise_images.py
"""

import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).parent.parent
IMG = ROOT / "static" / "img"
MANIFEST = ROOT / "content" / "images.json"

MAX_W = 1400
QUALITY = 80


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    before = after = 0

    for slug, data in manifest.items():
        path = IMG / f"{slug}.jpg"
        if not path.exists():
            print(f"  missing {slug}")
            continue

        start = path.stat().st_size
        before += start

        with Image.open(path) as im:
            im = im.convert("RGB")
            if im.width > MAX_W:
                h = round(im.height * MAX_W / im.width)
                im = im.resize((MAX_W, h), Image.LANCZOS)
            im.save(path, "JPEG", quality=QUALITY, optimize=True, progressive=True)
            data["width"], data["height"] = im.width, im.height

        # Small crop for the homepage and archive cards, so the grid does not
        # pull several megabytes of hero images.
        with Image.open(path) as im:
            im = im.convert("RGB")
            tw, th = 520, 300
            scale = max(tw / im.width, th / im.height)
            im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
            left, top = (im.width - tw) // 2, (im.height - th) // 3
            im = im.crop((left, top, left + tw, top + th))
            im.save(IMG / f"{slug}-card.jpg", "JPEG", quality=76, optimize=True, progressive=True)
        data["card"] = f"/static/img/{slug}-card.jpg"

        end = path.stat().st_size + (IMG / f"{slug}-card.jpg").stat().st_size
        after += end
        print(f"  {slug:38} {start//1024:>5} -> {end//1024:<5} KB  ({data['width']}x{data['height']})")

    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  total {before//1024} KB -> {after//1024} KB  "
          f"({100 - after * 100 // before}% smaller)")


if __name__ == "__main__":
    main()
