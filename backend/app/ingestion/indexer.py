"""Ingestion pipeline: download -> parse -> chunk -> embed -> index."""
from __future__ import annotations

import logging

from ..services import supa
from . import parser
from .chunker import chunk_text
from .embedder import embed_texts

log = logging.getLogger(__name__)

# PostgREST wants a pgvector value as its string literal form.
def _vec(values: list[float]) -> str:
    return "[" + ",".join(f"{v:.6f}" for v in values) + "]"


async def ingest_document(document_id: str, workspace_id: str, storage_path: str, filename: str) -> None:
    """Run the full pipeline and flip the document to 'ready' (or 'failed')."""
    try:
        data = await supa.download(storage_path)
        parsed = parser.parse(data, filename)

        rows: list[dict] = []
        idx = 0

        for page in parsed.pages:
            if not page.text:
                continue  # scanned page -> OCR fallback lands in Phase 4
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

        if not rows:
            raise ValueError("No extractable text found (the file may be scanned — OCR arrives in Phase 4)")

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
                "has_images": False,  # Phase 4: vision
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
