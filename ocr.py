import asyncio
import functools
import io
import re

import pytesseract
from PIL import Image, ImageEnhance

import config

if config.TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD


class OCRError(Exception):
    """Raised when OCR processing fails."""


def _preprocess(image: Image.Image) -> Image.Image:
    """Apply configured preprocessing to improve OCR accuracy.

    Optionally resizes large images and converts to grayscale with a
    contrast boost. Both steps are controlled by config flags.
    """
    if config.OCR_AUTO_RESIZE:
        longest_edge = max(image.width, image.height)
        if longest_edge > config.OCR_MAX_DIMENSION:
            image.thumbnail(
                (config.OCR_MAX_DIMENSION, config.OCR_MAX_DIMENSION),
                Image.Resampling.LANCZOS,
            )
    if config.OCR_AUTO_ENHANCE:
        image = image.convert("L")
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)
    return image


async def extract_text(image_bytes: bytes) -> tuple[str, float]:
    """Extract Hungarian text from image bytes using Tesseract.

    Args:
        image_bytes: Raw image data (JPEG, PNG, WebP, or HEIC).

    Returns:
        Tuple of (extracted_text, confidence_score).
        confidence_score is a float 0–100; -1.0 if unavailable.

    Raises:
        OCRError: If Tesseract is unavailable, the Hungarian language pack
            is missing, or image processing fails for any other reason.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image = _preprocess(image)

        loop = asyncio.get_running_loop()

        # Single Tesseract pass: image_to_data gives both per-word text and
        # confidence scores, so a separate image_to_string call is redundant.
        data: dict = await loop.run_in_executor(
            None,
            functools.partial(
                pytesseract.image_to_data,
                image,
                lang="hun",
                output_type=pytesseract.Output.DICT,
            ),
        )

        # Mean of per-word confidences; Tesseract uses -1 as a sentinel for
        # non-word rows (whitespace, separators) — exclude those.
        conf_values = [
            c for c in data["conf"]
            if isinstance(c, (int, float)) and c != -1
        ]
        confidence = (
            round(sum(conf_values) / len(conf_values), 1)
            if conf_values
            else -1.0
        )

        # Reconstruct text preserving line/block structure.
        line_words: dict = {}
        for i, word in enumerate(data["text"]):
            if not isinstance(data["conf"][i], (int, float)) or data["conf"][i] == -1:
                continue
            if not word.strip():
                continue
            key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            line_words.setdefault(key, []).append(word)

        prev_block: int | None = None
        text_parts: list[str] = []
        for (block, _par, _line), words in sorted(line_words.items()):
            if prev_block is not None and block != prev_block:
                text_parts.append("")
            text_parts.append(" ".join(words))
            prev_block = block

        text = "\n".join(text_parts).strip()
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text, confidence

    except (pytesseract.pytesseract.TesseractNotFoundError, FileNotFoundError) as exc:
        raise OCRError(
            "Tesseract is not installed or not on PATH. Run: brew install tesseract"
        ) from exc
    except Exception as exc:
        msg = str(exc)
        if "Failed loading language" in msg:
            raise OCRError(
                "Hungarian language pack not found. Run: brew install tesseract-lang"
                " and verify 'hun' appears in: tesseract --list-langs"
            ) from exc
        raise OCRError(f"OCR failed: {msg}") from exc


def tesseract_status() -> dict[str, bool]:
    """Check Tesseract availability and Hungarian language pack presence.

    Returns:
        Dict with keys 'available' and 'hun_lang', both bool.
        Never raises.
    """
    available = False
    hun_lang = False
    try:
        pytesseract.get_tesseract_version()
        available = True
    except Exception:
        pass
    try:
        hun_lang = "hun" in pytesseract.get_languages()
    except Exception:
        pass
    return {"available": available, "hun_lang": hun_lang}
