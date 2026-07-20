"""Reciprocal Rank Fusion — required by CLAUDE.md conventions."""
from app.retrieval.hybrid import RRF_K, reciprocal_rank_fusion


def _row(cid: str, content: str = "x") -> dict:
    return {"id": cid, "document_id": "doc-1", "content": content, "page": 1, "chunk_type": "text"}


def test_empty_input_returns_empty():
    assert reciprocal_rank_fusion([]) == []
    assert reciprocal_rank_fusion([[], []]) == []


def test_single_list_preserves_order():
    ranked = [_row("a"), _row("b"), _row("c")]
    out = reciprocal_rank_fusion([ranked])
    assert [c.id for c in out] == ["a", "b", "c"]


def test_chunk_in_both_lists_outranks_chunk_in_one():
    dense = [_row("a"), _row("b")]
    sparse = [_row("c"), _row("a")]
    out = reciprocal_rank_fusion([dense, sparse])
    # "a" is 1st in dense and 2nd in sparse -> highest fused score
    assert out[0].id == "a"


def test_scores_follow_the_rrf_formula():
    out = reciprocal_rank_fusion([[_row("a"), _row("b")]])
    assert out[0].score == 1.0 / (RRF_K + 1)
    assert out[1].score == 1.0 / (RRF_K + 2)


def test_deduplicates_across_lists():
    dense = [_row("a"), _row("b")]
    sparse = [_row("a"), _row("b")]
    out = reciprocal_rank_fusion([dense, sparse])
    assert len(out) == 2
    assert {c.id for c in out} == {"a", "b"}


def test_respects_limit():
    rows = [_row(str(i)) for i in range(30)]
    out = reciprocal_rank_fusion([rows], limit=5)
    assert len(out) == 5


def test_top_of_each_list_beats_deep_single_hit():
    dense = [_row("top_dense")] + [_row(f"d{i}") for i in range(19)]
    sparse = [_row("top_sparse")] + [_row(f"s{i}") for i in range(19)]
    out = reciprocal_rank_fusion([dense, sparse])
    assert {out[0].id, out[1].id} == {"top_dense", "top_sparse"}


def test_candidate_fields_are_carried_through():
    out = reciprocal_rank_fusion([[{"id": "a", "document_id": "doc-9",
                                    "content": "hello", "page": 7, "chunk_type": "table"}]])
    c = out[0]
    assert (c.document_id, c.content, c.page, c.chunk_type) == ("doc-9", "hello", 7, "table")
