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

## Phase Roadmap

- **Phase 1** (current): Typed text → English translation
- **Phase 2**: Image/OCR input
- **Phase 3**: Speech input
