"""Hungarian Reading Assistant — FastAPI application.

Serves a single-page frontend and exposes a /translate endpoint that proxies
Hungarian-to-English translation requests to a local Ollama instance.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from config import (
    MAX_IMAGE_BYTES,
    MAX_INPUT_CHARS,
    OCR_CONF_HIGH,
    OCR_CONF_LOW,
    OCR_CONF_MEDIUM,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
)
from ocr import OCRError, extract_text, tesseract_status
from translator import TranslationError, translate_hungarian


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with httpx.AsyncClient(timeout=5.0) as client:
        app.state.http_client = client
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


class OCRResponse(BaseModel):
    extracted_text: str
    confidence: float
    confidence_label: str
    warning: str | None = None


def _confidence_label(score: float) -> str:
    """Map a numeric OCR confidence score to a display label."""
    if score < 0:
        return "Unknown"
    if score >= OCR_CONF_HIGH:
        return "Good"
    if score >= OCR_CONF_MEDIUM:
        return "Fair"
    if score >= OCR_CONF_LOW:
        return "Poor"
    return "Low — review carefully"


@app.get("/")
async def serve_index() -> FileResponse:
    return FileResponse("static/index.html")


@app.post("/translate", response_model=TranslationResponse)
async def translate(request: TranslationRequest):
    try:
        translation = await translate_hungarian(request.text)
        return TranslationResponse(
            translation=translation,
            model=OLLAMA_MODEL,
            source_text=request.text,
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


_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic"}


@app.post("/ocr", response_model=OCRResponse)
async def ocr_image(image: UploadFile = File(...)):
    if not image.content_type or image.content_type not in _ALLOWED_IMAGE_TYPES:
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error="Unsupported or missing file type. Use JPEG, PNG, WEBP, or HEIC."
            ).model_dump(),
        )

    data = await image.read()

    if len(data) > MAX_IMAGE_BYTES:
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error=f"Image too large. Maximum size is {MAX_IMAGE_BYTES // 1_000_000} MB."
            ).model_dump(),
        )

    try:
        text, confidence = await extract_text(data)
        label = _confidence_label(confidence)
        warning = (
            "OCR confidence is low. Review the text carefully before translating."
            if label == "Low — review carefully"
            else None
        )
        return OCRResponse(
            extracted_text=text,
            confidence=confidence,
            confidence_label=label,
            warning=warning,
        )
    except OCRError as exc:
        return JSONResponse(
            status_code=503,
            content=ErrorResponse(error=str(exc)).model_dump(),
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(error="OCR failed", detail=str(exc)).model_dump(),
        )


@app.get("/health")
async def health(request: Request) -> JSONResponse:
    tess = tesseract_status()
    try:
        await request.app.state.http_client.get(f"{OLLAMA_BASE_URL}/api/tags")
        return JSONResponse(
            content={
                "status": "ok",
                "ollama_reachable": True,
                "model": OLLAMA_MODEL,
                "tesseract_available": tess["available"],
                "tesseract_hun_lang": tess["hun_lang"],
            }
        )
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "ollama_reachable": False,
                "model": OLLAMA_MODEL,
                "tesseract_available": tess["available"],
                "tesseract_hun_lang": tess["hun_lang"],
            },
        )
