"""API endpoint tests.

Ollama HTTP calls are mocked via patch.object so no running Ollama instance is
required. The shared httpx client stored in app.state is created during the
lifespan (before respx activates), so we patch httpx.AsyncClient.send at the
class level instead — that covers all instances regardless of creation time.

Tesseract runs for real in the integration-marked test; all other OCR tests
mock extract_text() directly so they work on any platform.
"""

import httpx
import pytest
import respx
from httpx import Response
from unittest.mock import AsyncMock

OLLAMA_CHAT = "http://localhost:11434/api/chat"
OLLAMA_TAGS = "http://localhost:11434/api/tags"

GOOD_OLLAMA_REPLY = Response(
    200,
    json={"message": {"role": "assistant", "content": "Good morning!"}},
)


def _mock_ollama_get(monkeypatch, *, raises=None):
    """Replace app.state.http_client.get with a mock.

    Targets only the shared lifespan client, leaving the ASGI test client
    (AsyncClient with ASGITransport) completely unaffected.
    """
    from main import app as fastapi_app

    if raises is not None:
        async def _raise(*args, **kwargs):
            raise raises
        monkeypatch.setattr(fastapi_app.state.http_client, "get", _raise)
    else:
        monkeypatch.setattr(
            fastapi_app.state.http_client, "get", AsyncMock(return_value=None)
        )


# ── /health ──────────────────────────────────────────────────────────────────


async def test_health_ollama_reachable(client, monkeypatch):
    _mock_ollama_get(monkeypatch)
    r = await client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["ollama_reachable"] is True
    assert "model" in data
    assert "tesseract_available" in data
    assert "tesseract_hun_lang" in data


async def test_health_ollama_unreachable_returns_503(client, monkeypatch):
    _mock_ollama_get(monkeypatch, raises=httpx.ConnectError("refused"))
    r = await client.get("/health")
    assert r.status_code == 503
    data = r.json()
    assert data["status"] == "degraded"
    assert data["ollama_reachable"] is False


async def test_health_tesseract_fields_always_present(client, monkeypatch):
    _mock_ollama_get(monkeypatch)
    r = await client.get("/health")
    data = r.json()
    assert isinstance(data["tesseract_available"], bool)
    assert isinstance(data["tesseract_hun_lang"], bool)


# ── /config ──────────────────────────────────────────────────────────────────


async def test_config_returns_default_mode(client):
    r = await client.get("/config")
    assert r.status_code == 200
    data = r.json()
    assert "default_mode" in data
    assert data["default_mode"] in ("text", "image")


# ── / (root / index) ─────────────────────────────────────────────────────────


async def test_root_returns_html(client):
    r = await client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert b"Hungarian Reading Assistant" in r.content


# ── /translate ───────────────────────────────────────────────────────────────


@respx.mock
async def test_translate_success(client):
    respx.post(OLLAMA_CHAT).mock(return_value=GOOD_OLLAMA_REPLY)
    r = await client.post("/translate", json={"text": "Jó reggelt!"})
    assert r.status_code == 200
    data = r.json()
    assert data["translation"] == "Good morning!"
    assert data["source_text"] == "Jó reggelt!"
    assert "model" in data


async def test_translate_empty_text_is_rejected(client):
    r = await client.post("/translate", json={"text": ""})
    assert r.status_code == 422


async def test_translate_missing_field_is_rejected(client):
    r = await client.post("/translate", json={})
    assert r.status_code == 422


async def test_translate_text_at_max_length_is_accepted(client, monkeypatch):
    from config import MAX_INPUT_CHARS
    from ocr import OCRError  # noqa: F401

    async def mock_translate(text):
        return "OK"

    monkeypatch.setattr("main.translate_hungarian", mock_translate)
    r = await client.post("/translate", json={"text": "a" * MAX_INPUT_CHARS})
    assert r.status_code == 200


async def test_translate_text_exceeding_max_length_is_rejected(client):
    from config import MAX_INPUT_CHARS
    r = await client.post("/translate", json={"text": "a" * (MAX_INPUT_CHARS + 1)})
    assert r.status_code == 422


@respx.mock
async def test_translate_ollama_connect_error_returns_503(client):
    import httpx
    respx.post(OLLAMA_CHAT).mock(side_effect=httpx.ConnectError("refused"))
    r = await client.post("/translate", json={"text": "Helló"})
    assert r.status_code == 503
    assert "error" in r.json()


@respx.mock
async def test_translate_ollama_timeout_returns_503(client):
    import httpx
    respx.post(OLLAMA_CHAT).mock(side_effect=httpx.TimeoutException("timed out"))
    r = await client.post("/translate", json={"text": "Helló"})
    assert r.status_code == 503
    error = r.json()["error"].lower()
    assert "timed out" in error or "reachable" in error


@respx.mock
async def test_translate_model_not_found_returns_503(client):
    respx.post(OLLAMA_CHAT).mock(return_value=Response(404, text="model not found"))
    r = await client.post("/translate", json={"text": "Helló"})
    assert r.status_code == 503
    assert "not found" in r.json()["error"].lower()


