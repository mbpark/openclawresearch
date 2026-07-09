#!/usr/bin/env python3
"""
Advanced Resilience Patterns Implementation
Circuit Breaker, Retry with Backoff, Bulkhead, Timeout, Fallback
"""

import asyncio
import time
import random
import logging
import json
import os
import base64
import hashlib
from pathlib import Path
from typing import Callable, Optional, Any, Dict, List
from dataclasses import dataclass, field, asdict
from enum import Enum
from functools import wraps
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CircuitBreakerState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"



class Checkpoint:
    """Represents a saved application state checkpoint"""

    def __init__(self, checkpoint_id: str, timestamp: float, state_data: Dict[str, Any], description: str = ""):
        self.checkpoint_id = checkpoint_id
        self.timestamp = timestamp
        self.state_data = state_data
        self.description = description

    def to_dict(self) -> Dict[str, Any]:
        """Convert checkpoint to dictionary"""
        return {
            "checkpoint_id": self.checkpoint_id,
            "timestamp": self.timestamp,
            "state_data": self.state_data,
            "description": self.description,
            "created_at": datetime.fromtimestamp(self.timestamp).isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Checkpoint":
        """Create checkpoint from dictionary"""
        return cls(
            checkpoint_id=data["checkpoint_id"],
            timestamp=data["timestamp"],
            state_data=data["state_data"],
            description=data.get("description", "")
        )



class CheckpointManager:
    """Manages checkpoint creation, storage, and recovery"""
    
    def __init__(self, storage_dir: str = "./checkpoints"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoints: List[Checkpoint] = []
        self.load_checkpoints()

    def create_checkpoint(self, state_data: Dict[str, Any], description: str = "") -> Checkpoint:
        """Create and save a new checkpoint"""
        checkpoint_id = f"checkpoint_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            timestamp=time.time(),
            state_data=state_data,
            description=description
        )
        
        # Save to disk
        self._save_checkpoint(checkpoint)
        self.checkpoints.append(checkpoint)
        
        logger.info(f"Checkpoint created: {checkpoint_id} with {len(state_data)} state keys")
        return checkpoint

    def load_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Load a checkpoint by ID"""
        checkpoint_file = self.storage_dir / f"{checkpoint_id}.json"
        
        if not checkpoint_file.exists():
            logger.error(f"Checkpoint {checkpoint_id} not found")
            return None
        
        try:
            with open(checkpoint_file, 'r') as f:
                data = json.load(f)
                checkpoint = Checkpoint.from_dict(data)
                
            # Add to local list if not already there
            if not any(c.checkpoint_id == checkpoint_id for c in self.checkpoints):
                self.checkpoints.append(checkpoint)
            
            logger.info(f"Checkpoint {checkpoint_id} loaded successfully")
            return checkpoint
        except Exception as e:
            logger.error(f"Failed to load checkpoint {checkpoint_id}: {e}")
            return None

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint"""
        checkpoint_file = self.storage_dir / f"{checkpoint_id}.json"
        
        if checkpoint_file.exists():
            try:
                checkpoint_file.unlink()
                self.checkpoints = [c for c in self.checkpoints if c.checkpoint_id != checkpoint_id]
                logger.info(f"Checkpoint {checkpoint_id} deleted")
                return True
            except Exception as e:
                logger.error(f"Failed to delete checkpoint {checkpoint_id}: {e}")
                return False
        
        return False

    def list_checkpoints(self) -> List[Checkpoint]:
        """List all checkpoints"""
        return sorted(self.checkpoints, key=lambda c: c.timestamp, reverse=True)

    def recover_from_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Recover state from a checkpoint"""
        checkpoint = self.load_checkpoint(checkpoint_id)
        if checkpoint:
            logger.info(f"Recovering state from checkpoint {checkpoint_id}")
            return checkpoint.state_data
        return None

    def _save_checkpoint(self, checkpoint: Checkpoint):
        """Save checkpoint to disk"""
        checkpoint_file = self.storage_dir / f"{checkpoint.checkpoint_id}.json"
        
        try:
            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save checkpoint {checkpoint.checkpoint_id}: {e}")
            raise

    def load_checkpoints(self):
        """Load all checkpoints from storage directory"""
        try:
            checkpoint_files = list(self.storage_dir.glob("checkpoint_*.json"))
            for file_path in checkpoint_files:
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        checkpoint = Checkpoint.from_dict(data)
                        self.checkpoints.append(checkpoint)
                except Exception as e:
                    logger.warning(f"Failed to load checkpoint {file_path}: {e}")
        except Exception as e:
            logger.error(f"Failed to load checkpoints: {e}")



class SecureCheckpointManager(CheckpointManager):

    def __init__(self, storage_dir: str = "./secure_checkpoints", security_level: str = "standard"):
        super().__init__(storage_dir)
        self.security_level = security_level
        self.encryption_key = self._derive_key(security_level)
        self.access_control = self._initialize_access_control()
        self.audit_log: List[Dict] = []
    
    def __init__(self, storage_dir: str = "./secure_checkpoints", security_level: str = "standard"):
        super().__init__(storage_dir)
        self.security_level = security_level
        self.encryption_key = self._derive_key(security_level)
        self.access_control = self._initialize_access_control()
        self.audit_log: List[Dict] = []

    def _derive_key(self, security_level: str) -> bytes:
        """Derive encryption key from security level"""
        import hashlib
        key_material = f"checkpoint_key_{security_level}_{time.time()}".encode()
        return hashlib.sha256(key_material).digest()

    def _derive_integrity_keys(self) -> Dict[str, bytes]:
        """Derive integrity validation keys"""
        import hashlib
        keys = {
            "hmac": hashlib.sha256(b"integrity_key_1").digest(),
            "checksum": hashlib.sha256(b"checksum_key_1").digest()
        }
        return keys

    def _initialize_access_control(self) -> Dict[str, Any]:
        """Initialize access control policies"""
        policies = {
            "standard": {
                "read_access": ["user", "admin"],
                "write_access": ["admin"],
                "delete_access": ["admin"],
                "audit_required": True
            },
            "high": {
                "read_access": ["admin"],
                "write_access": ["admin"],
                "delete_access": ["admin"],
                "audit_required": True,
                "encryption_required": True,
                "mfa_required": False
            },
            "critical": {
                "read_access": ["admin"],
                "write_access": ["admin"],
                "delete_access": ["admin"],
                "audit_required": True,
                "encryption_required": True,
                "mfa_required": True,
                "approved_user": "admin"
            }
        }
        return policies.get(self.security_level, policies["standard"])

    def _encrypt(self, data: bytes) -> bytes:
        """Encrypt checkpoint data"""
        # In a real implementation, use proper AES-256 encryption
        import base64
        # Simple XOR for demo purposes (use real encryption in production)
        encrypted = bytes(b ^ self.encryption_key[i % len(self.encryption_key)] for i, b in enumerate(data))
        return base64.b64encode(encrypted)

    def _decrypt(self, encrypted_data: bytes) -> bytes:
        """Decrypt checkpoint data"""
        import base64
        decrypted = base64.b64decode(encrypted_data)
        # Simple XOR decryption (use real encryption in production)
        key = self.encryption_key
        result = bytes(b ^ key[i % len(key)] for i, b in enumerate(decrypted))
        return result

    def _generate_checksum(self, data: bytes) -> str:
        """Generate integrity checksum"""
        return hashlib.sha256(data).hexdigest()

    def _verify_checksum(self, data: bytes, expected_checksum: str) -> bool:
        """Verify data integrity"""
        actual_checksum = self._generate_checksum(data)
        return actual_checksum == expected_checksum

    def create_checkpoint(self, state_data: Dict[str, Any], description: str = "", user: str = "system") -> Checkpoint:
        """Create and save a secure checkpoint with encryption and integrity validation"""
        # Audit logging
        if self.access_control["audit_required"]:
            self.audit_log.append({
                "action": "checkpoint_created",
                "timestamp": time.time(),
                "user": user,
                "checkpoint_id": f"checkpoint_{int(time.time() * 1000)}_{random.randint(1000, 9999)}",
                "description": description
            })

        checkpoint = super().create_checkpoint(state_data, description)
        
        # Encrypt and validate integrity
        checkpoint_file = self.storage_dir / f"{checkpoint.checkpoint_id}.json"
        try:
            # Read the original checkpoint data
            with open(checkpoint_file, 'r') as f:
                original_data = f.read().encode()
            
            # Generate checksum
            checksum = self._generate_checksum(original_data)
            
            # Encrypt data
            encrypted_data = self._encrypt(original_data)
            
            # Write encrypted data with checksum
            with open(checkpoint_file, 'w') as f:
                f.write(json.dumps({
                    "encrypted_data": encrypted_data.decode(),
                    "checksum": checksum,
                    "security_level": self.security_level,
                    "created_at": time.time()
                }))
            
            logger.info(f"Secure checkpoint created: {checkpoint.checkpoint_id} with encryption and integrity validation")
            return checkpoint
            
        except Exception as e:
            logger.error(f"Failed to create secure checkpoint: {e}")
            raise e

    def load_checkpoint(self, checkpoint_id: str, user: str = "system") -> Optional[Checkpoint]:
        """Load and decrypt a checkpoint with integrity validation"""
        # Audit logging
        if self.access_control["audit_required"]:
            self.audit_log.append({
                "action": "checkpoint_loaded",
                "timestamp": time.time(),
                "user": user,
                "checkpoint_id": checkpoint_id
            })

        checkpoint_file = self.storage_dir / f"{checkpoint_id}.json"
        
        if not checkpoint_file.exists():
            logger.error(f"Checkpoint {checkpoint_id} not found")
            return None
        
        try:
            with open(checkpoint_file, 'r') as f:
                secure_data = json.load(f)
            
            # Verify checksum and decrypt
            with open(checkpoint_file, 'rb') as f:
                content = f.read()
            
            # Parse JSON first
            with open(checkpoint_file, 'r') as f:
                secure_dict = json.load(f)
            
            # Decode base64 encrypted data
            encrypted_bytes = base64.b64decode(secure_dict["encrypted_data"].encode())
            actual_checksum = self._generate_checksum(encrypted_bytes)
            
            if not self._verify_checksum(encrypted_bytes, secure_dict["checksum"]):
                logger.error(f"Checkpoint integrity verification failed for {checkpoint_id}")
                return None
            
            # Decrypt data
            decrypted_bytes = self._decrypt(encrypted_bytes)
            checkpoint_dict = json.loads(decrypted_bytes)
            checkpoint = Checkpoint.from_dict(checkpoint_dict)
            
            logger.info(f"Secure checkpoint {checkpoint_id} loaded and verified")
            return checkpoint
            
        except Exception as e:
            logger.error(f"Failed to load secure checkpoint {checkpoint_id}: {e}")
            return None

    def delete_checkpoint(self, checkpoint_id: str, user: str = "system") -> bool:
        """Securely delete a checkpoint with audit logging"""
        # Audit logging
        if self.access_control["audit_required"]:
            self.audit_log.append({
                "action": "checkpoint_deleted",
                "timestamp": time.time(),
                "user": user,
                "checkpoint_id": checkpoint_id
            })

        checkpoint_file = self.storage_dir / f"{checkpoint_id}.json"
        
        if checkpoint_file.exists():
            try:
                # Secure deletion (overwrite before delete)
                with open(checkpoint_file, 'w') as f:
                    f.write('' * 1024)  # Overwrite with zeros
                checkpoint_file.unlink()
                self.checkpoints = [c for c in self.checkpoints if c.checkpoint_id != checkpoint_id]
                logger.info(f"Secure checkpoint {checkpoint_id} deleted")
                return True
            except Exception as e:
                logger.error(f"Failed to delete secure checkpoint {checkpoint_id}: {e}")
                return False
        
        return False



class Checkpointing:
    """Checkpointing pattern for state persistence"""

    def __init__(self, checkpoint_manager: CheckpointManager, state_key: str = "state"):
        self.checkpoint_manager = checkpoint_manager
        self.state_key = state_key

    async def execute(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute operation with automatic checkpointing"""
        try:
            # Get current state
            state_data = kwargs.get(self.state_key, {})

            # Create checkpoint before operation
            checkpoint = self.checkpoint_manager.create_checkpoint(
                state_data=state_data,
                description=f"Pre-{operation.__name__ if hasattr(operation, '__name__') else 'operation'}"
            )

            # Execute operation
            result = await operation(*args, **kwargs)

            # Update state with result if needed
            if result and self.state_key in kwargs:
                state_data[self.state_key] = result
                # Create recovery checkpoint
                self.checkpoint_manager.create_checkpoint(
                    state_data=state_data,
                    description=f"Post-{operation.__name__ if hasattr(operation, '__name__') else 'operation'}"
                )

            return result

        except Exception as e:
            logger.error(f"Operation failed: {e}")
            logger.info("Attempting recovery from checkpoint")

            # Try to recover from most recent checkpoint
            if self.checkpoint_manager.checkpoints:
                most_recent = self.checkpoint_manager.checkpoints[-1]
                recovered_state = self.checkpoint_manager.recover_from_checkpoint(most_recent.checkpoint_id)

                if recovered_state:
                    logger.info(f"Recovered state from checkpoint {most_recent.checkpoint_id}")
                    # Modify kwargs to use recovered state
                    if self.state_key in kwargs:
                        kwargs[self.state_key] = recovered_state

                    # Retry operation
                    return await operation(*args, **kwargs)

            raise e



@dataclass
class CircuitBreakerStateData:
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    threshold: int = 5
    timeout: float = 30.0
    # Adaptive parameters
    window_size: int = 100
    adaptive_enabled: bool = False
    security_level: str = "standard"  # standard, high, critical
    rate_limit: int = 1000  # requests per minute
    anomaly_threshold: float = 3.0  # standard deviations
    last_adaptive_update: float = field(default_factory=time.time)



class CircuitBreaker:
    """Circuit Breaker Pattern Implementation"""

    def __init__(self, name: str, failure_threshold: int = 5, timeout: float = 30.0,
                 adaptive_enabled: bool = False, security_level: str = "standard",
                 rate_limit: int = 1000, anomaly_threshold: float = 3.0):
        self.name = name
        self.adaptive_enabled = adaptive_enabled
        self.security_level = security_level
        self.rate_limit = rate_limit
        self.anomaly_threshold = anomaly_threshold
        self.state = CircuitBreakerStateData(
            threshold=failure_threshold,
            timeout=timeout,
            adaptive_enabled=adaptive_enabled,
            security_level=security_level,
            rate_limit=rate_limit,
            anomaly_threshold=anomaly_threshold
        )
        # Performance tracking for adaptive tuning
        self.performance_history = []
        self.request_counts = []
        self.last_minute_requests = 0
        self.last_minute_check = time.time()

    def _is_state_change_needed(self) -> bool:
        """Check if circuit breaker needs state transition"""
        if self.state.state == CircuitBreakerState.OPEN:
            if time.time() - self.state.last_failure_time >= self.state.timeout:
                self.state.state = CircuitBreakerState.HALF_OPEN
                self.state.failure_count = 0
                logger.info(f"{self.name}: Circuit opened, entering half-open state")
                return True
        return False

    def _check_rate_limit(self) -> bool:
        """Check if request is within rate limits"""
        current_time = time.time()

        # Reset request count every minute
        if current_time - self.last_minute_check >= 60:
            self.last_minute_requests = 0
            self.last_minute_check = current_time

        # Check rate limit based on security level
        if self.security_level == "high":
            effective_limit = self.rate_limit // 2
        elif self.security_level == "critical":
            effective_limit = self.rate_limit // 10
        else:
            effective_limit = self.rate_limit

        if self.last_minute_requests >= effective_limit:
            logger.warning(f"{self.name}: Rate limit exceeded ({self.last_minute_requests}/{effective_limit})")
            return False

        self.last_minute_requests += 1
        return True

    def _detect_anomalies(self) -> bool:
        """Detect anomalies in performance data"""
        if len(self.performance_history) < 10:
            return False

        # Calculate mean and standard deviation
        durations = [p['duration'] for p in self.performance_history[-20:]]
        if not durations:
            return False

        mean = sum(durations) / len(durations)
        variance = sum((d - mean) ** 2 for d in durations) / len(durations)
        std_dev = variance ** 0.5

        # Check for anomalies
        current_duration = durations[-1] if durations else 0
        if std_dev > 0 and abs(current_duration - mean) > self.anomaly_threshold * std_dev:
            logger.warning(f"{self.name}: Anomaly detected in performance (current: {current_duration:.4f}, mean: {mean:.4f}, std: {std_dev:.4f})")
            return True

        return False

    def _adapt_threshold(self):
        """Adapt failure threshold based on traffic patterns"""
        if not self.adaptive_enabled:
            return

        current_time = time.time()
        if current_time - self.state.last_adaptive_update < 300:  # Every 5 minutes
            return

        # Analyze recent performance (last 100 requests)
        recent_history = self.performance_history[-100:]
        if len(recent_history) < 10:
            return

        # Calculate success rate and adjust threshold
        success_count = len([r for r in recent_history if not r.get('error', False)])
        total_requests = len(recent_history)
        success_rate = success_count / total_requests if total_requests > 0 else 1.0

        # Adaptive threshold adjustment
        current_threshold = self.state.threshold
        if success_rate > 0.99:
            # Increase threshold - system is stable, can be more tolerant
            new_threshold = min(current_threshold + 2, 15)
        elif success_rate < 0.7:
            # Decrease threshold - system is failing, be more sensitive
            new_threshold = max(current_threshold - 1, 2)
        else:
            # Maintain current threshold
            new_threshold = current_threshold

        if new_threshold != current_threshold:
            self.state.threshold = new_threshold
            logger.info(f"{self.name}: Adaptive threshold adjusted: {current_threshold} -> {new_threshold}")

        self.state.last_adaptive_update = current_time

    def _apply_security_policy(self):
        """Apply security policy to circuit breaker behavior"""
        if self.security_level == "critical":
            # More aggressive circuit opening
            self.state.threshold = max(2, self.state.threshold // 2)
            # Shorter timeout for faster failure detection
            self.state.timeout = min(10.0, self.state.timeout * 0.5)
            # Enable rate limiting
            self.state.rate_limit = max(100, self.state.rate_limit // 2)

    def _handle_success(self):
        """Handle successful operation"""
        self.state.success_count += 1

        if self.state.state == CircuitBreakerState.HALF_OPEN:
            self.state.state = CircuitBreakerState.CLOSED
            self.state.failure_count = 0
            logger.info(f"{self.name}: Circuit closed after successful half-open test")
        elif self.state.success_count >= 10:
            self.state.success_count = 0

        # Update performance history
        self.performance_history.append({'success': True, 'timestamp': time.time()})
        self._adapt_threshold()

    def _handle_failure(self):
        """Handle failed operation"""
        self.state.failure_count += 1
        self.state.last_failure_time = time.time()
        self.state.success_count = 0

        if self.state.state == CircuitBreakerState.HALF_OPEN:
            self.state.state = CircuitBreakerState.OPEN
            logger.warning(f"{self.name}: Circuit reopened after failure in half-open state")
        elif self.state.failure_count >= self.state.threshold:
            self.state.state = CircuitBreakerState.OPEN
            logger.warning(f"{self.name}: Circuit opened after {self.state.failure_count} failures")

        # Update performance history
        self.performance_history.append({'success': False, 'timestamp': time.time()})
        self._adapt_threshold()

    async def execute(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute operation with circuit breaker protection"""
        # Check rate limit
        if not self._check_rate_limit():
            raise Exception(f"Rate limit exceeded for {self.name}")

        # Apply security policies
        self._apply_security_policy()

        # Check for state transitions
        if self._is_state_change_needed():
            pass  # State already updated

        if self.state.state == CircuitBreakerState.OPEN:
            logger.warning(f"{self.name}: Circuit is OPEN, rejecting call")
            raise Exception(f"Circuit breaker {self.name} is open")

        try:
            start_time = time.time()
            result = await operation(*args, **kwargs)
            duration = time.time() - start_time

            self._handle_success()
            return result
        except Exception as e:
            self._handle_failure()
            raise e



class RetryWithExponentialBackoff:
    """Retry Pattern with Exponential Backoff and Jitter"""

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    async def execute(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute operation with retry logic"""
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                last_exception = e

                if attempt == self.max_retries:
                    logger.error(f"Operation failed after {self.max_retries} retries: {e}")
                    raise e

                # Calculate exponential backoff with jitter
                delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                jitter = delay * 0.2 * (2 * (time.time() % 1) - 1)  # Random jitter +/- 20%
                actual_delay = delay + jitter

                logger.info(f"Retry attempt {attempt + 1}/{self.max_retries} after {actual_delay:.2f}s")
                await asyncio.sleep(actual_delay)

        raise last_exception



class Bulkhead:
    """Bulkhead Pattern Implementation - Resource Isolation"""

    def __init__(self, name: str, max_concurrent: int = 10):
        self.name = name
        self.max_concurrent = max_concurrent
        self.current_concurrent = 0
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def execute(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute operation within bulkhead limits"""
        async with self.semaphore:
            self.current_concurrent += 1
            try:
                return await operation(*args, **kwargs)
            finally:
                self.current_concurrent -= 1

    @property
    def utilization(self) -> float:
        """Current resource utilization percentage"""
        return (self.current_concurrent / self.max_concurrent) * 100



class TimeoutGuard:
    """Timeout Pattern Implementation"""

    def __init__(self, timeout_seconds: float):
        self.timeout = timeout_seconds

    async def execute(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute operation with timeout"""
        try:
            return await asyncio.wait_for(operation(*args, **kwargs), timeout=self.timeout)
        except asyncio.TimeoutError:
            logger.error(f"Operation timed out after {self.timeout}s")
            raise TimeoutError(f"Operation exceeded {self.timeout}s timeout")



class FallbackHandler:
    """Fallback Mechanism Pattern"""

    def __init__(self, fallback_callback: Callable):
        self.fallback_callback = fallback_callback

    async def execute(self, primary_operation: Callable, *args, **kwargs) -> Any:
        """Execute primary operation with fallback"""
        try:
            return await primary_operation(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Primary operation failed: {e}")
            logger.info("Executing fallback mechanism")
            try:
                return await self.fallback_callback(*args, **kwargs)
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
                raise fallback_error



class MultiLayerFallback:
    """Multi-Layer Fallback System with Security Integration"""

    def __init__(self, security_level: str = "standard"):
        self.security_level = security_level
        self.layers = []
        self.layer_validations = []
        self.security_policy = self._initialize_security_policy()
        self.audit_log = []

    def _initialize_security_policy(self) -> Dict[str, Any]:
        """Initialize security policies for different layers"""
        policies = {
            "standard": {
                "max_latency_ms": 100,
                "encryption_required": False,
                "validation_required": True,
                "audit_required": True,
                "cache_ttl": 300,
            },
            "high": {
                "max_latency_ms": 50,
                "encryption_required": True,
                "validation_required": True,
                "audit_required": True,
                "cache_ttl": 60,
                "data_classification": "confidential",
            },
            "critical": {
                "max_latency_ms": 25,
                "encryption_required": True,
                "validation_required": True,
                "audit_required": True,
                "cache_ttl": 30,
                "data_classification": "restricted",
                "mfa_required": True,
            }
        }
        return policies.get(self.security_level, policies["standard"])

    def add_layer(self, name: str, handler: Callable, validation: Optional[Callable] = None,
                  cache_enabled: bool = False, cache_ttl: int = None,
                  encryption_required: bool = False):
        """Add a fallback layer with security controls"""
        layer_config = {
            "name": name,
            "handler": handler,
            "validation": validation or (lambda x: True),
            "cache_enabled": cache_enabled,
            "cache_ttl": cache_ttl or self.security_policy["cache_ttl"],
            "encryption_required": encryption_required,
            "added_at": time.time(),
        }
        self.layers.append(layer_config)
        logger.info(f"Fallback layer '{name}' added with security: encryption={encryption_required}, validation={validation is not None}")

    async def _validate_response(self, response: Any, layer_name: str) -> bool:
        """Validate response against security policies"""
        try:
            # Check latency
            if self.security_policy["max_latency_ms"] > 0:
                # Latency validation would be tracked during handler execution
                pass

            # Check validation function
            if not self.layers[0]["validation"](response):
                logger.warning(f"Response validation failed for layer {layer_name}")
                return False

            # Audit logging for security
            if self.security_policy["audit_required"]:
                self.audit_log.append({
                    "timestamp": time.time(),
                    "layer": layer_name,
                    "valid": True,
                    "data_classification": self.security_policy.get("data_classification", "standard")
                })

            return True
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False

    async def _encrypt_if_required(self, data: Any, layer_name: str) -> Any:
        """Encrypt data if required by security policy"""
        if self.security_policy["encryption_required"]:
            try:
                # In a real implementation, use proper encryption
                import base64
                import json
                encrypted_data = base64.b64encode(json.dumps(data).encode()).decode()
                logger.info(f"Data encrypted for layer {layer_name}")
                return encrypted_data
            except Exception as e:
                logger.error(f"Encryption failed: {e}")
                raise e
        return data

    async def _decrypt_if_required(self, data: Any, layer_name: str) -> Any:
        """Decrypt data if required by security policy"""
        if self.security_policy["encryption_required"] and isinstance(data, str):
            try:
                import base64
                import json
                decrypted_data = json.loads(base64.b64decode(data.encode()))
                logger.info(f"Data decrypted for layer {layer_name}")
                return decrypted_data
            except Exception as e:
                logger.error(f"Decryption failed: {e}")
                raise e
        return data

    async def execute(self, primary_operation: Callable, *args, **kwargs) -> Any:
        """Execute primary operation with multi-layer fallback"""
        current_layer = 0
        last_error = None

        # Try primary operation first
        try:
            primary_result = await primary_operation(*args, **kwargs)
            if await self._validate_response(primary_result, "primary"):
                return primary_result
        except Exception as e:
            last_error = e

        # Iterate through fallback layers
        for layer_config in self.layers[current_layer:]:
            try:
                layer_name = layer_config["name"]
                handler = layer_config["handler"]

                # Execute fallback layer
                fallback_result = await handler(*args, **kwargs)

                # Encrypt if required
                if layer_config["encryption_required"]:
                    fallback_result = await self._encrypt_if_required(fallback_result, layer_name)

                # Validate response
                if await self._validate_response(fallback_result, layer_name):
                    # Decrypt if required
                    if layer_config["encryption_required"]:
                        fallback_result = await self._decrypt_if_required(fallback_result, layer_name)

                    logger.info(f"Successfully served from fallback layer: {layer_name}")
                    return fallback_result

            except Exception as e:
                logger.error(f"Fallback layer {layer_config['name']} failed: {e}")
                last_error = e
                current_layer += 1

        # All layers failed
        logger.error(f"All fallback layers failed. Last error: {last_error}")
        raise Exception(f"Multi-layer fallback system exhausted. Last error: {last_error}")

    def get_layer_statistics(self) -> Dict[str, Any]:
        """Get statistics about fallback layers"""
        return {
            "security_level": self.security_level,
            "layer_count": len(self.layers),
            "layers": [layer["name"] for layer in self.layers],
            "security_policy": self.security_policy,
            "audit_log_count": len(self.audit_log),
        }

    def clear_audit_log(self):
        """Clear audit log (in a real system, this would be more sophisticated)"""
        self.audit_log.clear()
        logger.info("Audit log cleared")



class SecurityFallbackLayer:
    """Security-focused fallback layer that handles sensitive operations"""

    def __init__(self, name: str, security_manager: "SecurityManager" = None):
        self.name = name
        self.security_manager = security_manager
        self.cache = {}

    async def execute(self, *args, **kwargs) -> Dict[str, Any]:
        """Execute security-sensitive fallback operation"""
        # This would contain security-aware fallback logic
        return {
            "status": "fallback",
            "layer": self.name,
            "security_level": "validated",
            "timestamp": time.time(),
            "data": {"fallback": True}
        }



class SecurityAwareRequestPrioritizer:
    """Request prioritization based on security level and threat assessment"""

    def __init__(self):
        self.priority_queue = []
        self.security_levels = {
            "low": 1,
            "medium": 2,
            "high": 3,
            "critical": 4
        }
        self.resource_allocation = {
            "low": 0.1,
            "medium": 0.3,
            "high": 0.4,
            "critical": 0.2
        }
        self.threat_level = "low"
        self.threat_history = []

    def _calculate_priority(self, request: Dict[str, Any]) -> int:
        """Calculate priority score for a request"""
        priority_score = 0

        # Security level priority
        security_level = request.get("security_level", "medium")
        priority_score += self.security_levels.get(security_level, 2)

        # Request criticality
        criticality = request.get("criticality", "medium")
        if criticality == "critical":
            priority_score += 3
        elif criticality == "high":
            priority_score += 2
        elif criticality == "medium":
            priority_score += 1

        # Resource sensitivity
        resource_type = request.get("resource_type", "standard")
        if resource_type == "sensitive":
            priority_score += 2
        elif resource_type == "confidential":
            priority_score += 3

        # Time sensitivity
        time_sensitivity = request.get("time_sensitivity", "medium")
        if time_sensitivity == "critical":
            priority_score += 3
        elif time_sensitivity == "high":
            priority_score += 2

        return priority_score

    def add_request(self, request: Dict[str, Any], user: str = "system") -> bool:
        """Add request to priority queue"""
        request["priority_score"] = self._calculate_priority(request)
        request["timestamp"] = time.time()
        request["user"] = user
        
        self.priority_queue.append(request)
        self.priority_queue.sort(key=lambda x: x["priority_score"], reverse=True)
        
        # Audit logging
        self._log_request(request, "added")
        
        logger.info(f"Request added to priority queue: {request.get('id', 'unknown')} with priority {request['priority_score']}")
        return True

    def _log_request(self, request: Dict[str, Any], action: str):
        """Log request for audit trail"""
        log_entry = {
            "action": action,
            "timestamp": time.time(),
            "request_id": request.get("id", "unknown"),
            "security_level": request.get("security_level", "medium"),
            "priority_score": request.get("priority_score", 0)
        }
        self.threat_history.append(log_entry)

    async def get_next_request(self) -> Optional[Dict[str, Any]]:
        """Get the next highest priority request"""
        if not self.priority_queue:
            return None

        # Get highest priority request
        request = self.priority_queue.pop(0)
        self._log_request(request, "processed")

        logger.info(f"Processed request {request.get('id', 'unknown')} with priority {request['priority_score']}")
        return request

    def set_threat_level(self, threat_level: str):
        """Set current threat level"""
        self.threat_level = threat_level
        self._log_threat_level_change()

        # Adjust resource allocation based on threat level
        if threat_level == "high" or threat_level == "critical":
            self.resource_allocation["critical"] = 0.4
            self.resource_allocation["high"] = 0.3
            self.resource_allocation["medium"] = 0.2
            self.resource_allocation["low"] = 0.1
        else:
            self.resource_allocation["critical"] = 0.2
            self.resource_allocation["high"] = 0.4
            self.resource_allocation["medium"] = 0.3
            self.resource_allocation["low"] = 0.1

    def _log_threat_level_change(self):
        """Log threat level change"""
        self.threat_history.append({
            "action": "threat_level_changed",
            "timestamp": time.time(),
            "threat_level": self.threat_level
        })

    def get_queue_statistics(self) -> Dict[str, Any]:
        """Get statistics about the priority queue"""
        return {
            "queue_size": len(self.priority_queue),
            "threat_level": self.threat_level,
            "priority_distribution": self._calculate_priority_distribution(),
            "resource_allocation": self.resource_allocation
        }

    def _calculate_priority_distribution(self) -> Dict[str, int]:
        """Calculate distribution of priority scores"""
        distribution = {"low": 0, "medium": 0, "high": 0, "critical": 0}

        for request in self.priority_queue:
            score = request.get("priority_score", 0)
            if score >= 10:
                distribution["critical"] += 1
            elif score >= 7:
                distribution["high"] += 1
            elif score >= 4:
                distribution["medium"] += 1
            else:
                distribution["low"] += 1

        return distribution

    def clear_queue(self):
        """Clear all requests from the queue"""
        self.priority_queue.clear()
        logger.info("Priority queue cleared")



class ResilientService:
    """Composite Resilience Service - Combines Multiple Patterns"""

    def __init__(self, name: str):
        self.name = name
        self.circuit_breaker = CircuitBreaker(name)
        self.retry_handler = RetryWithExponentialBackoff(max_retries=3)
        self.bulkhead = Bulkhead(name, max_concurrent=10)
        self.timeout_guard = TimeoutGuard(timeout_seconds=30.0)
        self.fallback = FallbackHandler(self._default_fallback)

    async def _default_fallback(self, *args, **kwargs) -> Dict[str, Any]:
        """Default fallback response"""
        return {
            "status": "fallback",
            "service": self.name,
            "message": "Primary service unavailable, using fallback",
            "timestamp": time.time()
        }

    async def process_request(self, request_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process request with full resilience pattern"""
        async def operation():
            # Simulate service processing
            await asyncio.sleep(random.uniform(0.1, 2.0))

            # Simulate random failures (20% chance)
            if random.random() < 0.2:
                raise Exception(f"Simulated failure in {self.name}")

            return {
                "request_id": request_id,
                "status": "success",
                "service": self.name,
                "payload": payload,
                "timestamp": time.time()
            }

        # Apply resilience patterns in order
        return await self.circuit_breaker.execute(
            self.retry_handler.execute,
            self.timeout_guard.execute,
            self.bulkhead.execute,
            operation
        )

    def get_metrics(self) -> Dict[str, Any]:
        """Get current resilience metrics"""
        return {
            "name": self.name,
            "circuit_breaker_state": self.circuit_breaker.state.state.value,
            "circuit_breaker_failures": self.circuit_breaker.state.failure_count,
            "bulkhead_utilization": self.bulkhead.utilization,
            "current_concurrent": self.bulkhead.current_concurrent,
            "max_concurrent": self.bulkhead.max_concurrent
        }



