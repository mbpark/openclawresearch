#!/usr/bin/env python3
"""
Comprehensive Resilience Testing Script
Tests various resilience patterns and measures recovery performance.
"""

import asyncio
import requests
import time
import json
import logging
import statistics
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
BASE_URL = "http://localhost:8080"
LB_URL = "http://localhost:8081"
TEST_DURATION = 300  # 5 minutes
CONCURRENT_REQUESTS = 10
FAILURE_RATE = 0.1  # 10% failure rate during tests

@dataclass
class TestResult:
    test_name: str
    success: bool
    response_time: Optional[float] = None
    error_message: Optional[str] = None
    timestamp: float = None
    metadata: Optional[Dict] = None

class ResilienceTestSuite:
    def __init__(self):
        self.results: List[TestResult] = []
        self.metrics_history: List[Dict] = []
        self.start_time = None

    async def health_check(self) -> TestResult:
        """Test basic health endpoint"""
        test_name = "health_check"
        try:
            start = time.time()
            response = requests.get(f"{BASE_URL}/health", timeout=10)
            response_time = time.time() - start
            
            if response.status_code == 200:
                return TestResult(
                    test_name=test_name,
                    success=True,
                    response_time=response_time,
                    timestamp=time.time()
                )
            else:
                return TestResult(
                    test_name=test_name,
                    success=False,
                    error_message=f"Status code: {response.status_code}",
                    timestamp=time.time()
                )
        except Exception as e:
            return TestResult(
                test_name=test_name,
                success=False,
                error_message=str(e),
                timestamp=time.time()
            )

    async def create_transaction(self) -> TestResult:
        """Test transaction creation with resilience patterns"""
        test_name = "create_transaction"
        try:
            start = time.time()
            payload = {
                "amount": 100.00,
                "description": "Test transaction",
                "user_id": "test_user_123"
            }
            response = requests.post(
                f"{BASE_URL}/api/transactions",
                json=payload,
                timeout=30
            )
            response_time = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                return TestResult(
                    test_name=test_name,
                    success=True,
                    response_time=response_time,
                    timestamp=time.time(),
                    metadata=data
                )
            else:
                return TestResult(
                    test_name=test_name,
                    success=False,
                    error_message=f"Status code: {response.status_code}, Body: {response.text}",
                    timestamp=time.time()
                )
        except Exception as e:
            return TestResult(
                test_name=test_name,
                success=False,
                error_message=str(e),
                timestamp=time.time()
            )

    async def get_transaction(self, transaction_id: int) -> TestResult:
        """Test transaction retrieval"""
        test_name = f"get_transaction_{transaction_id}"
        try:
            start = time.time()
            response = requests.get(
                f"{BASE_URL}/api/transactions/{transaction_id}",
                timeout=10
            )
            response_time = time.time() - start
            
            if response.status_code == 200:
                return TestResult(
                    test_name=test_name,
                    success=True,
                    response_time=response_time,
                    timestamp=time.time()
                )
            else:
                return TestResult(
                    test_name=test_name,
                    success=False,
                    error_message=f"Status code: {response.status_code}",
                    timestamp=time.time()
                )
        except Exception as e:
            return TestResult(
                test_name=test_name,
                success=False,
                error_message=str(e),
                timestamp=time.time()
            )

    async def create_checkpoint(self) -> TestResult:
        """Test checkpoint creation"""
        test_name = "create_checkpoint"
        try:
            start = time.time()
            response = requests.post(
                f"{BASE_URL}/api/checkpoints",
                json={"description": f"Checkpoint at {datetime.now()}"},
                timeout=30
            )
            response_time = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                return TestResult(
                    test_name=test_name,
                    success=True,
                    response_time=response_time,
                    timestamp=time.time(),
                    metadata=data
                )
            else:
                return TestResult(
                    test_name=test_name,
                    success=False,
                    error_message=f"Status code: {response.status_code}",
                    timestamp=time.time()
                )
        except Exception as e:
            return TestResult(
                test_name=test_name,
                success=False,
                error_message=str(e),
                timestamp=time.time()
            )

    async def recover_from_checkpoint(self, checkpoint_id: str) -> TestResult:
        """Test recovery from checkpoint"""
        test_name = f"recover_{checkpoint_id}"
        try:
            start = time.time()
            response = requests.post(
                f"{BASE_URL}/api/recover/{checkpoint_id}",
                timeout=60
            )
            response_time = time.time() - start
            
            if response.status_code == 200:
                return TestResult(
                    test_name=test_name,
                    success=True,
                    response_time=response_time,
                    timestamp=time.time()
                )
            else:
                return TestResult(
                    test_name=test_name,
                    success=False,
                    error_message=f"Status code: {response.status_code}",
                    timestamp=time.time()
                )
        except Exception as e:
            return TestResult(
                test_name=test_name,
                success=False,
                error_message=str(e),
                timestamp=time.time()
            )

    async def inject_failure(self, failure_type: str) -> TestResult:
        """Test failure injection"""
        test_name = f"inject_{failure_type}"
        try:
            start = time.time()
            response = requests.post(
                f"{BASE_URL}/api/failure/inject?failure_type={failure_type}",
                timeout=10
            )
            response_time = time.time() - start
            
            if response.status_code == 200:
                return TestResult(
                    test_name=test_name,
                    success=True,
                    response_time=response_time,
                    timestamp=time.time()
                )
            else:
                return TestResult(
                    test_name=test_name,
                    success=False,
                    error_message=f"Status code: {response.status_code}",
                    timestamp=time.time()
                )
        except Exception as e:
            return TestResult(
                test_name=test_name,
                success=False,
                error_message=str(e),
                timestamp=time.time()
            )

    async def load_test(self) -> List[TestResult]:
        """Run load test with concurrent requests"""
        test_name = "load_test"
        results = []
        
        async def concurrent_request(request_id: int):
            start = time.time()
            try:
                payload = {
                    "amount": float(request_id),
                    "description": f"Load test transaction {request_id}",
                    "user_id": f"user_{request_id % 10}"
                }
                response = requests.post(
                    f"{BASE_URL}/api/transactions",
                    json=payload,
                    timeout=30
                )
                response_time = time.time() - start
                
                results.append(TestResult(
                    test_name=f"{test_name}_{request_id}",
                    success=response.status_code == 200,
                    response_time=response_time,
                    timestamp=time.time()
                ))
            except Exception as e:
                results.append(TestResult(
                    test_name=f"{test_name}_{request_id}",
                    success=False,
                    error_message=str(e),
                    timestamp=time.time()
                ))

        # Create concurrent tasks
        tasks = [concurrent_request(i) for i in range(CONCURRENT_REQUESTS)]
        await asyncio.gather(*tasks)
        
        return results

    async def run_comprehensive_tests(self):
        """Run all resilience tests"""
        logger.info("Starting comprehensive resilience tests...")
        
        # Test health endpoint
        logger.info("Testing health endpoints...")
        health_results = [await self.health_check()]
        
        # Create transaction and test retrieval
        logger.info("Testing transaction operations...")
        create_result = await self.create_transaction()
        results = [create_result]
        
        if create_result.success:
            get_result = await self.get_transaction(create_result.metadata.get("transaction_id", 1))
            results.append(get_result)
        
        # Test checkpointing
        logger.info("Testing checkpoint operations...")
        checkpoint_result = await self.create_checkpoint()
        results.append(checkpoint_result)
        
        if checkpoint_result.success:
            # List checkpoints first
            try:
                checkpoints_resp = requests.get(f"{BASE_URL}/api/checkpoints", timeout=10)
                if checkpoints_resp.status_code == 200:
                    checkpoints = checkpoints_resp.json()["checkpoints"]
                    if checkpoints:
                        recover_result = await self.recover_from_checkpoint(checkpoints[0]["id"])
                        results.append(recover_result)
            except Exception as e:
                logger.error(f"Checkpoint recovery test failed: {e}")
        
        # Test failure injection
        logger.info("Testing failure injection...")
        for failure_type in ["timeout", "crash", "reset"]:
            failure_result = await self.inject_failure(failure_type)
            results.append(failure_result)
        
        # Run load test
        logger.info("Running load test...")
        load_results = await self.load_test()
        results.extend(load_results)
        
        # Calculate and store metrics
        self._calculate_metrics(results)
        
        return results

    def _calculate_metrics(self, results: List[TestResult]):
        """Calculate statistics from test results"""
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        response_times = [r.response_time for r in successful if r.response_time]
        
        if response_times:
            metrics = {
                "timestamp": time.time(),
                "total_requests": len(results),
                "successful_requests": len(successful),
                "failed_requests": len(failed),
                "success_rate": len(successful) / len(results) * 100,
                "avg_response_time": statistics.mean(response_times),
                "min_response_time": min(response_times),
                "max_response_time": max(response_times),
                "median_response_time": statistics.median(response_times),
                "std_dev": statistics.stdev(response_times) if len(response_times) > 1 else 0
            }
        else:
            metrics = {
                "timestamp": time.time(),
                "total_requests": len(results),
                "successful_requests": len(successful),
                "failed_requests": len(failed),
                "success_rate": 0,
                "avg_response_time": 0,
                "min_response_time": 0,
                "max_response_time": 0,
                "median_response_time": 0,
                "std_dev": 0
            }
        
        self.metrics_history.append(metrics)

    def generate_report(self) -> str:
        """Generate comprehensive test report"""
        if not self.metrics_history:
            return "No test results available"
        
        latest = self.metrics_history[-1]
        report = f"""
# Resilience Test Report
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overall Results
- **Total Requests:** {latest['total_requests']}
- **Successful:** {latest['successful_requests']}
- **Failed:** {latest['failed_requests']}
- **Success Rate:** {latest['success_rate']:.1f}%

## Response Time Analysis
- **Average:** {latest['avg_response_time']:.3f}s
- **Median:** {latest['median_response_time']:.3f}s
- **Min:** {latest['min_response_time']:.3f}s
- **Max:** {latest['max_response_time']:.3f}s
- **Std Dev:** {latest['std_dev']:.3f}s

## Detailed Results
"""
        for result in self.results:
            status = "✅ PASS" if result.success else "❌ FAIL"
            report += f"\n### {status} {result.test_name}\n"
            if result.response_time:
                report += f"- Response Time: {result.response_time:.3f}s\n"
            if result.error_message:
                report += f"- Error: {result.error_message}\n"
        
        return report

async def main():
    """Main test runner"""
    print("=" * 60)
    print("Resilience Test Suite")
    print("=" * 60)
    
    test_suite = ResilienceTestSuite()
    
    try:
        results = await test_suite.run_comprehensive_tests()
        report = test_suite.generate_report()
        
        print("\n" + report)
        
        # Save results to file
        with open(f"resilience_test_results_{int(time.time())}.json", "w") as f:
            json.dump({
                "timestamp": time.time(),
                "metrics": test_suite.metrics_history,
                "detailed_results": [asdict(r) for r in results]
            }, f, indent=2)
        
        print(f"\nResults saved to resilience_test_results_{int(time.time())}.json")
        
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
