"""Intake: turn a complaint (typed text, scanned PDF, or image) into text plus OCR quality info.

Scans go through Tesseract (pytesseract). If OCR quality is too low the item is marked
unreadable and the pipeline sends it straight to full human review without calling the LLM:
a model summarising garbled text would produce confident nonsense.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from PIL import Image

# Below either threshold the scan is treated as unreadable.
MIN_MEAN_CONFIDENCE = 70.0
MIN_WORDS = 15


@dataclass
class IngestResult:
    text: str
    source: str  # "text" | "pdf_text" | "ocr"
    ocr_confidence: Optional[float] = None  # mean word confidence 0-100
    ocr_words: Optional[int] = None
    readable: bool = True
    note: str = ""


OcrFn = Callable[[Image.Image], tuple[str, float, int]]


def tesseract_ocr(img: Image.Image, lang: str = "eng+fra") -> tuple[str, float, int]:
    """Return (text, mean word confidence, word count)."""
    import pytesseract

    if os.environ.get("TESSERACT_CMD"):  # e.g. a user-level install not on PATH
        pytesseract.pytesseract.tesseract_cmd = os.environ["TESSERACT_CMD"]
    data = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)
    words, confs = [], []
    for w, c in zip(data["text"], data["conf"]):
        c = float(c)
        if w.strip() and c >= 0:
            words.append(w)
            confs.append(c)
    text = pytesseract.image_to_string(img, lang=lang)
    mean = sum(confs) / len(confs) if confs else 0.0
    return text.strip(), mean, len(words)


def _judge(text: str, conf: float, n_words: int) -> IngestResult:
    readable = conf >= MIN_MEAN_CONFIDENCE and n_words >= MIN_WORDS
    note = "" if readable else f"OCR unreadable (mean confidence {conf:.0f}, {n_words} words)"
    return IngestResult(text=text, source="ocr", ocr_confidence=round(conf, 1), ocr_words=n_words,
                        readable=readable, note=note)


def ingest_file(path: Path, ocr: OcrFn = tesseract_ocr) -> IngestResult:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        import pymupdf

        doc = pymupdf.open(path)
        embedded = "\n".join(page.get_text() for page in doc).strip()
        if len(embedded.split()) >= MIN_WORDS:
            return IngestResult(text=embedded, source="pdf_text")
        texts, confs, total = [], [], 0
        for page in doc:  # image-only PDF: rasterise each page and OCR it
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            t, c, n = ocr(img)
            texts.append(t)
            confs.append(c * n)
            total += n
        mean = sum(confs) / total if total else 0.0
        return _judge("\n".join(texts), mean, total)
    if suffix in (".png", ".jpg", ".jpeg", ".tif", ".tiff"):
        t, c, n = ocr(Image.open(path))
        return _judge(t, c, n)
    if suffix == ".txt":
        return IngestResult(text=path.read_text(), source="text")
    raise ValueError(f"unsupported file type: {path}")


def ingest_item(item: dict, scans_dir: Path, ocr: OcrFn = tesseract_ocr) -> IngestResult:
    """Typed complaints use their text; mail scans must be read from the image only."""
    if item["channel"] == "mail_scan":
        hits = sorted(scans_dir.glob(f"{item['id']}.*"))
        if not hits:
            return IngestResult(text="", source="ocr", readable=False, note="scan file missing")
        return ingest_file(hits[0], ocr=ocr)
    return IngestResult(text=item["text"], source="text")
