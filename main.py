"""Hungarian Reading Assistant — FastAPI application.

Serves a single-page frontend and exposes a /translate endpoint that proxies
Hungarian-to-English translation requests to a local Ollama instance.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from config import MAX_INPUT_CHARS, OLLAMA_BASE_URL, OLLAMA_MODEL
from translator import TranslationError, translate_hungarian


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield


app = FastAPI(title="Hungarian Reading Assistant", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


class TranslationRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_INPUT_CHARS)


class TranslationResponse(BaseModel):
    translation: str
    model: str
    source_text: str


class ErrorResponse(BaseModel):
    error: str
    detail: str = ""


@app.get("/")
async def serve_index() -> FileResponse:
    return FileResponse("static/index.html")


@app.post("/translate")
async def translate(request: TranslationRequest) -> JSONResponse:
    try:
        translation = await translate_hungarian(request.text)
        return JSONResponse(
            content=TranslationResponse(
                translation=translation,
                model=OLLAMA_MODEL,
                source_text=request.text,
            ).model_dump()
        )
    except TranslationError as exc:
        return JSONResponse(
            status_code=503,
            content=ErrorResponse(error=str(exc)).model_dump(),
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="Internal server error", detail=str(exc)
            ).model_dump(),
        )


@app.get("/health")
async def health() -> JSONResponse:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.get(f"{OLLAMA_BASE_URL}/api/tags")
        return JSONResponse(
            content={"status": "ok", "ollama_reachable": True, "model": OLLAMA_MODEL}
        )
    except Exception:
        return JSONResponse(
            content={
                "status": "degraded",
                "ollama_reachable": False,
                "model": OLLAMA_MODEL,
            }
        )
