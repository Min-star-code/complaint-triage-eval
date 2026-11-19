"""Render the mail_scan complaints as fake scanned letters (PNG / JPG / image-only PDF).

The pipeline never sees the transcription in complaints.json for these items: it must OCR
the image. The transcription is kept only to measure OCR character error rate.

Run once; outputs are committed under data/scans/.
"""
from __future__ import annotations

import json
import random
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "scans"

FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Courier New.ttf",
    "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
]

# id -> (output format, degradation level)
PLAN = {
    "C051": ("pdf", "mild"),
    "C052": ("png", "mild"),
    "C053": ("pdf", "medium"),
    "C054": ("jpg", "severe"),  # meant to be unreadable by OCR -> full human review
}


def load_font(size: int) -> ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def render(text: str, level: str, seed: int) -> Image.Image:
    rng = random.Random(seed)
    w, h = 1700, 2200  # ~200 dpi letter page
    page = Image.new("L", (w, h), 250)
    draw = ImageDraw.Draw(page)
    font = load_font(34)
    y = 180
    for para in text.split("\n"):
        for line in textwrap.wrap(para, width=62):
            draw.text((150, y), line, fill=25, font=font)
            y += 52
        y += 30

    angle = {"mild": 1.2, "medium": 2.5, "severe": 6.0}[level]
    page = page.rotate(rng.uniform(-angle, angle), resample=Image.BICUBIC, fillcolor=235)

    noise_p = {"mild": 0.004, "medium": 0.015, "severe": 0.12}[level]
    px = page.load()
    for _ in range(int(w * h * noise_p)):
        x, yy = rng.randrange(w), rng.randrange(h)
        px[x, yy] = rng.choice([0, 60, 255])

    blur = {"mild": 0.6, "medium": 1.1, "severe": 3.2}[level]
    page = page.filter(ImageFilter.GaussianBlur(blur))
    if level == "severe":
        # low resolution fax-like copy
        page = page.resize((w // 4, h // 4)).resize((w, h))
    return page


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data = json.loads((ROOT / "data" / "complaints.json").read_text())
    by_id = {c["id"]: c for c in data["complaints"]}
    for i, (cid, (fmt, level)) in enumerate(PLAN.items()):
        img = render(by_id[cid]["text"], level, seed=100 + i)
        path = OUT / f"{cid}.{fmt}"
        if fmt == "pdf":
            img.convert("RGB").save(path, "PDF", resolution=200)
        elif fmt == "jpg":
            img.convert("RGB").save(path, "JPEG", quality=35)
        else:
            img.save(path)
        print("wrote", path.relative_to(ROOT))


if __name__ == "__main__":
    main()
