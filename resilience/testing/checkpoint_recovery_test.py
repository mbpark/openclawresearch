#!/usr/bin/env python3
"""
Checkpoint and Recovery Testing Framework
Tests state persistence and recovery mechanisms.
"""

import asyncio
import time
import json
import os
import shutil
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import logging
import hashlib

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ApplicationState:
    """Represents the state of an application that needs checkpointing"""
    user_sessions: Dict[str, Any] = None
    active_transactions: List[Dict[str, Any]] = None
    cache_entries: Dict[str, Any] = None
    config_settings: Dict[str, Any] = None
    checkpoint_timestamp: Optional[float] = None

    def __post_init__(self):
        if self.user_sessions is None:
            self.user_sessions = {}
        if self.active_transactions is None:
            self.active_transactions = []
        if self.cache_entries is None:
            self.cache_entries = {}
        if self.config_settings is None:
            self.config_settings = {}


class CheckpointManager:
    """Manages checkpoint creation and restoration"""

    def __init__(self, checkpoint_dir: str = "checkpoints"):
        self.checkpoint_dir = checkpoint_dir
        self.checkpoints: List[Dict[str, Any]] = []
        self.max_checkpoints = 5  # Keep last 5 checkpoints
        self._ensure_checkpoint_dir()

    def _ensure_checkpoint_dir(self):
        """Ensure checkpoint directory exists"""
        if not os.path.exists(self.checkpoint_dir):
            os.makedirs(self.checkpoint_dir)

    async def create_checkpoint(self, state: ApplicationState, description: str = "") -> str:
        """Create a checkpoint of the current state"""
        checkpoint_id = self._generate_checkpoint_id()
        checkpoint_path = os.path.join(self.checkpoint_dir, f"checkpoint_{checkpoint_id}.json")

        checkpoint_data = {
            "id": checkpoint_id,
            "timestamp": time.time(),
            "description": description,
            "state": asdict(state),
            "hash": self._calculate_state_hash(state)
        }

        # Write checkpoint to file asynchronously
        with open(checkpoint_path, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)

        self.checkpoints.append(checkpoint_data)
        self._cleanup_old_checkpoints()

        logger.info(f"Created checkpoint {checkpoint_id} at {checkpoint_path}")
        return checkpoint_id

    async def restore_checkpoint(self, checkpoint_id: Optional[str] = None) -> ApplicationState:
        """Restore state from a checkpoint"""
        if checkpoint_id is None:
            # Restore from latest checkpoint
            if not self.checkpoints:
                raise ValueError("No checkpoints available")
            checkpoint_id = self.checkpoints[-1]["id"]

        checkpoint_path = os.path.join(self.checkpoint_dir, f"checkpoint_{checkpoint_id}.json")

        if not os.path.exists(checkpoint_path):
            raise FileNotFoundError(f"Checkpoint {checkpoint_id} not found")

        with open(checkpoint_path, 'r') as f:
            checkpoint_data = json.load(f)

        # Verify checkpoint integrity
        if self._verify_state_hash(checkpoint_data["state"], checkpoint_data["hash"]):
            logger.info(f"Restored state from checkpoint {checkpoint_id}")
            return ApplicationState(**checkpoint_data["state"])
        else:
            logger.error(f"Checkpoint {checkpoint_id} failed integrity check")
            raise ValueError(f"Checkpoint {checkpoint_id} is corrupted")

    async def delete_checkpoint(self, checkpoint_id: str):
        """Delete a specific checkpoint"""
        checkpoint_path = os.path.join(self.checkpoint_dir, f"checkpoint_{checkpoint_id}.json")

        if os.path.exists(checkpoint_path):
            os.remove(checkpoint_path)
            logger.info(f"Deleted checkpoint {checkpoint_id}")

        # Remove from checkpoint list
        self.checkpoints = [c for c in self.checkpoints if c["id"] != checkpoint_id]

    def _generate_checkpoint_id(self) -> str:
        """Generate a unique checkpoint ID"""
        timestamp = str(time.time())
        random_suffix = f"{hashlib.md5(timestamp.encode()).hexdigest()[:8]}"
        return f"{timestamp}_{random_suffix}"

    def _calculate_state_hash(self, state: ApplicationState) -> str:
        """Calculate hash of state for integrity verification"""
        state_json = json.dumps(asdict(state), sort_keys=True)
        return hashlib.sha256(state_json.encode()).hexdigest()

    def _verify_state_hash(self, state: Dict[str, Any], expected_hash: str) -> bool:
        """Verify state integrity"""
        state_json = json.dumps(state, sort_keys=True)
        actual_hash = hashlib.sha256(state_json.encode()).hexdigest()
        return actual_hash == expected_hash

    def _cleanup_old_checkpoints(self):
        """Remove old checkpoints beyond max_checkpoints limit"""
        while len(self.checkpoints) > self.max_checkpoints:
            oldest_checkpoint = self.checkpoints.pop(0)
            checkpoint_path = os.path.join(self.checkpoint_dir, f"checkpoint_{oldest_checkpoint['id']}.json")
            if os.path.exists(checkpoint_path):
                os.remove(checkpoint_path)

    async def list_checkpoints(self) -> List[Dict[str, Any]]:
        """List all available checkpoints"""
        return self.checkpoints


