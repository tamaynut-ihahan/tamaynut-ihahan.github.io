#!/usr/bin/env python3
"""Generate lightweight WebP copies of every image in assets/img/.

  assets/img/sm/<name>.webp  – max 640px wide (cards, article images, faces)
  assets/img/xs/<name>.webp  – max 240px wide (news-list thumbnails)
  assets/img/logo.webp       – 300px wide header/footer logo
  assets/img/hero.webp       – full-size hero

The originals stay untouched: they are still used for zoom (lightbox) and sharing.
Usage:  pip install pillow && python3 tools/make_images.py
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "assets" / "img"
SIZES = {"sm": 640, "xs": 240}


def save(im, dest, width, quality=74):
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    dest.parent.mkdir(exist_ok=True)
    im.save(dest, "WEBP", quality=quality, method=6)
    print(f"{dest.relative_to(ROOT)}  {im.width}x{im.height}  {dest.stat().st_size // 1024} KiB")


for src in sorted(IMG.glob("*")):
    if not src.is_file() or src.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        continue
    if src.stem in {"logo", "hero"} and src.suffix == ".webp":
        continue
    im = Image.open(src)
    im = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB")
    if src.stem == "logo":
        save(im, IMG / "logo.webp", 300, quality=85)
        continue
    if src.stem == "hero":
        save(im, IMG / "hero.webp", 1080, quality=70)
    for folder, width in SIZES.items():
        if src.stem == "hero" and folder == "xs":
            continue
        save(im, IMG / folder / f"{src.stem}.webp", width)
