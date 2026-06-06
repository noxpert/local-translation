.PHONY: help install run run-prod test test-ocr health check-tesseract lint format clean env-check \
        docker-build docker-run docker-stop docker-logs docker-health \
        test-unit test-e2e install-dev install-playwright

.DEFAULT_GOAL := help

APP_HOST := 127.0.0.1
APP_PORT := 8000
HEALTH_URL := http://localhost:$(APP_PORT)/health

help:
	@echo ""
	@echo "Hungarian Reading Assistant — available targets:"
	@echo ""
	@echo "  Native development:"
	@echo "  make install          Install Python dependencies (pip) and remind about Tesseract"
	@echo "  make run              Start the dev server with --reload (checks for .env first)"
	@echo "  make run-prod         Start the production server (2 workers, no --reload)"
	@echo "  make test             Run unit tests then E2E tests (no running app needed)"
	@echo "  make test-ocr         Run OCR smoke test: make test-ocr IMAGE=/path/to/file.jpg"
	@echo "  make health           Hit /health and pretty-print the JSON response"
	@echo "  make check-tesseract  Show Tesseract version and installed languages"
	@echo "  make lint             Lint with ruff (falls back to flake8)"
	@echo "  make format           Format with ruff format (falls back to black)"
	@echo "  make clean            Remove __pycache__, .pyc, and cache directories"
	@echo "  make env-check        Verify required .env variables are set"
	@echo ""
	@echo "  Testing:"
	@echo "  make install-dev      Install development/test dependencies"
	@echo "  make install-playwright  Install Playwright + Chromium browser"
	@echo "  make test-unit        Run API unit tests (no browser, no Ollama needed)"
	@echo "  make test-e2e         Run Playwright E2E tests (no Ollama needed)"
	@echo ""
	@echo "  Docker (Option A — app + Tesseract in container, Ollama native):"
	@echo "  make docker-build     Build the Docker image"
	@echo "  make docker-run       Start the container in the background"
	@echo "  make docker-stop      Stop and remove the container"
	@echo "  make docker-logs      Tail app container logs"
	@echo "  make docker-health    Hit /health on the running container"
	@echo ""

install:
	@echo ">>> Installing Python dependencies..."
	pip install -r requirements.txt
	@echo ""
	@echo "NOTE: Tesseract OCR must also be installed separately via Homebrew:"
	@echo "  brew install tesseract && brew install tesseract-lang"
	@echo ""

run:
	@echo ">>> Starting development server..."
	@if [ ! -f .env ]; then \
		echo "ERROR: .env file not found."; \
		echo "Please run: cp .env.example .env"; \
		echo "Then edit .env with your settings before starting the server."; \
		exit 1; \
	fi
	uvicorn main:app --host $(APP_HOST) --port $(APP_PORT) --reload

run-prod:
	@echo ">>> Starting production server (2 workers)..."
	@if [ ! -f .env ]; then \
		echo "ERROR: .env file not found."; \
		echo "Please run: cp .env.example .env"; \
		echo "Then edit .env with your settings before starting the server."; \
		exit 1; \
	fi
	uvicorn main:app --host $(APP_HOST) --port $(APP_PORT) --workers 2

_check-app-running:
	@STATUS=$$(curl -s -o /dev/null -w "%{http_code}" $(HEALTH_URL) 2>/dev/null || echo "000"); \
	if [ "$$STATUS" != "200" ] && [ "$$STATUS" != "503" ]; then \
		echo "ERROR: App is not reachable at $(HEALTH_URL)"; \
		echo "Please run 'make run' in another terminal first."; \
		exit 1; \
	fi

test: test-unit test-e2e

test-ocr: _check-app-running
	@echo ">>> Running OCR smoke test..."
	@if [ -z "$(IMAGE)" ]; then \
		echo "ERROR: IMAGE variable is required."; \
		echo "Usage: make test-ocr IMAGE=/path/to/file.jpg"; \
		exit 1; \
	fi
	python test_smoke.py $(IMAGE)

