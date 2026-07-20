"""OCR fallback for scanned pages (Tesseract via pytesseract).

Tesseract is a system binary, not a pip package. If it isn't installed, OCR
degrades to a no-op with a one-time hint rather than failing ingestion — the
scanned pages simply stay unread until the binary is available.

Install (Windows): https://github.com/UB-Mannheim/tesseract/wiki
Then either add it to PATH or set TESSERACT_CMD in the environment.
"""
from __future__ import annotations

import io
import logging
import os
import shutil

log = logging.getLogger(__name__)

_OCR_DPI = 200
_resolved: str | None = None
_checked = False
_warned = False


def _tesseract_path() -> str | None:
    global _resolved, _checked
    if _checked:
        return _resolved
    _checked = True
    candidates = [
        os.environ.get("TESSERACT_CMD"),
        shutil.which("tesseract"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    _resolved = next((p for p in candidates if p and os.path.exists(p)), None)
    return _resolved


def ocr_available() -> bool:
    return _tesseract_path() is not None


def ocr_pages(data: bytes, page_numbers: list[int]) -> dict[int, str]:
    """OCR the given 1-based page numbers. Returns {page: text} for pages with text."""
    global _warned
    if not page_numbers:
        return {}
    path = _tesseract_path()
    if not path:
        if not _warned:
            log.warning(
                "Tesseract not installed — skipping OCR for %d scanned page(s). "
                "Install from https://github.com/UB-Mannheim/tesseract/wiki",
                len(page_numbers),
            )
            _warned = True
        return {}

    import fitz
    import pytesseract
    from PIL import Image

    pytesseract.pytesseract.tesseract_cmd = path
    out: dict[int, str] = {}
    with fitz.open(stream=data, filetype="pdf") as doc:
        for n in page_numbers:
            if not (1 <= n <= len(doc)):
                continue
            pix = doc[n - 1].get_pixmap(dpi=_OCR_DPI)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            text = pytesseract.image_to_string(img).strip()
            if len(text) >= 20:
                out[n] = text
    return out