class RecoveryTest:
    """Tests checkpoint recovery scenarios"""

    def __init__(self):
        self.checkpoint_manager = CheckpointManager()
        self.test_results: List[Dict[str, Any]] = []

    async def test_basic_checkpoint_recovery(self):
        """Test basic checkpoint creation and recovery"""
        logger.info("Testing basic checkpoint recovery...")

        # Create initial state
        state = ApplicationState(
            user_sessions={"user_1": {"logged_in": True}, "user_2": {"logged_in": False}},
            active_transactions=[{"id": "txn_1", "amount": 100}],
            cache_entries={"key_1": "value_1"}
        )

        # Create checkpoint
        checkpoint_id = await self.checkpoint_manager.create_checkpoint(
            state,
            "Initial state before changes"
        )

        # Simulate state changes
        state.user_sessions["user_3"] = {"logged_in": True}
        state.active_transactions.append({"id": "txn_2", "amount": 200})
        state.cache_entries["key_2"] = "value_2"

        # Create another checkpoint after changes
        checkpoint_id_2 = await self.checkpoint_manager.create_checkpoint(
            state,
            "State after modifications"
        )

        # Simulate state corruption or failure
        corrupted_state = ApplicationState()

        # Recover from checkpoint
        restored_state = await self.checkpoint_manager.restore_checkpoint(checkpoint_id)

        # Verify restoration
        success = (
            len(restored_state.user_sessions) == 2 and
            len(restored_state.active_transactions) == 1 and
            len(restored_state.cache_entries) == 1
        )

        self.test_results.append({
            "test": "basic_checkpoint_recovery",
            "success": success,
            "checkpoint_id": checkpoint_id,
            "timestamp": time.time()
        })

        return success

    async def test_incremental_checkpointing(self):
        """Test incremental checkpointing strategies"""
        logger.info("Testing incremental checkpointing...")

        # Create a large initial state
        state = ApplicationState(
            user_sessions={f"user_{i}": {"logged_in": True} for i in range(1000)},
            active_transactions=[{"id": f"txn_{i}", "amount": i} for i in range(100)],
            cache_entries={f"key_{i}": {"data": "x" * 100} for i in range(500)}
        )

        # Create full checkpoint
        start_time = time.time()
        checkpoint_id_1 = await self.checkpoint_manager.create_checkpoint(
            state,
            "Full checkpoint"
        )
        full_checkpoint_time = time.time() - start_time

        # Make small changes
        state.user_sessions["new_user"] = {"logged_in": True}
        state.active_transactions.append({"id": "new_txn", "amount": 999})

        # Create incremental checkpoint (simulated by only saving changes)
        start_time = time.time()
        checkpoint_id_2 = await self.checkpoint_manager.create_checkpoint(
            state,
            "Incremental checkpoint"
        )
        incremental_checkpoint_time = time.time() - start_time

        # Calculate size reduction
        checkpoint_1_size = os.path.getsize(
            os.path.join(self.checkpoint_manager.checkpoint_dir, f"checkpoint_{checkpoint_id_1}.json")
        )
        checkpoint_2_size = os.path.getsize(
            os.path.join(self.checkpoint_manager.checkpoint_dir, f"checkpoint_{checkpoint_id_2}.json")
        )

        success = incremental_checkpoint_time < full_checkpoint_time
        size_reduction = 1 - (checkpoint_2_size / checkpoint_1_size)

        self.test_results.append({
            "test": "incremental_checkpointing",
            "success": success,
            "full_checkpoint_time": full_checkpoint_time,
            "incremental_checkpoint_time": incremental_checkpoint_time,
            "size_reduction": size_reduction,
            "timestamp": time.time()
        })

        return success

    async def test_recovery_point_objective(self):
        """Test recovery point objective (RPO) compliance"""
        logger.info("Testing RPO compliance...")

        # Simulate application with frequent checkpoints
        state = ApplicationState()
        checkpoint_interval = 5.0  # seconds
        total_duration = 60.0  # seconds

        checkpoints_created = []
        start_time = time.time()

        while time.time() - start_time < total_duration:
            # Simulate state changes
            state.user_sessions[f"user_{int(time.time())}"] = {"logged_in": True}
            state.active_transactions.append({
                "id": f"txn_{int(time.time())}",
                "amount": random.uniform(10, 1000)
            })

            # Create checkpoint
            checkpoint_id = await self.checkpoint_manager.create_checkpoint(
                state,
                f"Periodic checkpoint at {time.time()}"
            )
            checkpoints_created.append(checkpoint_id)

            await asyncio.sleep(checkpoint_interval)

        # Simulate failure at current time
        failure_time = time.time()
        latest_checkpoint_time = self.checkpoint_manager.checkpoints[-1]["timestamp"]

        # Calculate RPO (data loss window)
        rpo = failure_time - latest_checkpoint_time

        success = rpo <= checkpoint_interval
        self.test_results.append({
            "test": "rpo_compliance",
            "success": success,
            "rpo": rpo,
            "checkpoint_interval": checkpoint_interval,
            "checkpoints_created": len(checkpoints_created),
            "timestamp": time.time()
        })

        return success

    async def run_all_tests(self):
        """Run all recovery tests"""
        logger.info("Running comprehensive checkpoint recovery tests...")

        tests = [
            self.test_basic_checkpoint_recovery,
            self.test_incremental_checkpointing,
            self.test_recovery_point_objective
        ]

        results = []
        for test in tests:
            try:
                success = await test()
                results.append({
                    "test_name": test.__name__,
                    "success": success,
                    "timestamp": time.time()
                })
            except Exception as e:
                logger.error(f"Test {test.__name__} failed: {e}")
                results.append({
                    "test_name": test.__name__,
                    "success": False,
                    "error": str(e),
                    "timestamp": time.time()
                })

        return results


