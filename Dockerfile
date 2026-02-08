# Build stage
FROM python:3.11-slim AS builder

WORKDIR /app
COPY requirements.txt .

RUN apt-get update && apt-get install -y --no-install-recommends gcc \
    && pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/* \
    && rm -rf /wheels

COPY . .

RUN mkdir -p data/db data/lake data/output data/logs

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]