import httpx

from config import OLLAMA_BASE_URL, OLLAMA_MODEL

_TIMEOUT = 60.0


class TranslationError(Exception):
    """Raised when the Ollama translation call fails."""


async def translate_hungarian(text: str) -> str:
    """Translate Hungarian text to English via Ollama.

    Args:
        text: Hungarian source text.

    Returns:
        English translation string.

    Raises:
        TranslationError: If Ollama is unreachable, returns a non-200 status,
            or the requested model is not found.
    """
    prompt = (
        "You are a professional Hungarian (hu) to English (en) translator.\n"
        f"Translate the following text:\n\n{text}"
    )

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
    except httpx.ConnectError as exc:
        raise TranslationError(
            f"Ollama is not reachable at {OLLAMA_BASE_URL}"
        ) from exc

    if response.status_code != 200:
        body = response.text
        if "model" in body.lower():
            raise TranslationError(
                f"Model '{OLLAMA_MODEL}' not found. Run: ollama pull {OLLAMA_MODEL}"
            )
        raise TranslationError(
            f"Ollama returned HTTP {response.status_code}: {body}"
        )

    data: dict = response.json()
    return data["message"]["content"]
