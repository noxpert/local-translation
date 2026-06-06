"""Shared fixtures for the API test suite."""

# ruff: noqa: E402 — env must be configured before the app is imported.
import io
import os

import httpx as _httpx
import pytest
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from PIL import Image, ImageDraw, ImageFont

# Load .env first so its values (e.g. TESSERACT_CMD) are in os.environ before
# the setdefault calls below. load_dotenv does not override variables that are
# already set in the environment, so an exported shell variable still wins.
load_dotenv()

# Fill in anything not provided by .env or the shell environment.
# TESSERACT_CMD is intentionally omitted: if it is not in .env it is left
# unset, and pytesseract will fall back to locating tesseract on PATH.
os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
os.environ.setdefault("OLLAMA_MODEL", "test-model")
os.environ["APP_DEFAULT_MODE"] = "text"

from main import app


@pytest.fixture
async def client():
    """ASGI test client — no running server required.

    httpx's ASGITransport does not trigger the ASGI lifespan, so we
    initialise app.state.http_client here to match what the lifespan
    sets up. Individual tests can monkeypatch .get() on this client
    to control /health behaviour without affecting the test transport.
    """
    async with _httpx.AsyncClient(timeout=5.0) as _ollama_client:
        app.state.http_client = _ollama_client
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac


@pytest.fixture
def png_image() -> bytes:
    """Minimal PNG with legible text generated via Pillow.

    Uses load_default(size=28) (Pillow ≥ 10.1) for a font large enough
    that Tesseract can process the image reliably.
    """
    img = Image.new("RGB", (500, 100), color="white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default(size=28)
    except TypeError:
        font = ImageFont.load_default()
    draw.text((20, 20), "Hello World Test", fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
