#!/usr/bin/env python3
"""
Make realistic shirt mockups for the flash-sale page.

Places each design onto a photo of a blank tee and lets the fabric's folds and
shadows show through the print, so it looks printed on. Only the mockup images
are new: the original art files are read, never written.

    python3 tools/shirt-mockups/make_mockups.py            # uses config.json next to this file

config.json:
  blank      photo containing the blank shirts (path relative to the repo root)
  out_dir    where mockups are written (e.g. shirts/img/mockups)
  out_width  width of each finished mockup in pixels
  shirts     per color: "crop" = [x0, y0, x1, y1] box around that shirt in the photo,
             "print" = [x, y, w, h] largest print area on the chest (photo pixels);
             art is scaled to fit inside it, centered left-right and aligned to the top
  designs    id -> art file (same ids as CONFIG.designs in shirts/index.html)
"""
import json, os, sys
import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
INK_OPACITY = 0.97        # a touch of fabric shows through, like real ink
SHADE_RANGE = (0.72, 1.18)


def shading_map(blank_rgb):
    """Fold/shadow pattern of the fabric: local brightness relative to its surroundings."""
    gray = blank_rgb.convert("L")
    fine = np.asarray(gray.filter(ImageFilter.GaussianBlur(1.2)), dtype=np.float32) + 4
    broad = np.asarray(gray.filter(ImageFilter.GaussianBlur(45)), dtype=np.float32) + 4
    return np.clip(fine / broad, *SHADE_RANGE)


def place(art, box):
    """Scale art to fit inside box (x, y, w, h), centered horizontally, top-aligned."""
    x, y, w, h = box
    s = min(w / art.width, h / art.height)
    a = art.resize((max(1, round(art.width * s)), max(1, round(art.height * s))), Image.LANCZOS)
    return a, (round(x + (w - a.width) / 2), round(y))


def mockup(blank, shirt, art):
    photo = blank.convert("RGB")
    shade = shading_map(photo)
    a, (ox, oy) = place(art.convert("RGBA"), shirt["print"])

    base = np.asarray(photo, dtype=np.float32)
    out = base.copy()
    ink = np.asarray(a, dtype=np.float32)
    h, w = ink.shape[:2]
    region = (slice(oy, oy + h), slice(ox, ox + w))
    alpha = ink[..., 3:4] / 255.0 * INK_OPACITY
    printed = np.clip(ink[..., :3] * shade[region][..., None], 0, 255)
    out[region] = printed * alpha + base[region] * (1 - alpha)

    x0, y0, x1, y1 = shirt["crop"]
    return Image.fromarray(out.astype(np.uint8)).crop((x0, y0, x1, y1))


def main(config_path):
    cfg = json.load(open(config_path))
    blank = Image.open(os.path.join(ROOT, cfg["blank"]))
    out_dir = os.path.join(ROOT, cfg["out_dir"])
    os.makedirs(out_dir, exist_ok=True)
    for did, art_path in cfg["designs"].items():
        art = Image.open(os.path.join(ROOT, art_path))
        for color, shirt in cfg["shirts"].items():
            img = mockup(blank, shirt, art)
            img = img.resize((cfg["out_width"], round(img.height * cfg["out_width"] / img.width)), Image.LANCZOS)
            dest = os.path.join(out_dir, f"{did}-{color.lower()}.webp")
            img.save(dest, quality=86, method=6)
            print("wrote", os.path.relpath(dest, ROOT))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "config.json"))
