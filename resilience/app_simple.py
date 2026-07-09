#!/usr/bin/env python3
"""
Simple Resilience Test Application
Uses SQLite for persistence - no external database needed.
"""

import os
import time
import json
import asyncio
import logging
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import random

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Simple Resilience Test", version="1.0.0")

# Prometheus metrics
REQUEST_COUNT = Counter('app_requests_total', 'Total requests', ['endpoint', 'method'])
REQUEST_DURATION = Histogram('app_request_duration_seconds', 'Request duration')
ACTIVE_CONNECTIONS = Gauge('app_active_connections', 'Active connections')
ERROR_COUNT = Counter('app_errors_total', 'Total errors', ['error_type'])
RECOVERY_TIME = Histogram('app_recovery_time_seconds', 'Recovery time')
CHECKPOINT_COUNT = Counter('app_checkpoints_total', 'Checkpoint count')

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

# SQLite database
DB_PATH = "resilience_test.db"

def init_db():
    """Initialize SQLite database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            description TEXT,
            user_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create index
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON transactions(user_id)')
    
    # Create app state table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS app_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            checkpoint_id TEXT UNIQUE,
            state_data JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("SQLite database initialized")

# Model classes
class Transaction(BaseModel):
    amount: float
    description: str
    user_id: str

# Resilience middleware
class ResilienceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        endpoint = request.url.path
        method = request.method
        
        REQUEST_COUNT.labels(endpoint=endpoint, method=method).inc()
        app_state.request_count += 1
        
        start_time = time.time()
        ACTIVE_CONNECTIONS.set(app_state.request_count)
        
        try:
            # Simulate failures in test mode
            if os.getenv("TEST_MODE") == "failure" and random.random() < float(os.getenv("FAILURE_RATE", "0.1")):
                ERROR_COUNT.labels(error_type="simulated_failure").inc()
                app_state.failures_simulated += 1
                raise HTTPException(status_code=500, detail="Simulated service failure")
            
            response = await call_next(request)
            duration = time.time() - start_time
            REQUEST_DURATION.observe(duration)
            
            return response
        except Exception as e:
            duration = time.time() - start_time
            REQUEST_DURATION.observe(duration)
            
            if isinstance(e, HTTPException):
                ERROR_COUNT.labels(error_type=e.detail).inc()
                return Response(
                    content=json.dumps({"error": e.detail, "timestamp": time.time()}),
                    status_code=e.status_code,
                    media_type="application/json"
                )
            else:
                ERROR_COUNT.labels(error_type="unhandled_exception").inc()
                return Response(
                    content=json.dumps({"error": str(e), "timestamp": time.time()}),
                    status_code=500,
                    media_type="application/json"
                )

# Database operations
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "uptime": time.time() - app_state.start_time,
        "request_count": app_state.request_count,
        "failures_simulated": app_state.failures_simulated,
        "recovery_count": app_state.recovery_count,
        "checkpoint_count": app_state.checkpoint_count
    }

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
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO transactions (amount, description, user_id) VALUES (?, ?, ?)",
            (transaction.amount, transaction.description, transaction.user_id)
        )
        transaction_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
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
    """Get transaction by ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,))
        transaction = cursor.fetchone()
        conn.close()
        
        if transaction:
            return dict(transaction)
        else:
            raise HTTPException(status_code=404, detail="Transaction not found")
    except Exception as e:
        ERROR_COUNT.labels(error_type="transaction_fetch").inc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch transaction: {str(e)}")

@app.post("/api/checkpoints")
async def create_checkpoint(description: str = ""):
    """Create a checkpoint of application state"""
    start_time = time.time()
    
    checkpoint_data = {
        "id": f"checkpoint_{int(time.time() * 1000)}",
        "timestamp": time.time(),
        "description": description,
        "app_state": {
            "request_count": app_state.request_count,
            "failures_simulated": app_state.failures_simulated,
            "recovery_count": app_state.recovery_count,
            "checkpoint_count": app_state.checkpoint_count
        }
    }
    
    # Store checkpoint
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO app_state (checkpoint_id, state_data) VALUES (?, ?)",
        (checkpoint_data["id"], json.dumps(checkpoint_data))
    )
    conn.commit()
    conn.close()
    
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
    """List all checkpoints"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM app_state ORDER BY created_at DESC")
    checkpoints = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {
        "checkpoints": checkpoints,
        "count": len(checkpoints),
        "current": app_state.last_checkpoint
    }

@app.post("/api/recover/{checkpoint_id}")
async def recover_from_checkpoint(checkpoint_id: str):
    """Recover from checkpoint"""
    start_time = time.time()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT state_data FROM app_state WHERE checkpoint_id = ?", (checkpoint_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    
    # Simulate recovery
    await asyncio.sleep(1)
    
    # Restore state
    checkpoint_data = json.loads(row["state_data"])
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
    """Inject failure for testing"""
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
    """Get application status"""
    return {
        "app_state": {
            "uptime": time.time() - app_state.start_time,
            "request_count": app_state.request_count,
            "failures_simulated": app_state.failures_simulated,
            "recovery_count": app_state.recovery_count,
            "checkpoint_count": app_state.checkpoint_count,
            "last_checkpoint": app_state.last_checkpoint
        },
        "timestamp": time.time(),
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    init_db()
    uvicorn.run(app, host="0.0.0.0", port=8080)
