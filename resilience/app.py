#!/usr/bin/env python3
"""
Resilience Test Application
A FastAPI application designed to test resilience patterns and failure recovery.
"""

import os
import time
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
import redis
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import random

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Resilience Test Application", version="1.0.0")

# Prometheus metrics
REQUEST_COUNT = Counter('app_requests_total', 'Total number of requests', ['endpoint', 'method'])
REQUEST_DURATION = Histogram('app_request_duration_seconds', 'Request duration')
ACTIVE_CONNECTIONS = Gauge('app_active_connections', 'Number of active connections')
ERROR_COUNT = Counter('app_errors_total', 'Total number of errors', ['error_type'])
RECOVERY_TIME = Histogram('app_recovery_time_seconds', 'Time to recover from failure')
CHECKPOINT_COUNT = Counter('app_checkpoints_total', 'Total number of checkpoints created')

# Application state
class AppState:
    def __init__(self):
        self.start_time = time.time()
        self.request_count = 0
        self.checkpoint_count = 0
        self.last_checkpoint = None
        self.failures_simulated = 0
        self.recovery_count = 0

app_state = AppState()

# Database connection
db_pool = None
redis_client = None

# Configuration
TEST_MODE = os.getenv("TEST_MODE", "normal")  # normal, failure, recovery
FAILURE_RATE = float(os.getenv("FAILURE_RATE", "0.1"))  # 10% chance of failure in test mode
SIMULATE_LATENCY = float(os.getenv("SIMULATE_LATENCY", "0"))  # Additional latency in ms

# Pydantic models
class Transaction(BaseModel):
    amount: float
    description: str
    user_id: str

class UserSession(BaseModel):
    user_id: str
    username: str
    email: str

class CheckpointRequest(BaseModel):
    description: str = ""

# Database operations
async def init_db():
    global db_pool
    try:
        db_pool = psycopg2.pool.SimpleConnectionPool(
            1, 10,
            host=os.getenv("DB_HOST", "database"),
            port=os.getenv("DB_PORT", "5432"),
            user=os.getenv("DB_USER", "testuser"),
            password=os.getenv("DB_PASSWORD", "testpass"),
            database=os.getenv("DB_NAME", "testdb")
        )
        logger.info("Database connection pool initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

async def init_redis():
    global redis_client
    try:
        redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            decode_responses=True
        )
        await redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error(f"Redis initialization failed: {e}")
        redis_client = None

# Middleware for resilience patterns
class ResilienceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        endpoint = request.url.path
        method = request.method
        
        REQUEST_COUNT.labels(endpoint=endpoint, method=method).inc()
        app_state.request_count += 1
        
        start_time = time.time()
        ACTIVE_CONNECTIONS.set(app_state.request_count)
        
        try:
            # Simulate failures if in test mode
            if TEST_MODE == "failure" and random.random() < FAILURE_RATE:
                ERROR_COUNT.labels(error_type="simulated_failure").inc()
                app_state.failures_simulated += 1
                raise HTTPException(status_code=500, detail="Simulated service failure")
            
            response = await call_next(request)
            
            # Track request duration
            duration = time.time() - start_time
            REQUEST_DURATION.observe(duration)
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            REQUEST_DURATION.observe(duration)
            
            if isinstance(e, HTTPException):
                ERROR_COUNT.labels(error_type=e.detail).inc()
                return JSONResponse(
                    status_code=e.status_code,
                    content={"error": e.detail, "timestamp": time.time()}
                )
            else:
                ERROR_COUNT.labels(error_type="unhandled_exception").inc()
                return JSONResponse(
                    status_code=500,
                    content={"error": str(e), "timestamp": time.time()}
                )

class CircuitBreakerMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, failure_threshold=5, timeout=30.0):
        super().__init__(app)
        self.app = app
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open

    async def dispatch(self, request, call_next):
        # Check circuit breaker state
        if self.state == "open":
            if time.time() - self.last_failure_time >= self.timeout:
                self.state = "half_open"
                self.failure_count = 0
                logger.info("Circuit breaker: transitioning to half-open state")
            else:
                logger.warning("Circuit breaker: open - rejecting request")
                return JSONResponse(
                    status_code=503,
                    content={"error": "Service temporarily unavailable", "circuit": "open"}
                )

        try:
            response = await call_next(request)
            self._handle_success()
            return response
        except Exception as e:
            self._handle_failure()
            raise e

    def _handle_success(self):
        if self.state == "half_open":
            self.state = "closed"
            self.failure_count = 0
            logger.info("Circuit breaker: closed after successful half-open test")
        elif self.failure_count >= 10:
            self.failure_count = 0

    def _handle_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == "half_open":
            self.state = "open"
            logger.warning("Circuit breaker: reopened after failure in half-open")
        elif self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker: opened after {self.failure_count} failures")

# Routes
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "uptime": time.time() - app_state.start_time,
        "request_count": app_state.request_count,
        "failures_simulated": app_state.failures_simulated,
        "recovery_count": app_state.recovery_count,
        "checkpoint_count": app_state.checkpoint_count
    }
    
    # Check database connectivity
    try:
        conn = db_pool.getconn()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.putbackconn()
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = f"disconnected: {str(e)}"
    
    return health_status

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(
        content=generate_latest(),
        status_code=200,
        media_type=CONTENT_TYPE_LATEST
    )

@app.post("/api/transactions")
async def create_transaction(transaction: Transaction, x_request_id: Optional[str] = Header(None)):
    """Create a new transaction"""
    start_time = time.time()
    
    # Simulate additional latency if configured
    if SIMULATE_LATENCY > 0:
        await asyncio.sleep(SIMULATE_LATENCY / 1000)
    
    # Store transaction in database
    try:
        conn = db_pool.getconn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO transactions (amount, description, user_id, created_at) VALUES (%s, %s, %s, %s) RETURNING id",
            (transaction.amount, transaction.description, transaction.user_id, datetime.now())
        )
        transaction_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.putbackconn()
        
        # Store in Redis for quick access
        if redis_client:
            redis_key = f"transaction:{transaction_id}"
            redis_data = {
                "id": transaction_id,
                "amount": transaction.amount,
                "description": transaction.description,
                "user_id": transaction.user_id,
                "created_at": time.time()
            }
            redis_client.setex(redis_key, 3600, json.dumps(redis_data))
        
        return {
            "success": True,
            "transaction_id": transaction_id,
            "timestamp": time.time(),
            "request_id": x_request_id
        }
    except Exception as e:
        ERROR_COUNT.labels(error_type="transaction_creation").inc()
        logger.error(f"Transaction creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transaction failed: {str(e)}")

@app.get("/api/transactions/{transaction_id}")
async def get_transaction(transaction_id: int, x_request_id: Optional[str] = Header(None)):
    """Get a transaction by ID"""
    try:
        # Try Redis first
        if redis_client:
            redis_key = f"transaction:{transaction_id}"
            cached_data = redis_client.get(redis_key)
            if cached_data:
                return json.loads(cached_data)
        
        # Fall back to database
        conn = db_pool.getconn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM transactions WHERE id = %s", (transaction_id,))
        transaction = cur.fetchone()
        cur.close()
        conn.putbackconn()
        
        if transaction:
            return dict(transaction)
        else:
            raise HTTPException(status_code=404, detail="Transaction not found")
    except Exception as e:
        ERROR_COUNT.labels(error_type="transaction_fetch").inc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch transaction: {str(e)}")

