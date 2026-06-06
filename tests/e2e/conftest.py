"""Playwright E2E fixtures — starts a live uvicorn server for the session."""

import os
import socket
import threading
import time

import httpx
import pytest
import uvicorn
from dotenv import load_dotenv

# Load .env first so TESSERACT_CMD (and similar path settings) reach config.py.
# Then apply test-specific overrides:
#   - setdefault for values that are fine if they come from .env (Ollama coords).
#   - explicit assignment for APP_DEFAULT_MODE so tests always start in text
#     mode regardless of what the developer has in their .env file.
load_dotenv()
os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
os.environ.setdefault("OLLAMA_MODEL", "test-model")
os.environ["APP_DEFAULT_MODE"] = "text"


def _free_port() -> int:
    """Return an available TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def live_server():
    """Start the FastAPI app in a background thread for the test session.

    A free port is chosen dynamically so concurrent or back-to-back sessions
    never collide on a fixed port number.
    """
    from main import app

    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Poll until the server is ready (up to 10 s).
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            httpx.get(f"http://127.0.0.1:{port}/health", timeout=1)
            break
        except Exception:
            time.sleep(0.25)
    else:
        raise RuntimeError("E2E live server did not start in time.")

    yield f"http://127.0.0.1:{port}"

    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture
def app_page(page, live_server):
    """Navigate to the app and yield the Playwright page."""
    page.goto(live_server)
    page.wait_for_load_state("networkidle")
    return page
