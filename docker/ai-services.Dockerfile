FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY ai-services/requirements.txt ./ai-services/requirements.txt
RUN pip install --no-cache-dir -r ai-services/requirements.txt

# Copy source
COPY ai-services/ ./ai-services/

EXPOSE 8001

# Healthcheck
HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "ai-services.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]