@app.post("/api/checkpoints")
async def create_checkpoint(request: CheckpointRequest):
    """Create a checkpoint of application state"""
    start_time = time.time()
    
    checkpoint_data = {
        "id": f"checkpoint_{int(time.time() * 1000)}",
        "timestamp": time.time(),
        "description": request.description,
        "app_state": {
            "request_count": app_state.request_count,
            "failures_simulated": app_state.failures_simulated,
            "recovery_count": app_state.recovery_count,
            "checkpoint_count": app_state.checkpoint_count
        },
        "active_transactions": [],
        "user_sessions": []
    }
    
    # In a real application, we would capture more state here
    # For now, we'll just store the checkpoint metadata
    
    # Store checkpoint metadata
    checkpoint_file = f"checkpoints/checkpoint_{checkpoint_data['id']}.json"
    os.makedirs("checkpoints", exist_ok=True)
    
    with open(checkpoint_file, 'w') as f:
        json.dump(checkpoint_data, f, indent=2)
    
    app_state.checkpoint_count += 1
    app_state.last_checkpoint = checkpoint_data["id"]
    
    recovery_time = time.time() - start_time
    RECOVERY_TIME.observe(recovery_time)
    CHECKPOINT_COUNT.inc()
    
    return {
        "success": True,
        "checkpoint_id": checkpoint_data["id"],
        "recovery_time": recovery_time,
        "timestamp": time.time()
    }

@app.get("/api/checkpoints")
async def list_checkpoints():
    """List all available checkpoints"""
    checkpoints = []
    
    if os.path.exists("checkpoints"):
        for filename in os.listdir("checkpoints"):
            if filename.startswith("checkpoint_") and filename.endswith(".json"):
                checkpoint_path = os.path.join("checkpoints", filename)
                with open(checkpoint_path, 'r') as f:
                    checkpoint_data = json.load(f)
                    checkpoints.append(checkpoint_data)
    
    return {
        "checkpoints": checkpoints,
        "count": len(checkpoints),
        "current": app_state.last_checkpoint
    }

@app.post("/api/recover/{checkpoint_id}")
async def recover_from_checkpoint(checkpoint_id: str):
    """Recover application state from a checkpoint"""
    start_time = time.time()
    
    checkpoint_file = f"checkpoints/checkpoint_{checkpoint_id}.json"
    
    if not os.path.exists(checkpoint_file):
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    
    with open(checkpoint_file, 'r') as f:
        checkpoint_data = json.load(f)
    
    # Simulate recovery process
    await asyncio.sleep(2)  # Simulate time to restore state
    
    # Restore application state
    restored_state = checkpoint_data["app_state"]
    app_state.request_count = restored_state["request_count"]
    app_state.failures_simulated = restored_state["failures_simulated"]
    app_state.recovery_count += 1
    app_state.last_checkpoint = checkpoint_id
    
    recovery_time = time.time() - start_time
    RECOVERY_TIME.observe(recovery_time)
    
    return {
        "success": True,
        "checkpoint_id": checkpoint_id,
        "recovery_time": recovery_time,
        "restored_state": restored_state,
        "timestamp": time.time()
    }

@app.post("/api/failure/inject")
async def inject_failure(failure_type: str = "timeout"):
    """Manually inject a failure for testing"""
    global TEST_MODE, FAILURE_RATE
    
    if failure_type == "timeout":
        app_state.failures_simulated += 1
        ERROR_COUNT.labels(error_type="manual_timeout").inc()
        return {"success": True, "message": f"Injected {failure_type} failure", "timestamp": time.time()}
    
    elif failure_type == "crash":
        app_state.failures_simulated += 1
        ERROR_COUNT.labels(error_type="manual_crash").inc()
        app_state.recovery_count += 1
        return {"success": True, "message": f"Injected {failure_type} failure", "timestamp": time.time()}
    
    elif failure_type == "reset":
        app_state.failures_simulated = 0
        app_state.recovery_count = 0
        return {"success": True, "message": "Reset failure counters", "timestamp": time.time()}
    
    return {"success": False, "error": "Unknown failure type"}

@app.get("/api/status")
async def get_status():
    """Get comprehensive application status"""
    return {
        "app_state": {
            "uptime": time.time() - app_state.start_time,
            "request_count": app_state.request_count,
            "failures_simulated": app_state.failures_simulated,
            "recovery_count": app_state.recovery_count,
            "checkpoint_count": app_state.checkpoint_count,
            "last_checkpoint": app_state.last_checkpoint,
            "test_mode": TEST_MODE,
            "failure_rate": FAILURE_RATE
        },
        "timestamp": time.time(),
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