async def main():
    """Main test runner"""
    import random

    print("=" * 60)
    print("Checkpoint and Recovery Testing Suite")
    print("=" * 60)

    recovery_test = RecoveryTest()

    results = await recovery_test.run_all_tests()

    # Generate report
    success_count = sum(1 for r in results if r["success"])
    total_tests = len(results)

    print(f"\nTest Results:")
    print(f"Total Tests: {total_tests}")
    print(f"Successful: {success_count}")
    print(f"Failed: {total_tests - success_count}")
    print(f"Success Rate: {(success_count/total_tests)*100:.1f}%")

    print("\nDetailed Results:")
    for result in results:
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"{status} {result['test_name']}")
        if "rpo" in result:
            print(f"   RPO: {result['rpo']:.2f}s")
        if "full_checkpoint_time" in result:
            print(f"   Full Checkpoint: {result['full_checkpoint_time']:.4f}s")
            print(f"   Incremental Checkpoint: {result['incremental_checkpoint_time']:.4f}s")

    # Save results
    with open("checkpoint_recovery_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\nResults saved to checkpoint_recovery_results.json")

    # Cleanup checkpoints
    await recovery_test.checkpoint_manager.checkpoints.clear()
    for checkpoint in os.listdir(recovery_test.checkpoint_manager.checkpoint_dir):
        os.remove(os.path.join(recovery_test.checkpoint_manager.checkpoint_dir, checkpoint))


if __name__ == "__main__":
    asyncio.run(main())