@respx.mock
async def test_translate_ollama_5xx_returns_503(client):
    respx.post(OLLAMA_CHAT).mock(return_value=Response(500, text="internal server error"))
    r = await client.post("/translate", json={"text": "Helló"})
    assert r.status_code == 503


@respx.mock
async def test_translate_unexpected_response_shape_returns_503(client):
    respx.post(OLLAMA_CHAT).mock(return_value=Response(200, json={"no_message_key": True}))
    r = await client.post("/translate", json={"text": "Helló"})
    assert r.status_code == 503
    assert "error" in r.json()


# ── /ocr ─────────────────────────────────────────────────────────────────────


async def test_ocr_success(client, png_image, monkeypatch):
    """Verify the /ocr endpoint serialises extract_text() results correctly.

    extract_text() is mocked so the test is not sensitive to whether
    Tesseract is installed or which Python version is in use.
    """
    async def mock_extract(_bytes):
        return ("Helló világ", 88.3)

    monkeypatch.setattr("main.extract_text", mock_extract)
    r = await client.post(
        "/ocr",
        files={"image": ("test.png", png_image, "image/png")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["extracted_text"] == "Helló világ"
    assert data["confidence"] == 88.3
    assert data["confidence_label"] in ("Good", "Fair", "Poor", "Low — review carefully")
    assert "warning" in data


@pytest.mark.integration
async def test_ocr_real_tesseract(client, png_image):
    """End-to-end OCR test using a real Tesseract process.

    Marked integration — requires Tesseract + hun language pack to be
    installed. Skipped automatically if Tesseract is not functional.
    Run explicitly with: pytest -m integration
    """
    try:
        import pytesseract
        from PIL import Image as _Image
        # Verify the full pipeline works, not just version detection.
        _img = _Image.new("RGB", (200, 50), "white")
        pytesseract.image_to_string(_img, lang="hun")
    except Exception as exc:
        pytest.skip(f"Tesseract pipeline not functional on this system: {exc}")

    r = await client.post(
        "/ocr",
        files={"image": ("test.png", png_image, "image/png")},
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data["extracted_text"], str)
    assert isinstance(data["confidence"], float)
    assert data["confidence_label"] in (
        "Good", "Fair", "Poor", "Low — review carefully", "Unknown"
    )


async def test_ocr_wrong_content_type_returns_422(client):
    r = await client.post(
        "/ocr",
        files={"image": ("note.txt", b"plain text", "text/plain")},
    )
    assert r.status_code == 422
    assert "error" in r.json()


async def test_ocr_missing_content_type_returns_422(client):
    # httpx sends multipart without a sub-part content-type when mimeType is None
    r = await client.post(
        "/ocr",
        files={"image": ("file", b"data", None)},
    )
    assert r.status_code == 422


async def test_ocr_file_too_large_returns_422(client):
    from config import MAX_IMAGE_BYTES
    oversized = b"0" * (MAX_IMAGE_BYTES + 1)
    r = await client.post(
        "/ocr",
        files={"image": ("big.jpg", oversized, "image/jpeg")},
    )
    assert r.status_code == 422
    assert "large" in r.json()["error"].lower()


async def test_ocr_tesseract_not_found_returns_503(client, png_image, monkeypatch):
    from ocr import OCRError

    async def raise_not_found(_bytes):
        raise OCRError("Tesseract is not installed or not on PATH.")

    monkeypatch.setattr("main.extract_text", raise_not_found)
    r = await client.post(
        "/ocr",
        files={"image": ("t.png", png_image, "image/png")},
    )
    assert r.status_code == 503
    assert "tesseract" in r.json()["error"].lower()


async def test_ocr_language_pack_missing_returns_503(client, png_image, monkeypatch):
    from ocr import OCRError

    async def raise_lang_error(_bytes):
        raise OCRError(
            "Hungarian language pack not found. Run: brew install tesseract-lang"
        )

    monkeypatch.setattr("main.extract_text", raise_lang_error)
    r = await client.post(
        "/ocr",
        files={"image": ("t.png", png_image, "image/png")},
    )
    assert r.status_code == 503
    error = r.json()["error"].lower()
    assert "language" in error or "hun" in error


async def test_ocr_confidence_label_reflects_score(client, png_image, monkeypatch):
    async def mock_extract(_bytes):
        return ("extracted text", 95.0)

    monkeypatch.setattr("main.extract_text", mock_extract)
    r = await client.post(
        "/ocr",
        files={"image": ("t.png", png_image, "image/png")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["confidence"] == 95.0
    assert data["confidence_label"] == "Good"
    assert data["warning"] is None


async def test_ocr_low_confidence_includes_warning(client, png_image, monkeypatch):
    async def mock_extract(_bytes):
        return ("blurry text", 55.0)

    monkeypatch.setattr("main.extract_text", mock_extract)
    r = await client.post(
        "/ocr",
        files={"image": ("t.png", png_image, "image/png")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["confidence_label"] == "Low — review carefully"
    assert data["warning"] is not None
    assert "review" in data["warning"].lower()
