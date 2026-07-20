"""Describe embedded images/charts with Gemini Vision -> searchable text.

Charts, diagrams and infographics carry information the text layer doesn't. We
render each meaningful embedded image to PNG and ask Gemini for a description,
stored as a chunk_type='image_desc' chunk so it's retrievable like any text.
"""
from __future__ import annotations

import base64
import logging

import httpx

from ..config import settings

log = logging.getLogger(__name__)

MODEL = "gemini-2.5-flash"
_BASE = "https://generativelanguage.googleapis.com/v1beta"
_TIMEOUT = httpx.Timeout(60.0)
_MIN_DIM = 150          # skip icons / bullets / logos
_MAX_IMAGES = 8         # cap Gemini calls per document
_MAX_PIXELS = 4_000_000  # downscale huge scans before sending
_MIN_DRAWINGS = 20      # a page with this many vector paths is "designed" (charts/cards)
_PAGE_DPI = 170         # render DPI — high enough for vision to read dense text

_PROMPT = (
    "This image is a page or chart from a document a user will ask questions about. "
    "Transcribe and describe ALL informative content so it is searchable:\n"
    "- Every heading, label, plan/tier name, and feature listed.\n"
    "- EVERY number, price, percentage, and currency amount, EXACTLY as shown "
    "(include the currency symbol you actually see, e.g. ₹, $, €).\n"
    "- For charts: the type, axes, legend, and the values of each series.\n"
    "Be thorough and specific — do not summarize away the details. "
    "If it is only a logo or purely decorative, reply with exactly: DECORATIVE."
)


def _extract_pngs(data: bytes) -> list[tuple[int, bytes]]:
    """PNGs worth describing: embedded raster images, plus whole pages that are
    heavily vector-drawn (charts/infographics/designed layouts).

    Rendering designed pages also sidesteps font-cmap corruption — e.g. a page
    whose embedded font extracts the rupee sign as 'I' renders the real glyph in
    pixels, which vision reads correctly. Deduped and capped by page.
    """
    import fitz

    jobs: list[tuple[int, bytes]] = []
    pages_used: set[int] = set()
    seen_xref: set[int] = set()

    with fitz.open(stream=data, filetype="pdf") as doc:
        # 1) embedded raster images
        for pno in range(len(doc)):
            for img in doc.get_page_images(pno, full=True):
                xref = img[0]
                if xref in seen_xref:
                    continue
                seen_xref.add(xref)
                try:
                    pix = fitz.Pixmap(doc, xref)
                    if pix.width < _MIN_DIM or pix.height < _MIN_DIM:
                        continue
                    if pix.n - pix.alpha >= 4:  # CMYK -> RGB
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    jobs.append((pno + 1, pix.tobytes("png")))
                    pages_used.add(pno + 1)
                except Exception:
                    continue
                if len(jobs) >= _MAX_IMAGES:
                    return jobs

        # 2) heavily vector-drawn pages -> render the whole page
        for pno in range(len(doc)):
            if (pno + 1) in pages_used:
                continue
            try:
                if len(doc[pno].get_drawings()) < _MIN_DRAWINGS:
                    continue
                png = doc[pno].get_pixmap(dpi=_PAGE_DPI).tobytes("png")
                jobs.append((pno + 1, png))
            except Exception:
                continue
            if len(jobs) >= _MAX_IMAGES:
                break
    return jobs


async def _describe(client: httpx.AsyncClient, png: bytes) -> str | None:
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": _PROMPT},
                    {"inline_data": {"mime_type": "image/png",
                                     "data": base64.b64encode(png).decode()}},
                ],
            }
        ],
        # thinkingBudget 0 disables 2.5-flash's reasoning tokens, which otherwise
        # eat the output budget and truncate the transcription.
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 1200,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    r = await client.post(
        f"{_BASE}/models/{MODEL}:generateContent",
        headers={"Content-Type": "application/json", "x-goog-api-key": settings.gemini_api_key},
        json=payload,
    )
    if r.status_code != 200:
        log.warning("Gemini vision %s: %s", r.status_code, r.text[:150])
        return None
    parts = r.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text or text.upper().startswith("DECORATIVE"):
        return None
    return text


async def describe_document_images(data: bytes) -> list[tuple[int, str]]:
    """Return (page_number, description) for each meaningful image. Best-effort."""
    if not settings.gemini_api_key:
        return []
    try:
        jobs = _extract_pngs(data)
    except Exception:
        log.exception("image extraction failed")
        return []
    if not jobs:
        return []

    out: list[tuple[int, str]] = []
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        for page, png in jobs:
            try:
                if desc := await _describe(client, png):
                    out.append((page, desc))
            except Exception:
                log.exception("vision describe failed on page %d", page)
    return out
