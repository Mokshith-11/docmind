"""Semantic chunking: ~500 tokens with ~50 token overlap, respecting headings.

Pure functions — no I/O — so this is unit-testable (see tests/test_chunker.py).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

TARGET_TOKENS = 500
OVERLAP_TOKENS = 50

# Rough but stable: English averages ~4 characters per token.
_CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // _CHARS_PER_TOKEN)


_HEADING_MD = re.compile(r"^\s{0,3}#{1,6}\s+\S")
_HEADING_NUM = re.compile(r"^\s*\d+(\.\d+)*\.?\s+[A-Z][^.!?]{0,78}$")


def is_heading(line: str) -> bool:
    """Markdown heading, numbered section, or a short title-ish line with no terminal period."""
    s = line.strip()
    if not s or len(s) > 90:
        return False
    if _HEADING_MD.match(s) or _HEADING_NUM.match(s):
        return True
    if s.endswith((".", "!", "?", ",", ";")):
        return False
    words = s.split()
    if len(words) > 12:
        return False
    if s.isupper() and len(words) >= 1:
        return True
    # Title Case with no sentence punctuation
    caps = sum(1 for w in words if w[:1].isupper())
    return len(words) >= 2 and caps / len(words) >= 0.6


@dataclass
class Chunk:
    content: str
    index: int


def _blocks(text: str) -> list[str]:
    """Split into paragraph blocks, keeping headings as their own block."""
    out: list[str] = []
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        lines = para.split("\n")
        buf: list[str] = []
        for ln in lines:
            if is_heading(ln):
                if buf:
                    out.append("\n".join(buf).strip())
                    buf = []
                out.append(ln.strip())
            else:
                buf.append(ln)
        if buf:
            out.append("\n".join(buf).strip())
    return [b for b in out if b]


def _tail_overlap(text: str, overlap_tokens: int) -> str:
    """Last ~overlap_tokens worth of text, cut on a word boundary."""
    if overlap_tokens <= 0:
        return ""
    chars = overlap_tokens * _CHARS_PER_TOKEN
    if len(text) <= chars:
        return text
    tail = text[-chars:]
    sp = tail.find(" ")
    return tail[sp + 1 :] if sp != -1 else tail


def chunk_text(
    text: str,
    target_tokens: int = TARGET_TOKENS,
    overlap_tokens: int = OVERLAP_TOKENS,
) -> list[Chunk]:
    """Group blocks into ~target_tokens chunks. A heading starts a new chunk."""
    if not text or not text.strip():
        return []

    chunks: list[str] = []
    cur = ""

    def flush() -> None:
        nonlocal cur
        if cur.strip():
            chunks.append(cur.strip())
        cur = ""

    for block in _blocks(text):
        heading = is_heading(block)
        # A heading opens a new chunk, but don't leave a chunk that's only a heading.
        if heading and cur and estimate_tokens(cur) > overlap_tokens:
            flush()

        candidate = f"{cur}\n\n{block}".strip() if cur else block
        if estimate_tokens(candidate) <= target_tokens:
            cur = candidate
            continue

        # Candidate overflows: close current, carry overlap into the next chunk.
        if cur:
            prev = cur
            flush()
            cur = _tail_overlap(prev, overlap_tokens)
            cur = f"{cur}\n\n{block}".strip() if cur else block
        else:
            cur = block

        # A single block bigger than target: split it on sentence boundaries.
        while estimate_tokens(cur) > target_tokens:
            cut = _split_point(cur, target_tokens)
            if cut <= 0:
                break
            head, rest = cur[:cut].strip(), cur[cut:].strip()
            if not head:
                break
            chunks.append(head)
            overlap = _tail_overlap(head, overlap_tokens)
            cur = f"{overlap} {rest}".strip() if overlap else rest

    flush()
    return [Chunk(content=c, index=i) for i, c in enumerate(chunks)]


def _split_point(text: str, target_tokens: int) -> int:
    """Index to cut at: last sentence end before the target, else a word boundary."""
    limit = min(len(text), target_tokens * _CHARS_PER_TOKEN)
    window = text[:limit]
    m = list(re.finditer(r"[.!?]\s", window))
    if m:
        return m[-1].end()
    sp = window.rfind(" ")
    return sp if sp > 0 else limit
