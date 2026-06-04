# Hungarian Reading Assistant

A locally-run web app that lets you type or paste Hungarian text and receive an English translation powered by a local [Ollama](https://ollama.com) instance running `translategemma:12b`. No data leaves your machine.

## Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com) installed and running
- `translategemma:12b` model pulled

## Installation

```bash
# Clone the repository
git clone https://github.com/noxpert/local-translation.git
cd local-translation

# Pull the translation model (one-time, ~8 GB)
ollama pull translategemma:12b

# Install Python dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
```

## Running

```bash
# Ensure Ollama is running
ollama serve

# Start the app
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Then open http://localhost:8000 in a browser.

## Configuration

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `translategemma:12b` | Model to use for translation |
| `APP_PORT` | `8000` | Port the app listens on |
| `APP_HOST` | `127.0.0.1` | Host the app binds to |
| `MAX_INPUT_CHARS` | `5000` | Maximum input text length |

## Switching Models

To use the higher-quality (but slower/larger) model, set in `.env`:

```
OLLAMA_MODEL=translategemma:27b
```

Then pull it: `ollama pull translategemma:27b`

## Phase 2 — Image OCR Setup

Phase 2 adds the ability to photograph a Hungarian book page and extract the text using [Tesseract](https://github.com/tesseract-ocr/tesseract) OCR before translating it. Phase 1 (typed text translation) continues to work independently — if Tesseract is not installed, only the `/ocr` endpoint is affected.

### macOS Installation (primary)

```bash
# Install Tesseract OCR engine
brew install tesseract

# Install all language packs including Hungarian
brew install tesseract-lang

# Verify Hungarian is available
tesseract --list-langs
# Look for 'hun' in the output

# Install new Python dependencies
pip install -r requirements.txt
```

### Other platforms (brief)

- **Linux**: `sudo apt install tesseract-ocr tesseract-ocr-hun`
- **Windows**: Download the installer from <https://github.com/UB-Mannheim/tesseract/wiki>, then download `hun.traineddata` from the [tessdata repo](https://github.com/tesseract-ocr/tessdata) and place it in the Tesseract `tessdata/` directory. Set `TESSERACT_CMD` in `.env` to the full path of `tesseract.exe`.

### Configuration

| Variable | Default | Description |
|---|---|---|
| `TESSERACT_CMD` | (blank) | Full path to the `tesseract` binary. Leave blank if it is on your `PATH`. |
| `MAX_IMAGE_BYTES` | `15000000` | Upload size cap in bytes (~15 MB). |
| `OCR_AUTO_RESIZE` | `true` | Shrink images whose longest edge exceeds `OCR_MAX_DIMENSION` before OCR. |
| `OCR_MAX_DIMENSION` | `3000` | Long-edge pixel cap used when `OCR_AUTO_RESIZE` is on. |
| `OCR_AUTO_ENHANCE` | `true` | Convert to grayscale + boost contrast for cleaner OCR. |
| `OCR_CONF_HIGH` | `95` | Confidence ≥ this → "Good" (green). |
| `OCR_CONF_MEDIUM` | `90` | Confidence ≥ this → "Fair" (yellow). |
| `OCR_CONF_LOW` | `85` | Confidence ≥ this → "Poor" (orange); below → "Low — review carefully" (red). |

### Verifying Phase 2 is working

```bash
curl http://localhost:8000/health
# Should show "tesseract_available": true, "tesseract_hun_lang": true
```

If Tesseract is not installed, Phase 1 (typed text translation) continues to work normally — only the `/ocr` endpoint will return an error.

## Phase Roadmap

- **Phase 1**: Typed text → English translation
- **Phase 2** (current): Image/OCR input
- **Phase 3**: Speech input
