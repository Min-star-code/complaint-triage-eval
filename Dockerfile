FROM python:3.12-slim

# Tesseract with English + French for the scanned letters
RUN apt-get update \
 && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng tesseract-ocr-fra \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Tests first (fake LLM, no key needed), then the full evaluation with the real model.
# The API key comes from --env-file at run time; it is never baked into the image.
ENTRYPOINT ["sh", "-c", "python -m pytest -q -p no:warnings && python scripts/run_eval.py \"$@\"", "--"]
CMD ["--tag", "docker", "--prompt", "v1", "--runs", "1"]
