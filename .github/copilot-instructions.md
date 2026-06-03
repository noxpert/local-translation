# Copilot Instructions

## Project

Hungarian Reading Assistant — a local-only web app that translates typed Hungarian text to English using a locally running Ollama instance. No external APIs; all inference runs on the user's machine.

## Stack

- **Backend**: Python 3.11+, FastAPI, uvicorn
- **LLM runtime**: Ollama (`translategemma:12b` by default, `translategemma:27b` as fallback)
- **HTTP client**: `httpx` (async) for FastAPI → Ollama calls
- **Config**: `python-dotenv` + `.env` file; settings exposed as typed module-level constants in `config.py`
- **Frontend**: Plain HTML5 + CSS + vanilla JS; no framework, no build step

## Key files

| File | Purpose |
|---|---|
| `config.py` | Loads `.env`; source of truth for all settings |
| `translator.py` | `translate_hungarian(text)` async function; `TranslationError` exception |
| `main.py` | FastAPI app; routes `/`, `/translate`, `/health`; Pydantic v2 request/response models |
| `static/index.html` | Single-page UI |
| `static/app.js` | `fetch`-based JS; `submitTranslation()`, `clearOutput()` |
| `static/style.css` | All styles; no external fonts or CDN |
| `test_smoke.py` | Plain runnable smoke test (not pytest) |

## Conventions

- All FastAPI route handlers are `async def`.
- Pydantic v2 — use `.model_dump()`, not `.dict()`.
- Import settings from `config.py`, never hardcode values.
- `translator.py` raises `TranslationError` for all Ollama failures; `main.py` catches it and returns HTTP 503.
- The `/health` endpoint always returns HTTP 200 — it signals degraded state via the `ollama_reachable` boolean in the body.
- Frontend JS uses `fetch()` with `async/await`; no jQuery or other libraries.
- `Ctrl+Enter` in the textarea submits the form (handled in `app.js`).

## TranslateGemma prompt format

The model requires a **single user message** — no separate system role:

```
You are a professional Hungarian (hu) to English (en) translator.
Translate the following text:

{text}
```

Do not add a system-role message; the model ignores or mishandles it.

## Out of scope (Phase 1)

Image/OCR input, speech input, streaming responses, user history, authentication, Docker.