health:
	@echo ">>> Checking app health..."
	curl -s $(HEALTH_URL) | python3 -m json.tool

check-tesseract:
	@echo ">>> Checking Tesseract installation..."
	@if ! command -v tesseract > /dev/null 2>&1; then \
		echo "ERROR: tesseract not found in PATH."; \
		echo "Install it with: brew install tesseract && brew install tesseract-lang"; \
		exit 1; \
	fi
	tesseract --version
	@echo ""
	@echo "--- Installed languages ---"
	@tesseract --list-langs
	@echo ""
	@if tesseract --list-langs 2>&1 | grep -q '^hun$$'; then \
		echo "✓ Hungarian (hun) is installed."; \
	else \
		echo "WARN: Hungarian (hun) not found in language list."; \
		echo "Install it with: brew install tesseract-lang"; \
	fi

lint:
	@echo ">>> Linting..."
	@if command -v ruff > /dev/null 2>&1; then \
		ruff check .; \
	elif command -v flake8 > /dev/null 2>&1; then \
		flake8 .; \
	else \
		echo "No linter found. Install ruff with: pip install ruff"; \
	fi

format:
	@echo ">>> Formatting..."
	@if command -v ruff > /dev/null 2>&1; then \
		ruff format .; \
	elif command -v black > /dev/null 2>&1; then \
		black .; \
	else \
		echo "No formatter found. Install ruff with: pip install ruff"; \
	fi

clean:
	@echo ">>> Cleaning up cache files..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -type f -name '*.pyc' -delete 2>/dev/null; true
	find . -type f -name '*.pyo' -delete 2>/dev/null; true
	rm -rf .pytest_cache .ruff_cache
	@echo "Done."

install-dev:
	@echo ">>> Installing development dependencies..."
	pip install -r requirements-dev.txt

install-playwright:
	@echo ">>> Installing Playwright + Chromium..."
	playwright install chromium --with-deps

test-unit:
	@echo ">>> Running API unit tests..."
	pytest tests/test_api.py -v

test-e2e:
	@echo ">>> Running Playwright E2E tests..."
	pytest tests/e2e/ -v


docker-build:
	@echo ">>> Building Docker image..."
	docker compose build

docker-run:
	@echo ">>> Starting container (detached)..."
	@if [ ! -f .env ]; then \
		echo "ERROR: .env file not found."; \
		echo "Please run: cp .env.example .env"; \
		exit 1; \
	fi
	docker compose up -d
	@echo "App will be available at http://localhost:$(APP_PORT)"

docker-stop:
	@echo ">>> Stopping container..."
	docker compose down

docker-logs:
	@echo ">>> Tailing app logs (Ctrl+C to exit)..."
	docker compose logs -f app

docker-health:
	@echo ">>> Checking containerised app health..."
	curl -s $(HEALTH_URL) | python3 -m json.tool

env-check:
	@echo ">>> Checking .env variables..."
	@if [ ! -f .env ]; then \
		echo "ERROR: .env not found. Run: cp .env.example .env"; \
		exit 1; \
	fi
	@echo ""
	@_check_var() { \
		val=$$(grep -E "^$$1=" .env 2>/dev/null | cut -d= -f2- | tr -d '"'"'"' '); \
		if [ -n "$$val" ]; then \
			echo "  PASS  $$1"; \
		else \
			echo "  WARN  $$1 is not set"; \
		fi; \
	}; \
	_check_var OLLAMA_BASE_URL; \
	_check_var OLLAMA_MODEL; \
	echo ""; \
	echo "  --- Phase 2 (OCR) ---"; \
	tess_val=$$(grep -E "^TESSERACT_CMD=" .env 2>/dev/null | cut -d= -f2- | tr -d '"'"'"' '); \
	if [ -n "$$tess_val" ]; then \
		echo "  PASS  TESSERACT_CMD = $$tess_val"; \
	else \
		echo "  WARN  TESSERACT_CMD is not set"; \
		echo "        On Apple Silicon, set it to: /opt/homebrew/bin/tesseract"; \
	fi
	@echo ""
