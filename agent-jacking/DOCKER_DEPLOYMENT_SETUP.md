# Agentic Workflow Graph Controller - Docker Deployment Setup

## Overview

This directory contains Docker configuration and deployment scripts for the **Agentic Workflow Graph Controller** and **VLMGuard-R1 Intent Analyzer** to be deployed as a microservice or API gateway for agentic workflows.

---

## 🐳 Docker Setup

### `Dockerfile`

```dockerfile
# Use Python 3.9 slim image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port for API service
EXPOSE 8000

# Command to run the service
CMD ["uvicorn", "api_service:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### `requirements.txt`

```
# Core ML/Embedding libraries
scikit-learn>=1.3.0
sentence-transformers>=2.2.2
torch>=2.0.0
transformers>=4.30.0
huggingface-hub>=0.16.4

# Web framework for API service
fastapi>=0.103.0
uvicorn[standard]>=0.23.0
pydantic>=2.3.0

# Security and validation
pyyaml>=6.0
```

---

## 🚀 API Service (`api_service.py`)

```python
"""
Agentic Workflow Graph Controller API Service

FastAPI service exposing the Agentic Workflow Graph Controller and VLMGuard-R1 Intent Analyzer
as REST endpoints for agentic framework integration.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
from vlmguard_r1_sentence_transformer_analyzer import AdvancedVLMGuardR1IntentAnalyzer
from agentic_workflow_graph_controller import AgenticWorkflowGraphExecutionController

app = FastAPI(title="Agentic Workflow Graph Controller API", version="1.0.0")

# Initialize components
intent_analyzer = AdvancedVLMGuardR1IntentAnalyzer(model_name="all-MiniLM-L6-v2")
workflow_controller = AgenticWorkflowGraphExecutionController()

class IntentAnalysisRequest(BaseModel):
    intent_text: str

class IntentAnalysisResponse(BaseModel):
    original_intent: str
    action: str
    risk_score: float
    reasoning_chain: str
    rewritten_intent: str
    rewrite_actions: List[str]

class ToolCallRequest(BaseModel):
    agent_intent: str
    tool_name: str
    tool_parameters: Dict[str, Any]

class ToolCallResponse(BaseModel):
    status: str
    message: str
    intent_result: Dict[str, Any]
    execution_result: Dict[str, Any]

@app.post("/api/v1/analyze-intent", response_model=IntentAnalysisResponse)
def analyze_intent(request: IntentAnalysisRequest):
    """Analyze agent intent for malicious patterns using VLMGuard-R1."""
    try:
        result = intent_analyzer.process_intent(request.intent_text)
        return IntentAnalysisResponse(
            original_intent=result['original_intent'],
            action=result['action'],
            risk_score=result['analysis']['risk_score'],
            reasoning_chain=result['reasoning_chain'],
            rewritten_intent=result['rewritten_intent'],
            rewrite_actions=result['rewrite_actions']
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/validate-tool-call", response_model=ToolCallResponse)
def validate_tool_call(request: ToolCallRequest):
    """Validate and potentially execute a tool call through the Agentic Workflow Graph Controller."""
    try:
        result = workflow_controller.process_agent_intent(
            agent_intent=request.agent_intent,
            tool_name=request.tool_name,
            tool_parameters=request.tool_parameters
        )
        
        return ToolCallResponse(
            status=result.get('status', 'UNKNOWN'),
            message=result.get('message', 'Tool call processed'),
            intent_result=result.get('intent_result', {}),
            execution_result=result.get('execution_result', {})
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Agentic Workflow Graph Controller API"}
```

---

## 🐙 Docker Compose Setup (`docker-compose.yml`)

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

---

## 📝 Deployment Instructions

### 1. Build and Run Locally

```bash
# Build the Docker image
docker build -t agentic-security-controller .

# Run the container
docker run -p 8000:8000 agentic-security-controller
```

### 2. Run with Docker Compose

```bash
# Start the service
docker-compose up -d

# Check logs
docker-compose logs -f agentic-security-controller
```

### 3. Test the API

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Intent analysis
curl -X POST http://localhost:8000/api/v1/analyze-intent \
  -H "Content-Type: application/json" \
  -d '{"intent_text": "I need to install the lodash package to fix the error."}'

# Tool call validation
curl -X POST http://localhost:8000/api/v1/validate-tool-call \
  -H "Content-Type: application/json" \
  -d '{
    "agent_intent": "Install lodash package",
    "tool_name": "install_package",
    "tool_parameters": {"package_manager": "npm", "package_name": "lodash", "version": "4.17.21"}
  }'
```

---

## 🔐 Production Considerations

1. **Model Caching**: The Sentence Transformer model (`all-MiniLM-L6-v2`) is ~90MB and will be downloaded on first run. Consider pre-downloading and mounting it as a volume.
2. **Rate Limiting**: Implement rate limiting on the FastAPI endpoints to prevent abuse.
3. **Authentication**: Add API key or JWT authentication for production deployments.
4. **Monitoring**: Integrate with Prometheus/Grafana for monitoring intent analysis and tool validation metrics.
5. **Scaling**: The service can be scaled horizontally behind a load balancer since it's stateless (model is loaded in memory).

---

## 🧪 Testing the API Service

Run the test script to verify the API service:

```bash
# Start the service first
docker-compose up -d

# Run integration tests
python3 test_api_service.py
```