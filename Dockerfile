# Conflict & Security Intelligence — data pipeline (Bronze/Silver/Gold)
# Build:  docker build -t csi-pipeline .
# Run:    docker run --rm --env-file .env -v "$PWD/data:/app/data" -v "$PWD/reports:/app/reports" csi-pipeline
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Seoul

WORKDIR /app

# Dependencies first (cache-friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pipeline code + reference data (terror.db + bronze live in a mounted volume)
COPY scripts/ ./scripts/
COPY data/*.json ./data/

# Default: run the medallion pipeline once (bronze -> silver -> gold)
ENTRYPOINT ["python", "scripts/pipeline/run.py"]
