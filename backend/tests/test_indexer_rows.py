"""Guard the PostgREST bulk-insert contract.

PostgREST rejects a bulk insert whose objects don't all carry identical keys
(PGRST102 "All object keys must match"). Text chunks omit table_json while table
chunks set it, so text rows must send an explicit null.
"""
from app.ingestion.parser import Page, Parsed, Table


def build_rows(parsed: Parsed, document_id: str, workspace_id: str) -> list[dict]:
    """Mirrors the row construction in indexer.ingest_document."""
    from app.ingestion.chunker import chunk_text

    rows: list[dict] = []
    idx = 0
    for page in parsed.pages:
        if not page.text:
            continue
        for ch in chunk_text(page.text):
            rows.append(
                {
                    "document_id": document_id,
                    "workspace_id": workspace_id,
                    "content": ch.content,
                    "page": page.number,
                    "chunk_index": idx,
                    "chunk_type": "text",
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
    return rows


def _mixed_doc() -> Parsed:
    return Parsed(
        pages=[Page(number=1, text="A paragraph about payment terms and delivery.")],
        tables=[Table(page=1, rows=[["Item", "Cost"], ["Setup", "$500"]])],
    )


def test_text_and_table_rows_share_identical_keys():
    rows = build_rows(_mixed_doc(), "doc-1", "ws-1")
    assert len(rows) >= 2
    keysets = {frozenset(r) for r in rows}
    assert len(keysets) == 1, f"bulk insert would 400 (PGRST102); got {keysets}"


def test_text_rows_carry_explicit_null_table_json():
    rows = build_rows(_mixed_doc(), "doc-1", "ws-1")
    text_rows = [r for r in rows if r["chunk_type"] == "text"]
    assert text_rows
    for r in text_rows:
        assert "table_json" in r and r["table_json"] is None


def test_chunk_indexes_are_contiguous_across_types():
    rows = build_rows(_mixed_doc(), "doc-1", "ws-1")
    assert [r["chunk_index"] for r in rows] == list(range(len(rows)))


def test_table_markdown_renders_header_and_body():
    md = Table(page=2, rows=[["Item", "Cost"], ["Setup", "$500"]]).to_markdown()
    assert "| Item | Cost |" in md
    assert "| Setup | $500 |" in md
