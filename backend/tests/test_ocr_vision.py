"""OCR + vision degrade gracefully when their dependencies aren't available."""
import app.ingestion.ocr as ocr
import app.ingestion.vision as vision


def test_ocr_no_pages_is_noop():
    assert ocr.ocr_pages(b"", []) == {}


def test_ocr_without_tesseract_returns_empty(monkeypatch):
    # simulate the binary being absent regardless of the host
    monkeypatch.setattr(ocr, "_tesseract_path", lambda: None)
    assert ocr.ocr_pages(b"%PDF-fake", [1, 2, 3]) == {}


def test_ocr_available_reflects_resolution(monkeypatch):
    monkeypatch.setattr(ocr, "_tesseract_path", lambda: None)
    assert ocr.ocr_available() is False
    monkeypatch.setattr(ocr, "_tesseract_path", lambda: r"C:\fake\tesseract.exe")
    assert ocr.ocr_available() is True


async def test_vision_no_key_returns_empty(monkeypatch):
    monkeypatch.setattr(vision.settings, "gemini_api_key", "")
    assert await vision.describe_document_images(b"%PDF-fake") == []


async def test_vision_no_images_returns_empty(monkeypatch):
    monkeypatch.setattr(vision.settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(vision, "_extract_pngs", lambda data: [])
    assert await vision.describe_document_images(b"%PDF-fake") == []
