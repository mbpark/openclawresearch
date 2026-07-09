#!/usr/bin/env python3
"""
Stress Testing & Chaos Engineering - Phase 2
Tests resilience patterns under load and with injected failures.
"""

import time
import json
import logging
import random
import asyncio
import requests
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class StressTestResult:
    test_name: str
    duration_seconds: float
    requests_made: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    max_response_time: float
    min_response_time: float
    success_rate: float
    error_breakdown: Dict[str, int]
    notes: str

@dataclass
class ChaosScenario:
    name: str
    description: str
    injection_method: str
    duration: float
    frequency: float
    severity: str

class StressTestManager:
    """Manages stress tests and chaos engineering scenarios"""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.results: List[StressTestResult] = []
        self.chaos_scenarios = self._create_chaos_scenarios()
        self.running = False
    
    def _create_chaos_scenarios(self) -> List[ChaosScenario]:
        """Create list of chaos engineering scenarios"""
        return [
            ChaosScenario(
                name="network_latency",
                description="Simulate network latency spikes",
                injection_method="timeout",
                duration=30.0,
                frequency=0.3,
                severity="medium"
            ),
            ChaosScenario(
                name="service_crash",
                description="Simulate service crashes",
                injection_method="crash",
                duration=20.0,
                frequency=0.2,
                severity="high"
            ),
            ChaosScenario(
                name="error_injection",
                description="Inject random errors",
                injection_method="error",
                duration=25.0,
                frequency=0.4,
                severity="medium"
            ),
            ChaosScenario(
                name="concurrent_load",
                description="Generate high concurrent load",
                injection_method="load",
                duration=60.0,
                frequency=1.0,
                severity="low"
            ),
            ChaosScenario(
                name="checkpoint_overload",
                description="Overload checkpoint system",
                injection_method="checkpoint",
                duration=15.0,
                frequency=0.5,
                severity="high"
            )
        ]
    
    async def _make_request(self, endpoint: str, payload: Dict = None) -> Tuple[float, bool, str]:
        """Make a single request and record timing"""
        start_time = time.time()
        try:
            if endpoint == "health":
                response = requests.get(f"{self.base_url}/health", timeout=10)
            elif endpoint == "transaction":
                response = requests.post(
                    f"{self.base_url}/api/transactions",
                    json=payload or {"amount": 100.0, "description": "test", "user_id": "test"},
                    timeout=10
                )
            elif endpoint == "checkpoint":
                response = requests.post(f"{self.base_url}/api/checkpoints", timeout=10)
            else:
                response = requests.get(f"{self.base_url}/api/status", timeout=10)
            
            duration = time.time() - start_time
            success = response.status_code == 200
            error_msg = "" if success else f"Status {response.status_code}"
            
            return duration, success, error_msg
            
        except Exception as e:
            duration = time.time() - start_time
            return duration, False, str(e)
    
    async def run_load_test(self, total_requests: int = 100, concurrent: int = 10) -> StressTestResult:
        """Run load test with specified number of concurrent requests"""
        logger.info(f"Running load test: {total_requests} requests, {concurrent} concurrent")
        
        start_time = time.time()
        results = []
        errors = {"success": 0, "failure": 0}
        
        async def worker():
            while True:
                # Generate random endpoint
                endpoint = random.choice(["health", "transaction", "status", "checkpoint"])
                duration, success, error = await self._make_request(endpoint)
                
                results.append({
                    "duration": duration,
                    "success": success,
                    "error": error
                })
                
                if success:
                    errors["success"] += 1
                else:
                    errors["failure"] += 1
                
                # Stop condition
                if len(results) >= total_requests:
                    return
        
        # Run concurrent workers
        tasks = [worker() for _ in range(concurrent)]
        await asyncio.gather(*tasks)
        
        duration = time.time() - start_time
        successful = errors["success"]
        failed = errors["failure"]
        response_times = [r["duration"] for r in results]
        
        result = StressTestResult(
            test_name=f"load_test_{total_requests}_req_{concurrent}_concurrent",
            duration_seconds=duration,
            requests_made=len(results),
            successful_requests=successful,
            failed_requests=failed,
            avg_response_time=statistics.mean(response_times),
            max_response_time=max(response_times),
            min_response_time=min(response_times),
            success_rate=(successful / len(results)) * 100,
            error_breakdown=errors,
            notes=f"Duration: {duration:.2f}s, Avg: {statistics.mean(response_times):.4f}s"
        )
        
        self.results.append(result)
        return result
    
    async def run_chaos_test(self, scenario: ChaosScenario) -> StressTestResult:
        """Run chaos engineering test with specified scenario"""
        logger.info(f"Running chaos test: {scenario.name}")
        
        start_time = time.time()
        results = []
        errors = {"success": 0, "failure": 0, "timeout": 0, "error": 0}
        
        # Inject chaos during test
        async def chaos_worker():
            while time.time() - start_time < scenario.duration:
                # Randomly inject chaos based on frequency
                if random.random() < scenario.frequency:
                    await self._inject_chaos(scenario)
                
                # Make normal request
                endpoint = random.choice(["health", "transaction", "status"])
                duration, success, error = await self._make_request(endpoint)
                
                results.append({
                    "duration": duration,
                    "success": success,
                    "error": error
                })
                
                if success:
                    errors["success"] += 1
                else:
                    # Categorize error
                    if "timeout" in error.lower():
                        errors["timeout"] += 1
                    elif "status" in error:
                        errors["error"] += 1
                    else:
                        errors["failure"] += 1
                
                await asyncio.sleep(random.uniform(0.1, 0.5))
        
        await chaos_worker()
        
        duration = time.time() - start_time
        successful = errors["success"]
        failed = sum([errors["failure"], errors["timeout"], errors["error"]])
        response_times = [r["duration"] for r in results]
        
        result = StressTestResult(
            test_name=f"chaos_test_{scenario.name}",
            duration_seconds=duration,
            requests_made=len(results),
            successful_requests=successful,
            failed_requests=failed,
            avg_response_time=statistics.mean(response_times),
            max_response_time=max(response_times),
            min_response_time=min(response_times),
            success_rate=(successful / len(results)) * 100,
            error_breakdown=errors,
            notes=f"Scenario: {scenario.name}, Severity: {scenario.severity}"
        )
        
        self.results.append(result)
        return result
    
    async def _inject_chaos(self, scenario: ChaosScenario):
        """Inject chaos based on scenario type"""
        try:
            if scenario.injection_method == "timeout":
                # Simulate network timeout by hitting an endpoint that hangs
                requests.get(f"{self.base_url}/health", timeout=1)
            elif scenario.injection_method == "crash":
                # Trigger failure injection
                requests.post(f"{self.base_url}/api/failure/inject?failure_type=crash", timeout=5)
            elif scenario.injection_method == "error":
                # Trigger error injection
                requests.post(f"{self.base_url}/api/failure/inject?failure_type=timeout", timeout=5)
            elif scenario.injection_method == "checkpoint":
                # Overload checkpoint system
                for _ in range(5):
                    requests.post(f"{self.base_url}/api/checkpoints", timeout=5)
        except Exception as e:
            pass  # Expected during chaos testing
    
    async def run_full_stress_suite(self):
        """Run comprehensive stress test suite"""
        logger.info("Starting full stress test suite...")
        
        # Phase 1: Basic load tests
        logger.info("Phase 1: Basic load tests")
        for concurrent in [5, 10, 20, 50]:
            result = await self.run_load_test(total_requests=50, concurrent=concurrent)
            logger.info(f"Load test {concurrent} concurrent: {result.success_rate}% success, {result.avg_response_time:.4f}s avg")
        
        # Phase 2: Chaos tests
        logger.info("Phase 2: Chaos tests")
        for scenario in self.chaos_scenarios:
            result = await self.run_chaos_test(scenario)
            logger.info(f"Chaos test {scenario.name}: {result.success_rate}% success, {result.avg_response_time:.4f}s avg")
        
        # Phase 3: Extended load test
        logger.info("Phase 3: Extended load test")
        result = await self.run_load_test(total_requests=200, concurrent=20)
        logger.info(f"Extended load test: {result.success_rate}% success, {result.avg_response_time:.4f}s avg")
        
        # Generate summary report
        self._generate_stress_test_report()
    
    def _generate_stress_test_report(self):
        """Generate comprehensive stress test report"""
        if not self.results:
            return
        
        report = f"""
# Stress Test Report
**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}

## Summary
- **Total Tests Run:** {len(self.results)}
- **Overall Success Rate:** {statistics.mean([r.success_rate for r in self.results]):.1f}%
- **Average Response Time:** {statistics.mean([r.avg_response_time for r in self.results]):.4f}s
- **Max Response Time:** {max(r.max_response_time for r in self.results):.4f}s

## Load Test Results

| Test | Requests | Concurrent | Success Rate | Avg Response Time |
|------|----------|------------|--------------|-------------------|
"""

        for result in self.results:
            if "load_test" in result.test_name:
                report += f"| {result.test_name} | {result.requests_made} | {result.requests_made//50*10} | {result.success_rate:.1f}% | {result.avg_response_time:.4f}s |\n"

        report += "\n## Chaos Test Results\n\n"

        for result in self.results:
            if "chaos_test" in result.test_name:
                report += f"| {result.test_name} | {result.requests_made} | {result.success_rate:.1f}% | {result.avg_response_time:.4f}s | {result.failed_requests} failures |\n"

        report += "\n## Key Findings\n\n"
        
        # Calculate findings
        avg_success_rate = statistics.mean([r.success_rate for r in self.results])
        avg_response_time = statistics.mean([r.avg_response_time for r in self.results])
        
        if avg_success_rate >= 95:
            report += "✅ **Excellent reliability** - System maintains >95% success rate under stress\n"
        elif avg_success_rate >= 90:
            report += "✅ **Good reliability** - System maintains >90% success rate under stress\n"
        else:
            report += "⚠️ **Reliability concerns** - Success rate below 90% under stress\n"
        
        if avg_response_time < 0.1:
            report += "✅ **Excellent performance** - Average response time <100ms\n"
        elif avg_response_time < 0.5:
            report += "✅ **Good performance** - Average response time <500ms\n"
        else:
            report += "⚠️ **Performance concerns** - Average response time >500ms\n"
        
        # Check for specific issues
        high_failure_scenarios = [r for r in self.results if r.success_rate < 80]
        if high_failure_scenarios:
            report += f"\n⚠️ **High failure scenarios detected:** {len(high_failure_scenarios)} tests with <80% success rate\n"
            for scenario in high_failure_scenarios:
                report += f"  - {scenario.test_name}: {scenario.success_rate:.1f}% success\n"
        
        report += "\n## Recommendations\n\n"
        report += "Based on stress test results:\n"
        
        if avg_success_rate < 95:
            report += "- **Improve error handling** - Consider implementing circuit breaker patterns\n"
            report += "- **Add retry logic** - For transient failures\n"
            report += "- **Optimize database queries** - If response times are high\n"
        
        if avg_response_time > 0.5:
            report += "- **Add caching** - For frequently accessed data\n"
            report += "- **Scale horizontally** - Add more instances\n"
            report += "- **Optimize code** - Profile and optimize hot paths\n"
        
        # Save report
        report_path = f"stress_test_report_{int(time.time())}.md"
        with open(report_path, "w") as f:
            f.write(report)
        
        logger.info(f"Stress test report saved to {report_path}")
        
        return report

if __name__ == "__main__":
    async def main():
        manager = StressTestManager()
        
        try:
            await manager.run_full_stress_suite()
            
            print("\n" + "=" * 60)
            print("Stress Testing Complete!")
            print("=" * 60)
            
        except Exception as e:
            logger.error(f"Stress testing failed: {e}")
            raise
    
    asyncio.run(main())
