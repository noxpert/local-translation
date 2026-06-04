#!/usr/bin/env python3
"""Smoke test for the Hungarian Reading Assistant.

Run while the app is running:
    python test_smoke.py

curl equivalents
----------------
Health check (now shows Tesseract status):
    curl http://localhost:8000/health

Translation (short greeting):
    curl -s -X POST http://localhost:8000/translate \
        -H "Content-Type: application/json" \
        -d '{"text": "Jó reggelt kívánok!"}' | python3 -m json.tool

Translation (longer sentence):
    curl -s -X POST http://localhost:8000/translate \
        -H "Content-Type: application/json" \
        -d '{"text": "A macska az asztal alatt alszik."}' | python3 -m json.tool

OCR upload:
    curl -s -X POST http://localhost:8000/ocr \
        -F "image=@/path/to/book_page.jpg" | python3 -m json.tool

Common issues
-------------
Ollama not running:
    Start it with: ollama serve
    The /health endpoint will show {"ollama_reachable": false}.

Model not yet pulled:
    Run: ollama pull translategemma:12b
    The /translate endpoint will return a 503 with a message naming the missing model.

Port conflict on 8000:
    Change APP_PORT in .env and restart:
    uvicorn main:app --host 127.0.0.1 --port <new_port> --reload

CORS issues (opening index.html from the filesystem):
    Always access the app via http://localhost:8000, not by opening the HTML
    file directly (file:// URLs). FastAPI serves the page at GET /.
"""

import json
import os
import sys

import httpx

BASE_URL = "http://localhost:8000"

TRANSLATIONS = [
    "Jó reggelt kívánok!",
    "A macska az asztal alatt alszik.",
]


def separator(title: str) -> None:
    print(f"\n{'─' * 50}")
    print(f"  {title}")
    print('─' * 50)


def check_health(client: httpx.Client) -> None:
    separator("GET /health")
    response = client.get(f"{BASE_URL}/health")
    data = response.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))

    if not data.get("ollama_reachable"):
        print("\nWARNING: Ollama is not reachable. Translations will fail.")
        print("  Start Ollama with: ollama serve")


def check_translation(client: httpx.Client, text: str) -> None:
    separator(f'POST /translate — "{text}"')
    response = client.post(
        f"{BASE_URL}/translate",
        json={"text": text},
        timeout=90.0,
    )
    data = response.json()
    print(f"HTTP {response.status_code}")
    print(json.dumps(data, indent=2, ensure_ascii=False))


def check_ocr_health(client: httpx.Client) -> None:
    """Report whether Tesseract and the Hungarian language pack are available."""
    separator("GET /health — Tesseract status")
    response = client.get(f"{BASE_URL}/health")
    data = response.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))

    if not data.get("tesseract_available"):
        print("\nWARNING: Tesseract is not available. OCR (/ocr) will fail.")
        print("  Install it with: brew install tesseract")
    if not data.get("tesseract_hun_lang"):
        print("\nWARNING: Hungarian language pack ('hun') not found.")
        print("  Install it with: brew install tesseract-lang")
        print("  Verify 'hun' appears in: tesseract --list-langs")


def check_ocr_upload(client: httpx.Client, image_path: str) -> None:
    """Upload a local image to /ocr and print the extraction result."""
    separator(f"POST /ocr — {image_path}")

    if not os.path.isfile(image_path):
        print(f"ERROR: No such file: {image_path}")
        return

    filename = os.path.basename(image_path)
    with open(image_path, "rb") as fh:
        # OCR can be slow on first run; use a generous timeout.
        response = client.post(
            f"{BASE_URL}/ocr",
            files={"image": (filename, fh, "image/jpeg")},
            timeout=120.0,
        )

    data = response.json()
    print(f"HTTP {response.status_code}")

    if response.status_code == 200:
        print(f"confidence:       {data.get('confidence')}")
        print(f"confidence_label: {data.get('confidence_label')}")
        text = data.get("extracted_text", "")
        preview = text[:200]
        suffix = "…" if len(text) > 200 else ""
        print(f"extracted_text (first 200 chars):\n{preview}{suffix}")
        if data.get("warning"):
            print(f"\nwarning: {data['warning']}")
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))


def main() -> None:
    print(f"Smoke test against {BASE_URL}")

    try:
        with httpx.Client(timeout=10.0) as client:
            check_health(client)
            check_ocr_health(client)

        # Use a longer timeout for translation calls
        with httpx.Client() as client:
            for text in TRANSLATIONS:
                check_translation(client, text)

            # Optional OCR check when an image path is supplied.
            if len(sys.argv) > 1:
                check_ocr_upload(client, sys.argv[1])
            else:
                print("\nTip: pass an image path to test OCR, e.g.:")
                print("  python test_smoke.py /path/to/book_page.jpg")

    except httpx.ConnectError:
        print(
            f"\nERROR: Could not connect to {BASE_URL}.\n"
            "Is the app running? Start it with:\n"
            "  uvicorn main:app --host 127.0.0.1 --port 8000 --reload",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"\n{'─' * 50}")
    print("Smoke test complete.")


if __name__ == "__main__":
    main()
