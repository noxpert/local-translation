import os

from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "translategemma:12b")
APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
APP_HOST: str = os.getenv("APP_HOST", "127.0.0.1")
MAX_INPUT_CHARS: int = int(os.getenv("MAX_INPUT_CHARS", "5000"))
