#!/usr/bin/env python3
"""
Application Resilience Test Harness
Framework for testing and evaluating application resilience against unexpected events.
"""

import asyncio
import time
import json
import random
import traceback
from dataclasses import dataclass, asdict, field
from typing import Callable, Optional, List, Dict, Any
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FailureType(Enum):
    """Types of failures to simulate"""
    NETWORK_TIMEOUT = "network_timeout"
    NETWORK_PARTITION = "network_partition"
    SERVICE_CRASH = "service_crash"
    DATA_CORRUPTION = "data_corruption"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    DEPENDENCY_FAILURE = "dependency_failure"
    LATENCY_SPIKE = "latency_spike"
    AUTHENTICATION_FAILURE = "authentication_failure"
    RATE_LIMITING = "rate_limiting"
    DISK_FULL = "disk_full"


@dataclass
class TestResult:
    """Result of a single resilience test"""
    test_name: str
    failure_type: FailureType
    success: bool
    recovery_time: Optional[float] = None
    data_loss: Optional[float] = None  # In bytes
    user_impact: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ApplicationState:
    """Represents application state for checkpointing and recovery testing"""
    user_sessions: Dict[str, Any] = field(default_factory=dict)
    pending_transactions: List[Dict[str, Any]] = field(default_factory=list)
    cached_data: Dict[str, Any] = field(default_factory=dict)
    last_checkpoint: Optional[float] = None
    checkpoint_size: int = 0


