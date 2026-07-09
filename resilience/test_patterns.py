#!/usr/bin/env python3
"""
Comprehensive Resilience Patterns Test Suite
Tests circuit breaker, retry, bulkhead, timeout, and fallback patterns.
"""

import asyncio
import time
import json
import logging
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from resilience_patterns import ResilientService, CircuitBreaker, RetryWithExponentialBackoff

@dataclass
class PatternTestResult:
    pattern_name: str
    test_name: str
    success: bool
    response_time: float
    failure_count: int = 0
    retry_count: int = 0
    timestamp: float = None

class ResiliencePatternsTestSuite:
    def __init__(self):
        self.results: List[PatternTestResult] = []
        self.test_count = 0

    async def test_circuit_breaker(self):
        """Test circuit breaker pattern"""
        logger.info("Testing circuit breaker pattern...")
        
        service = ResilientService("CircuitBreakerTest")
        
        # Normal operation
        for i in range(3):
            try:
                result = await service.process_request(f"cb_{i}", {"test": i})
                self.results.append(PatternTestResult(
                    pattern_name="Circuit Breaker",
                    test_name=f"normal_operation_{i}",
                    success=True,
                    response_time=0.0,  # Would measure real time
                    timestamp=time.time()
                ))
            except Exception as e:
                self.results.append(PatternTestResult(
                    pattern_name="Circuit Breaker",
                    test_name=f"normal_operation_{i}",
                    success=False,
                    response_time=0.0,
                    failure_count=1,
                    timestamp=time.time()
                ))
        
        # Trigger circuit breaker
        for i in range(5):  # Should trigger after 5 failures
            try:
                result = await service.process_request(f"cb_fail_{i}", {"fail": i})
            except Exception as e:
                self.results.append(PatternTestResult(
                    pattern_name="Circuit Breaker",
                    test_name=f"trigger_breaker_{i}",
                    success=False,
                    response_time=0.0,
                    failure_count=1,
                    timestamp=time.time()
                ))

    async def test_retry_with_backoff(self):
        """Test retry with exponential backoff"""
        logger.info("Testing retry with exponential backoff...")
        
        retry_handler = RetryWithExponentialBackoff(max_retries=3, base_delay=0.1)
        
        async def flaky_operation():
            if random.random() < 0.7:  # 70% failure rate
                raise Exception("Random failure")
            return {"status": "success"}
        
        start_time = time.time()
        try:
            result = await retry_handler.execute(flaky_operation)
            response_time = time.time() - start_time
            self.results.append(PatternTestResult(
                pattern_name="Retry with Backoff",
                test_name="flaky_operation",
                success=True,
                response_time=response_time,
                timestamp=time.time()
            ))
        except Exception as e:
            response_time = time.time() - start_time
            self.results.append(PatternTestResult(
                pattern_name="Retry with Backoff",
                test_name="flaky_operation",
                success=False,
                response_time=response_time,
                failure_count=1,
                timestamp=time.time()
            ))

    async def test_bulkhead(self):
        """Test bulkhead pattern"""
        logger.info("Testing bulkhead pattern...")
        
        service = ResilientService("BulkheadTest")
        
        # Test with concurrent requests
        async def concurrent_request(request_id):
            try:
                result = await service.process_request(f"bh_{request_id}", {"concurrent": request_id})
                return True
            except Exception as e:
                return False
        
        # Run 10 concurrent requests (bulkhead limit is 10)
        tasks = [concurrent_request(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        success_count = sum(results)
        self.results.append(PatternTestResult(
            pattern_name="Bulkhead",
            test_name="concurrent_requests",
            success=success_count == 10,
            response_time=0.0,
            failure_count=10 - success_count,
            timestamp=time.time()
        ))

    async def test_timeout(self):
        """Test timeout pattern"""
        logger.info("Testing timeout pattern...")
        
        timeout_guard = TimeoutGuard(timeout_seconds=1.0)
        
        async def slow_operation():
            await asyncio.sleep(2.0)  # Takes 2 seconds
            return {"status": "slow_success"}
        
        start_time = time.time()
        try:
            result = await timeout_guard.execute(slow_operation)
            self.results.append(PatternTestResult(
                pattern_name="Timeout",
                test_name="slow_operation",
                success=True,
                response_time=time.time() - start_time,
                timestamp=time.time()
            ))
        except TimeoutError as e:
            response_time = time.time() - start_time
            self.results.append(PatternTestResult(
                pattern_name="Timeout",
                test_name="slow_operation",
                success=False,
                response_time=response_time,
                failure_count=1,
                timestamp=time.time()
            ))

    async def test_fallback(self):
        """Test fallback mechanism"""
        logger.info("Testing fallback mechanism...")
        
        async def primary_operation():
            raise Exception("Primary service failed")
        
        async def fallback_operation():
            return {"status": "fallback", "message": "Using fallback"}
        
        fallback = FallbackHandler(fallback_operation)
        
        start_time = time.time()
        try:
            result = await fallback.execute(primary_operation)
            response_time = time.time() - start_time
            self.results.append(PatternTestResult(
                pattern_name="Fallback",
                test_name="primary_failure",
                success=True,
                response_time=response_time,
                timestamp=time.time()
            ))
        except Exception as e:
            response_time = time.time() - start_time
            self.results.append(PatternTestResult(
                pattern_name="Fallback",
                test_name="primary_failure",
                success=False,
                response_time=response_time,
                failure_count=1,
                timestamp=time.time()
            ))

    async def run_all_tests(self):
        """Run all pattern tests"""
        logger.info("Running comprehensive resilience patterns tests...")
        
        # Import random for flaky operations
        import random
        from resilience_patterns import TimeoutGuard, FallbackHandler
        
        tests = [
            self.test_circuit_breaker,
            self.test_retry_with_backoff,
            self.test_bulkhead,
            self.test_timeout,
            self.test_fallback
        ]
        
        for test in tests:
            try:
                await test()
            except Exception as e:
                logger.error(f"Test {test.__name__} failed: {e}")
        
        return self.results

    def generate_report(self) -> str:
        """Generate test report"""
        if not self.results:
            return "No test results available"
        
        report = f"""
# Resilience Patterns Test Report
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Test Summary
- **Total Tests:** {len(self.results)}
- **Successful:** {sum(1 for r in self.results if r.success)}
- **Failed:** {sum(1 for r in self.results if not r.success)}
- **Success Rate:** {sum(1 for r in self.results if r.success) / len(self.results) * 100:.1f}%

## Results by Pattern
"""
        
        # Group by pattern
        patterns = {}
        for result in self.results:
            if result.pattern_name not in patterns:
                patterns[result.pattern_name] = []
            patterns[result.pattern_name].append(result)
        
        for pattern_name, pattern_results in patterns.items():
            success_count = sum(1 for r in pattern_results if r.success)
            report += f"\n### {pattern_name}\n"
            report += f"- **Tests:** {len(pattern_results)}\n"
            report += f"- **Success Rate:** {success_count / len(pattern_results) * 100:.1f}%\n"
            
            for result in pattern_results:
                status = "✅" if result.success else "❌"
                report += f"- {status} {result.test_name}\n"
        
        return report


if __name__ == "__main__":
    import asyncio
    import random
    from resilience_patterns import TimeoutGuard, FallbackHandler
    
    test_suite = ResiliencePatternsTestSuite()
    
    async def main():
        print("=" * 60)
        print("Resilience Patterns Test Suite")
        print("=" * 60)
        
        results = await test_suite.run_all_tests()
        report = test_suite.generate_report()
        
        print("\n" + report)
        
        # Save results
        with open(f"patterns_test_results_{int(time.time())}.json", "w") as f:
            json.dump([asdict(r) for r in results], f, indent=2)
        
        print(f"\nResults saved to patterns_test_results_{int(time.time())}.json")
    
    asyncio.run(main())
