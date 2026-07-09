"""
Agentic Workflow Graph Controller API Service

FastAPI service exposing the Agentic Workflow Graph Controller and VLMGuard-R1 Intent Analyzer
as REST endpoints for agentic framework integration.
"""

import os
import sys
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Dict, Any, List
import logging
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Add workspace to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from vlmguard_r1_sentence_transformer_analyzer import AdvancedVLMGuardR1IntentAnalyzer
    from agentic_workflow_graph_controller import AgenticWorkflowGraphExecutionController
    INTENT_ANALYZER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import intent analyzer components: {e}")
    INTENT_ANALYZER_AVAILABLE = False

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("agentic_security_controller")

# API Key validation - read from environment variable or use default for development
API_KEY = os.environ.get("SECURITY_API_KEY", "default-dev-api-key-change-in-production")

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# HTTP Bearer security scheme
security = HTTPBearer(auto_error=False)

# Initialize components if available
if INTENT_ANALYZER_AVAILABLE:
    try:
        intent_analyzer = AdvancedVLMGuardR1IntentAnalyzer(model_name="all-MiniLM-L6-v2")
        workflow_controller = AgenticWorkflowGraphExecutionController()
    except Exception as e:
        print(f"Warning: Could not initialize components: {e}")
        intent_analyzer = None
        workflow_controller = None
else:
    intent_analyzer = None
    workflow_controller = None


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


app = FastAPI(title="Agentic Workflow Graph Controller API", version="1.0.0")

# Add rate limit handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Custom dependency to check API key from either Bearer token or x-api-key header
def get_api_key_auth(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to verify API key from Bearer token or x-api-key header."""
    api_key = None
    
    # First, try to get from Bearer token
    if credentials and credentials.credentials:
        api_key = credentials.credentials
    
    # If not found in Bearer token, try x-api-key header
    if not api_key:
        for header_name, header_value in request.headers.items():
            if header_name.lower() == 'x-api-key':
                api_key = header_value
                break
    
    # Validate the API key
    if api_key != API_KEY:
        client_ip = request.client.host if request.client else 'unknown'
        logger.warning(f"UNAUTHORIZED ACCESS ATTEMPT - invalid or missing API key from {client_ip}")
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    
    return api_key


@app.get("/api/v1/health")
def health_check():
    """Health check endpoint - no authentication required."""
    status = "healthy" if INTENT_ANALYZER_AVAILABLE and intent_analyzer is not None else "degraded"
    return {
        "status": status,
        "service": "Agentic Workflow Graph Controller API",
        "components": {
            "intent_analyzer": INTENT_ANALYZER_AVAILABLE and intent_analyzer is not None,
            "workflow_controller": INTENT_ANALYZER_AVAILABLE and workflow_controller is not None
        }
    }


@app.post("/api/v1/analyze-intent")
@limiter.limit("30/minute")
def analyze_intent(request: Request, intent_request: IntentAnalysisRequest, api_key: str = Depends(get_api_key_auth)):
    """Analyze agent intent for malicious patterns using VLMGuard-R1."""
    if not INTENT_ANALYZER_AVAILABLE or intent_analyzer is None:
        raise HTTPException(status_code=503, detail="Intent analyzer not available")
    
    try:
        result = intent_analyzer.process_intent(intent_request.intent_text)
        
        # Log high-risk intents
        if result['analysis']['risk_score'] >= 0.7:
            logger.warning(f"HIGH RISK INTENT DETECTED - Risk Score: {result['analysis']['risk_score']}, Action: {result['action']}, Intent: {intent_request.intent_text[:100]}...")
        
        return {
            "original_intent": result['original_intent'],
            "action": result['action'],
            "risk_score": result['analysis']['risk_score'],
            "reasoning_chain": result['reasoning_chain'],
            "rewritten_intent": result['rewritten_intent'],
            "rewrite_actions": result['rewrite_actions']
        }
    except Exception as e:
        logger.error(f"Error in intent analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/validate-tool-call")
@limiter.limit("30/minute")
def validate_tool_call(request: Request, tool_request: ToolCallRequest, api_key: str = Depends(get_api_key_auth)):
    """Validate and potentially execute a tool call through the Agentic Workflow Graph Controller."""
    if not INTENT_ANALYZER_AVAILABLE or workflow_controller is None:
        raise HTTPException(status_code=503, detail="Workflow controller not available")
    
    try:
        result = workflow_controller.process_agent_intent(
            intent_text=tool_request.agent_intent,
            action_type=tool_request.tool_name,
            parameters=tool_request.tool_parameters
        )
        
        # Log blocked or high-risk tool calls
        if result.get('status') in ['BLOCKED', 'HIGH_RISK']:
            logger.warning(f"BLOCKED/HIGH-RISK TOOL CALL - Status: {result.get('status')}, Intent: {tool_request.agent_intent[:100]}..., Action: {tool_request.tool_name}")
        
        # Extract execution result if available
        execution_result = {}
        if 'execution_result' in result:
            execution_result = result['execution_result']
        elif result.get('status') == 'EXECUTED':
            execution_result = {'status': 'EXECUTED', 'message': 'Tool executed successfully'}
        
        return {
            "status": result.get('status', 'UNKNOWN'),
            "message": result.get('message', 'Tool call processed'),
            "intent_result": result.get('intent_result', {}),
            "execution_result": execution_result
        }
    except Exception as e:
        logger.error(f"Error in tool call validation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)