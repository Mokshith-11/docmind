from app.ingestion.chunker import (
    TARGET_TOKENS,
    chunk_text,
    estimate_tokens,
    is_heading,
)


def test_empty_text_yields_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   \n  ") == []


def test_short_text_is_one_chunk():
    chunks = chunk_text("A short paragraph about termination clauses.")
    assert len(chunks) == 1
    assert chunks[0].index == 0
    assert "termination" in chunks[0].content


def test_long_text_splits_into_multiple_chunks_within_target():
    para = "The vendor shall deliver the goods within thirty days of the order. " * 120
    chunks = chunk_text(para)
    assert len(chunks) > 1
    # allow a little slack for the overlap carried into each chunk
    for c in chunks:
        assert estimate_tokens(c.content) <= TARGET_TOKENS * 1.35


def test_chunks_are_indexed_in_order():
    text = "Sentence number one here. " * 400
    chunks = chunk_text(text)
    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_consecutive_chunks_overlap():
    text = "Clause about liability and indemnity obligations. " * 200
    chunks = chunk_text(text)
    assert len(chunks) >= 2
    tail = chunks[0].content[-60:].strip()
    # some trailing fragment of chunk 0 should reappear at the head of chunk 1
    assert any(w in chunks[1].content[:200] for w in tail.split()[:4])


def test_heading_starts_a_new_chunk():
    body = "This section explains the payment schedule in detail. " * 30
    text = f"{body}\n\n## Termination\n\nEither party may terminate with notice."
    chunks = chunk_text(text)
    assert any(c.content.lstrip().startswith("## Termination") for c in chunks)


def test_is_heading_recognises_forms():
    assert is_heading("## Termination")
    assert is_heading("3.1 Payment Terms")
    assert is_heading("TERMINATION")
    assert is_heading("Payment Terms")
    assert not is_heading("The vendor shall deliver the goods within thirty days.")
    assert not is_heading("")


def test_oversized_single_block_is_split():
    # one block, no paragraph breaks, far over target
    block = "word " * 4000
    chunks = chunk_text(block)
    assert len(chunks) > 1
