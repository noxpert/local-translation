#!/usr/bin/env python3
"""Smoke test for the Hungarian Reading Assistant.

Run while the app is running:
    python test_smoke.py

curl equivalents
----------------
Health check:
    curl http://localhost:8000/health

Translation (short greeting):
    curl -s -X POST http://localhost:8000/translate \
        -H "Content-Type: application/json" \
        -d '{"text": "Jó reggelt kívánok!"}' | python3 -m json.tool

Translation (longer sentence):
    curl -s -X POST http://localhost:8000/translate \
        -H "Content-Type: application/json" \
        -d '{"text": "A macska az asztal alatt alszik."}' | python3 -m json.tool

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
    separator(f"POST /translate — "{text}"")
    response = client.post(
        f"{BASE_URL}/translate",
        json={"text": text},
        timeout=90.0,
    )
    data = response.json()
    print(f"HTTP {response.status_code}")
    print(json.dumps(data, indent=2, ensure_ascii=False))


def main() -> None:
    print(f"Smoke test against {BASE_URL}")

    try:
        with httpx.Client(timeout=10.0) as client:
            check_health(client)

        # Use a longer timeout for translation calls
        with httpx.Client() as client:
            for text in TRANSLATIONS:
                check_translation(client, text)

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