class ResilienceTester:
    """Base class for resilience testing"""

    def __init__(self, name: str):
        self.name = name
        self.results: List[TestResult] = []
        self.application_state = ApplicationState()

    async def setup(self):
        """Setup test environment"""
        pass

    async def teardown(self):
        """Cleanup test environment"""
        pass

    async def run_test(self, failure_type: FailureType) -> TestResult:
        """Run a single resilience test"""
        test_name = f"{self.name}_{failure_type.value}"
        logger.info(f"Running resilience test: {test_name}")

        start_time = time.time()

        try:
            # Simulate application state before failure
            self._prepare_state()

            # Apply failure
            await self._apply_failure(failure_type)

            # Attempt recovery
            recovery_success = await self._attempt_recovery(failure_type)

            # Calculate metrics
            recovery_time = time.time() - start_time
            data_loss = self._calculate_data_loss()

            return TestResult(
                test_name=test_name,
                failure_type=failure_type,
                success=recovery_success,
                recovery_time=recovery_time,
                data_loss=data_loss,
                user_impact=self._assess_user_impact(),
                metrics=self._collect_metrics()
            )

        except Exception as e:
            logger.error(f"Test {test_name} failed with exception: {e}")
            return TestResult(
                test_name=test_name,
                failure_type=failure_type,
                success=False,
                error_message=str(e),
                recovery_time=time.time() - start_time
            )

    def _prepare_state(self):
        """Prepare application state before test"""
        # Generate some realistic application state
        self.application_state.user_sessions = {
            f"user_{i}": {"logged_in": True, "last_activity": time.time()}
            for i in range(random.randint(100, 1000))
        }
        self.application_state.pending_transactions = [
            {"id": f"txn_{i}", "amount": random.random() * 1000, "status": "pending"}
            for i in range(random.randint(10, 100))
        ]
        self.application_state.cached_data = {
            f"cache_{i}": {"data": random.randbytes(1024), "timestamp": time.time()}
            for i in range(random.randint(50, 500))
        }

    async def _apply_failure(self, failure_type: FailureType):
        """Apply a simulated failure"""
        await asyncio.sleep(0.1)  # Simulate some work before failure

        if failure_type == FailureType.NETWORK_TIMEOUT:
            await asyncio.sleep(random.uniform(5, 30))  # Simulate timeout
        elif failure_type == FailureType.SERVICE_CRASH:
            raise RuntimeError("Simulated service crash")
        elif failure_type == FailureType.DATA_CORRUPTION:
            self.application_state.cached_data = {k: {"corrupted": True} for k in self.application_state.cached_data}
        elif failure_type == FailureType.RESOURCE_EXHAUSTION:
            self.application_state = ApplicationState()  # Clear state
        elif failure_type == FailureType.LATENCY_SPIKE:
            await asyncio.sleep(random.uniform(10, 60))
        # Add more failure types as needed

    async def _attempt_recovery(self, failure_type: FailureType) -> bool:
        """Attempt to recover from failure"""
        start_time = time.time()

        # Default recovery strategy
        if failure_type in [FailureType.SERVICE_CRASH, FailureType.NETWORK_TIMEOUT]:
            # Simulate restart/recovery
            await asyncio.sleep(random.uniform(1, 10))
            self._reinitialize_state()
            return True

        elif failure_type == FailureType.DATA_CORRUPTION:
            # Attempt to restore from checkpoint
            if self.application_state.last_checkpoint:
                await asyncio.sleep(2)  # Simulate restore time
                self._restore_from_checkpoint()
                return True
            return False

        elif failure_type == FailureType.RESOURCE_EXHAUSTION:
            # Simulate resource cleanup and recovery
            await asyncio.sleep(5)
            self.application_state = ApplicationState()
            return True

        return False

    def _reinitialize_state(self):
        """Reinitialize application state after crash"""
        self.application_state = ApplicationState()
        # Simulate loading from persistent storage
        self.application_state.last_checkpoint = time.time()

    def _restore_from_checkpoint(self):
        """Restore state from last checkpoint"""
        # In a real implementation, this would load state from persistent storage
        self.application_state.last_checkpoint = time.time()

    def _calculate_data_loss(self) -> float:
        """Calculate amount of data lost during failure"""
        # Count lost transactions
        lost_transactions = len(self.application_state.pending_transactions)
        # Estimate data loss in bytes (rough estimate)
        return lost_transactions * 256  # 256 bytes per transaction estimate

    def _assess_user_impact(self) -> str:
        """Assess impact on user experience"""
        if not self.application_state.user_sessions:
            return "All users logged out, significant impact"
        elif len(self.application_state.user_sessions) < 50:
            return "Some users affected, moderate impact"
        return "Minimal user impact"

    def _collect_metrics(self) -> Dict[str, Any]:
        """Collect performance and resilience metrics"""
        return {
            "active_sessions": len(self.application_state.user_sessions),
            "pending_transactions": len(self.application_state.pending_transactions),
            "cache_entries": len(self.application_state.cached_data),
            "last_checkpoint": self.application_state.last_checkpoint
        }

    async def run_all_tests(self, failure_types: Optional[List[FailureType]] = None) -> List[TestResult]:
        """Run all configured tests"""
        if failure_types is None:
            failure_types = list(FailureType)

        tasks = [self.run_test(ft) for ft in failure_types]
        self.results = await asyncio.gather(*tasks)
        return self.results

    def generate_report(self) -> str:
        """Generate a summary report of test results"""
        report = f"Resilience Testing Report for {self.name}\n"
        report += "=" * 60 + "\n\n"

        total_tests = len(self.results)
        successful = sum(1 for r in self.results if r.success)
        failed = total_tests - successful

        report += f"Total Tests: {total_tests}\n"
        report += f"Successful: {successful}\n"
        report += f"Failed: {failed}\n"
        report += f"Success Rate: {(successful/total_tests)*100:.1f}%\n\n"

        report += "Results by Failure Type:\n"
        report += "-" * 40 + "\n"

        for result in self.results:
            status = "✅ PASS" if result.success else "❌ FAIL"
            report += f"{status} {result.test_name}\n"
            if result.recovery_time:
                report += f"   Recovery Time: {result.recovery_time:.2f}s\n"
            if result.data_loss:
                report += f"   Data Loss: {result.data_loss} bytes\n"
            if result.user_impact:
                report += f"   User Impact: {result.user_impact}\n"

        return report


# Example usage
async def main():
    tester = ResilienceTester("ExampleApplication")
    await tester.setup()

    results = await tester.run_all_tests()
    print(tester.generate_report())

    # Save results to file
    with open("resilience_test_results.json", "w") as f:
        json.dump([asdict(r) for r in results], f, indent=2)

    await tester.teardown()


if __name__ == "__main__":
    asyncio.run(main())
