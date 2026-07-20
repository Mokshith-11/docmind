from app.ingestion.parser import clean_text
from app.retrieval.hybrid import _or_query


def test_or_query_joins_terms_with_or():
    # websearch_to_tsquery ANDs bare words; " or " makes it OR (recall).
    assert _or_query("setup cost") == "setup or cost"


def test_or_query_strips_punctuation_and_stopwordish_symbols():
    assert _or_query("What is the setup cost?") == "What or is or the or setup or cost"


def test_or_query_handles_empty():
    assert _or_query("") == ""
    assert _or_query("???") == ""


def test_clean_text_removes_control_chars():
    assert "\x13" not in clean_text("bullet\x13 item")
    assert clean_text("bullet\x13 item") == "bullet  item".replace("  ", "  ")


def test_clean_text_preserves_real_punctuation():
    # en-dash and normal text must survive
    out = clean_text("40–80 calls per day")
    assert "–" in out
    assert "calls per day" in out


def test_clean_text_collapses_blank_runs():
    assert clean_text("a\n\n\n\n\nb") == "a\n\nb"


def test_clean_text_drops_replacement_char():
    assert "�" not in clean_text("price� here")
