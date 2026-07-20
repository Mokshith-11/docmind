"""Ingestion pipeline: download -> parse -> chunk -> embed -> index."""
from __future__ import annotations

import logging

from ..services import supa
from . import parser
from .chunker import chunk_text
from .embedder import embed_texts
from .ocr import ocr_pages
from .vision import describe_document_images

log = logging.getLogger(__name__)

# PostgREST wants a pgvector value as its string literal form.
def _vec(values: list[float]) -> str:
    return "[" + ",".join(f"{v:.6f}" for v in values) + "]"


async def ingest_document(document_id: str, workspace_id: str, storage_path: str, filename: str) -> None:
    """Run the full pipeline and flip the document to 'ready' (or 'failed')."""
    try:
        data = await supa.download(storage_path)
        parsed = parser.parse(data, filename)

        # OCR fallback: recover text from scanned pages (no-op if Tesseract absent).
        scanned = [p.number for p in parsed.pages if p.needs_ocr]
        ocr_text = ocr_pages(data, scanned) if scanned else {}
        for page in parsed.pages:
            if page.needs_ocr and (t := ocr_text.get(page.number)):
                page.text = t

        rows: list[dict] = []
        idx = 0

        for page in parsed.pages:
            if not page.text:
                continue  # still empty (e.g. scanned page and no OCR available)
            for ch in chunk_text(page.text):
                rows.append(
                    {
                        "document_id": document_id,
                        "workspace_id": workspace_id,
                        "content": ch.content,
                        "page": page.number,
                        "chunk_index": idx,
                        "chunk_type": "text",
                        # Explicit null: PostgREST rejects a bulk insert whose rows
                        # don't all carry identical keys (PGRST102).
                        "table_json": None,
                    }
                )
                idx += 1

        for tbl in parsed.tables:
            md = tbl.to_markdown()
            if not md:
                continue
            rows.append(
                {
                    "document_id": document_id,
                    "workspace_id": workspace_id,
                    "content": md,
                    "page": tbl.page,
                    "chunk_index": idx,
                    "chunk_type": "table",
                    "table_json": {"rows": tbl.rows},
                }
            )
            idx += 1

        # Vision: describe embedded images/charts as searchable image_desc chunks.
        image_descs = await describe_document_images(data)
        for page_no, desc in image_descs:
            rows.append(
                {
                    "document_id": document_id,
                    "workspace_id": workspace_id,
                    "content": desc,
                    "page": page_no,
                    "chunk_index": idx,
                    "chunk_type": "image_desc",
                    "table_json": None,
                }
            )
            idx += 1

        if not rows:
            raise ValueError(
                "No extractable text found. If this is a scanned document, install "
                "Tesseract OCR (https://github.com/UB-Mannheim/tesseract/wiki)."
            )

        vectors = await embed_texts([r["content"] for r in rows])
        for row, vec in zip(rows, vectors):
            row["embedding"] = _vec(vec)

        # Insert in batches so a big document doesn't blow the request size.
        for i in range(0, len(rows), 100):
            await supa.insert("chunks", rows[i : i + 100])

        await supa.update(
            "documents",
            {"id": f"eq.{document_id}"},
            {
                "status": "ready",
                "page_count": parsed.page_count,
                "has_tables": parsed.has_tables,
                "has_images": bool(image_descs),
            },
        )
        log.info("ingested %s: %d chunks", document_id, len(rows))

    except Exception as exc:  # noqa: BLE001 — background task must never crash silently
        log.exception("ingestion failed for %s", document_id)
        try:
            await supa.update("documents", {"id": f"eq.{document_id}"}, {"status": "failed"})
        except Exception:
            log.exception("could not mark %s failed", document_id)
        raise
