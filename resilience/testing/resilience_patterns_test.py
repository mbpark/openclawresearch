#!/usr/bin/env python3
"""
Resilience Patterns Test Suite
Tests different resilience patterns against failure scenarios.
"""

import asyncio
import time
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class CircuitBreakerState:
    state: str = "closed"  # closed, open, half_open
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    threshold: int = 5
    timeout: float = 30.0


class CircuitBreaker:
    """Circuit Breaker Pattern Implementation"""

    def __init__(self, name: str, failure_threshold: int = 5, timeout: float = 30.0):
        self.name = name
        self.state = CircuitBreakerState(threshold=failure_threshold, timeout=timeout)

    async def execute(self, operation: callable, *args, **kwargs) -> Any:
        """Execute operation with circuit breaker protection"""
        if self.state.state == "open":
            if time.time() - self.state.last_failure_time >= self.state.timeout:
                self.state.state = "half_open"
                self.state.failure_count = 0
                logger.info(f"{self.name}: Circuit opening, entering half-open state")
            else:
                logger.warning(f"{self.name}: Circuit is OPEN, rejecting call")
                raise Exception(f"Circuit breaker {self.name} is open")

        try:
            result = await operation(*args, **kwargs)
            self._handle_success()
            return result
        except Exception as e:
            self._handle_failure()
            raise e

    def _handle_success(self):
        """Handle successful operation"""
        self.state.success_count += 1
        if self.state.state == "half_open":
            # If we succeed in half-open, reset to closed
            self.state.state = "closed"
            self.state.failure_count = 0
            logger.info(f"{self.name}: Circuit closed after successful half-open test")
        elif self.state.success_count >= 10:
            # Reset after enough successes
            self.state.success_count = 0

    def _handle_failure(self):
        """Handle failed operation"""
        self.state.failure_count += 1
        self.state.last_failure_time = time.time()
        self.state.success_count = 0

        if self.state.state == "half_open":
            # One failure in half-open sends us back to open
            self.state.state = "open"
            logger.warning(f"{self.name}: Circuit reopened after failure in half-open")
        elif self.state.failure_count >= self.state.threshold:
            self.state.state = "open"
            logger.warning(f"{self.name}: Circuit opened after {self.state.failure_count} failures")


class RetryWithBackoff:
    """Retry Pattern with Exponential Backoff"""

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    async def execute(self, operation: callable, *args, **kwargs) -> Any:
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
    """Bulkhead Pattern Implementation"""

    def __init__(self, name: str, max_concurrent: int = 10):
        self.name = name
        self.max_concurrent = max_concurrent
        self.current_concurrent = 0
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def execute(self, operation: callable, *args, **kwargs) -> Any:
        """Execute operation within bulkhead limits"""
        async with self.semaphore:
            self.current_concurrent += 1
            try:
                return await operation(*args, **kwargs)
            finally:
                self.current_concurrent -= 1


class FallbackHandler:
    """Fallback Mechanism Pattern"""

    def __init__(self, fallback_callback: callable):
        self.fallback_callback = fallback_callback

    async def execute(self, primary_operation: callable, *args, **kwargs) -> Any:
        """Execute primary operation with fallback"""
        try:
            return await primary_operation(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Primary operation failed: {e}")
            logger.info("Executing fallback mechanism")
            return await self.fallback_callback(*args, **kwargs)


class TimeoutGuard:
    """Timeout Pattern Implementation"""

    def __init__(self, timeout_seconds: float):
        self.timeout = timeout_seconds

    async def execute(self, operation: callable, *args, **kwargs) -> Any:
        """Execute operation with timeout"""
        try:
            return await asyncio.wait_for(operation(*args, **kwargs), timeout=self.timeout)
        except asyncio.TimeoutError:
            logger.error(f"Operation timed out after {self.timeout}s")
            raise TimeoutError(f"Operation exceeded {self.timeout}s timeout")


class ResilientService:
    """Example resilient service combining multiple patterns"""

    def __init__(self, name: str):
        self.name = name
        self.circuit_breaker = CircuitBreaker(name)
        self.retry_handler = RetryWithBackoff(max_retries=3)
        self.bulkhead = Bulkhead(name, max_concurrent=10)
        self.timeout_guard = TimeoutGuard(timeout_seconds=30.0)

    async def process_request(self, request_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process a request with full resilience pattern"""

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


async def test_resilience_patterns():
    """Test different resilience patterns"""

    print("=" * 60)
    print("Resilience Patterns Testing Suite")
    print("=" * 60)

    service = ResilientService("PaymentProcessor")

    # Test configuration
    num_requests = 50
    request_ids = [f"req_{i}" for i in range(num_requests)]
    payloads = [{"amount": random.uniform(10, 1000), "currency": "USD"} for _ in range(num_requests)]

    results = []
    start_time = time.time()

    for i in range(num_requests):
        try:
            result = await service.process_request(request_ids[i], payloads[i])
            results.append({
                "request_id": request_ids[i],
                "status": "success",
                "result": result,
                "timestamp": time.time()
            })
        except Exception as e:
            results.append({
                "request_id": request_ids[i],
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            })

    total_time = time.time() - start_time

    # Generate report
    success_count = sum(1 for r in results if r["status"] == "success")
    failure_count = num_requests - success_count

    print(f"\nTest Results:")
    print(f"Total Requests: {num_requests}")
    print(f"Successful: {success_count}")
    print(f"Failed: {failure_count}")
    print(f"Success Rate: {(success_count/num_requests)*100:.1f}%")
    print(f"Total Time: {total_time:.2f}s")
    print(f"Requests/sec: {num_requests/total_time:.2f}")

    # Save detailed results
    report = {
        "test_name": "Resilience Patterns Test",
        "total_requests": num_requests,
        "successful": success_count,
        "failed": failure_count,
        "success_rate": (success_count/num_requests)*100,
        "total_time": total_time,
        "requests_per_second": num_requests/total_time,
        "results": results
    }

    with open("resilience_patterns_results.json", "w") as f:
        json.dump(report, f, indent=2)

    print("\nDetailed results saved to resilience_patterns_results.json")


if __name__ == "__main__":
    import random
    asyncio.run(test_resilience_patterns())
