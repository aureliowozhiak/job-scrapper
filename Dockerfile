# Multi-stage Dockerfile for job-scrapper

# Stage 1: Base image with dependencies
FROM python:3.12-slim as base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Development image
FROM base as development

# Copy all source code
COPY . .

# Create necessary directories
RUN mkdir -p lake output logs

ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=development

CMD ["python", "api.py"]

# Stage 3: Production image
FROM base as production

# Copy only necessary files
COPY methods/ methods/
COPY utils/ utils/
COPY jobfinder_bot/ jobfinder_bot/
COPY api.py .
COPY app.py .
COPY load.py .
COPY endpoints.py .

# Create necessary directories with proper permissions
RUN mkdir -p lake output logs && \
    chmod -R 755 lake output logs

# Create non-root user
RUN useradd -m -u 1000 scrapper && \
    chown -R scrapper:scrapper /app

USER scrapper

ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/', timeout=5)"

EXPOSE 5000

CMD ["python", "api.py"]
