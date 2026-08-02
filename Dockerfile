FROM python:3.11-slim as base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8501 \
    # Reduce pip's internal cache size
    PIP_NO_CACHE_DIR=1 \
    # Tell Streamlit we're in production
    STREAMLIT_SERVER_RUN_ON_SAVE=false \
    # Faster Python imports
    PYTHONHASHSEED=42

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Stage 1: Core requirements (lightweight install)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Optional heavy packages (separate layer for faster rebuilds)
COPY requirements-optional.txt .
RUN pip install --no-cache-dir -r requirements-optional.txt || echo "Optional packages skipped"

COPY . .

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
