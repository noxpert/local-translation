import os

from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "translategemma:12b")
APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
APP_HOST: str = os.getenv("APP_HOST", "127.0.0.1")
MAX_INPUT_CHARS: int = int(os.getenv("MAX_INPUT_CHARS", "5000"))

# Phase 2: OCR
TESSERACT_CMD: str = os.getenv("TESSERACT_CMD", "")
MAX_IMAGE_BYTES: int = int(os.getenv("MAX_IMAGE_BYTES", "15000000"))
OCR_AUTO_RESIZE: bool = os.getenv("OCR_AUTO_RESIZE", "true").lower() == "true"
OCR_MAX_DIMENSION: int = int(os.getenv("OCR_MAX_DIMENSION", "3000"))
OCR_AUTO_ENHANCE: bool = os.getenv("OCR_AUTO_ENHANCE", "true").lower() == "true"
OCR_CONF_HIGH: int = int(os.getenv("OCR_CONF_HIGH", "95"))
OCR_CONF_MEDIUM: int = int(os.getenv("OCR_CONF_MEDIUM", "90"))
OCR_CONF_LOW: int = int(os.getenv("OCR_CONF_LOW", "85"))
