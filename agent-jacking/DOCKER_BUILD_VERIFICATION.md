# Docker Build & Deployment Verification Guide

This document provides instructions for building, testing, and deploying the Agentic Workflow Graph Controller with VLMGuard-R1 Intent Analyzer using Docker.

## 📋 Prerequisites

- Docker Engine 20.10+ 
- Docker Compose 2.0+
- At least 4GB of RAM available for the container

## 🚀 Quick Start

### 1. Build the Docker Image

```bash
docker build -t agentic-security-controller:latest .
```

### 2. Run with Docker Compose

```bash
docker-compose up -d
```

### 3. Verify the Service is Running

```bash
curl -s http://localhost:8000/api/v1/health | jq
```

Expected response:
```json
{
  "status": "healthy",
  "service": "Agentic Workflow Graph Controller API",
  "components": {
    "intent_analyzer": true,
    "workflow_controller": true
  }
}
```

## 🧪 Testing the API

### Intent Analysis Endpoint

```bash
curl -X POST http://localhost:8000/api/v1/analyze-intent \
  -H "Content-Type: application/json" \
  -d '{"intent_text": "I need to install the lodash package to fix the undefined function error."}'
```

### Tool Call Validation Endpoint

```bash
curl -X POST http://localhost:8000/api/v1/validate-tool-call \
  -H "Content-Type: application/json" \
  -d '{
    "agent_intent": "I need to install the lodash package to fix the undefined function error.",
    "tool_name": "install_package",
    "tool_parameters": {
      "package_manager": "npm",
      "package_name": "lodash",
      "version": "4.17.21"
    }
  }'
```

## 🛠️ Dockerfile Enhancements

The Dockerfile has been enhanced with the following improvements:

1. **Pre-downloaded Sentence Transformer model**: The `all-MiniLM-L6-v2` model is now downloaded during the build process, eliminating the need to download it on first run.
2. **Health check endpoint**: Added a `HEALTHCHECK` instruction to monitor the service health.
3. **Added `curl` dependency**: Required for the health check to function properly.

### Dockerfile Structure

```dockerfile
# Use Python 3.9 slim image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create models directory and pre-download Sentence Transformer model
RUN mkdir -p /app/models && \
    python -c "from sentence_transformers import SentenceTransformer; model = SentenceTransformer('all-MiniLM-L6-v2', cache_folder='/app/models'); print('Model downloaded successfully')"

# Copy application code
COPY . .

# Expose port for API service
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Command to run the service
CMD ["uvicorn", "api_service:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 🔧 Docker Compose Configuration

The `docker-compose.yml` file configures the service with the following settings:

```yaml
version: '3.8'

services:
  agentic-security-controller:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MODEL_NAME=all-MiniLM-L6-v2
      - PORT=8000
    volumes:
      - ./models:/app/models
    restart: unless-stopped
```

### Volume Mount for Models

The `./models:/app/models` volume mount ensures that:
- The pre-downloaded Sentence Transformer model is persisted across container restarts
- Subsequent builds or container runs can use the cached model

## 🐛 Troubleshooting

### Issue: Container fails to start

**Solution**: Check the logs with `docker-compose logs -f`. Ensure that port 8000 is not already in use on your host machine.

### Issue: Health check fails

**Solution**: The health check has a 60-second start period to allow for service initialization. If it continues to fail after 60 seconds, check the service logs.

### Issue: Model download fails during build

**Solution**: Ensure you have a stable internet connection. The model is approximately 90MB and may take a few moments to download.

## 📊 Performance Considerations

- **Memory Usage**: The `all-MiniLM-L6-v2` model requires approximately 500MB of RAM. Ensure your Docker host has sufficient memory.
- **Startup Time**: The first startup after a fresh build may take 30-60 seconds to initialize the model and service.
- **API Latency**: Intent analysis requests typically complete within 100-300ms depending on the complexity of the intent text.

## 🔐 Security Considerations

- The API service runs without authentication by default. In production environments, consider adding rate limiting and authentication.
- The container runs as the `root` user by default. For production, consider creating a non-root user in the Dockerfile.
- The `./models` volume mount should be secured to prevent unauthorized access to the model files.