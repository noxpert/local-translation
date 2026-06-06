FROM python:3.12-slim

# Install Tesseract and the Hungarian language pack in a single layer
# so the package cache is never committed to the image.
RUN apt-get update -q && \
    apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-hun \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies before copying source so this layer is
# cached independently and only rebuilds when requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# APP_HOST must be 0.0.0.0 inside a container; set as default here so the
# image works correctly without any .env override.
ENV APP_HOST=0.0.0.0

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
