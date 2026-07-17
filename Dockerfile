FROM python:3.14-slim

WORKDIR /app

# System dependencies for psycopg2 and pymupdf
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY . .

# Create data directories
RUN mkdir -p /app/data/memory

# Pre-download NLTK punkt tokenizer for semantic chunking
RUN python -c "import nltk; nltk.download('punkt_tab', quiet=True)"

EXPOSE 8000

# Initialize DB and start server
CMD ["sh", "-c", "python scripts/init_db.py && python -m uvicorn techcorp_platform.app:app --host 0.0.0.0 --port 8000"]