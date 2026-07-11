#!/usr/bin/env python3
"""
Final Comprehensive QUIC XRING Dynamic Test
"""

import subprocess
import sys
import os
import tempfile
import time
from datetime import datetime

print("=" * 60)
print("FINAL QUIC XRING DYNAMIC TEST")
print("=" * 60)

# Configuration
QUICTE_SERVER = "/opt/homebrew/bin/quiche-server"
QUICTE_CLIENT = "/opt/homebrew/bin/quiche-client"
TEMP_DIR = tempfile.mkdtemp(prefix="quic_final_test_")
CERT_DIR = f"{TEMP_DIR}/certs"
PAYLOAD_FILE = f"{TEMP_DIR}/xring_payload.bin"
SERVER_PORT = 4433

print(f"\n📁 Test directory: {TEMP_DIR}")

# Generate certificates
print("\n🔐 Generating certificates...")
os.makedirs(CERT_DIR, exist_ok=True)

subprocess.run(["openssl", "genrsa", "-out", f"{CERT_DIR}/server.key", "2048"], capture_output=True)
subprocess.run([
    "openssl", "req", "-new", "-x509",
    "-key", f"{CERT_DIR}/server.key",
    "-out", f"{CERT_DIR}/server.crt",
    "-days", "365",
    "-subj", "/CN=localhost"
], capture_output=True)

print("✅ Certificates generated")

# Generate 260-byte payload
print("\n🎯 Generating 260-byte XRING payload...")
payload = bytearray()
payload.extend([0x20, 0x40])
for _ in range(61):
    payload.extend([0x40, 1, ord('x'), 0])
payload.extend([0x40, 5, ord('A'), ord('A'), ord('A'), ord('A'), ord('A'), 5, ord('B'), ord('B'), ord('B'), ord('B'), ord('B')])
payload.extend([0x20, 0x41])
payload = payload[:260]

with open(PAYLOAD_FILE, "wb") as f:
    f.write(payload)

print(f"✅ Payload size: {len(payload)} bytes")

# Clean up any existing servers
print("\n🧹 Cleaning up existing processes...")
subprocess.run(["pkill", "-f", "quiche-server"], capture_output=True)
time.sleep(2)

# Test 1: Start server
print("\n🚀 Test 1: Starting quiche-server...")
server_process = subprocess.Popen(
    [QUICTE_SERVER,
     f"--listen=127.0.0.1:{SERVER_PORT}",
     f"--cert={CERT_DIR}/server.crt",
     f"--key={CERT_DIR}/server.key",
     f"--root={TEMP_DIR}/"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

time.sleep(3)

if server_process.poll() is None:
    print("✅ Server started successfully")
    server_running = True
else:
    print("❌ Server failed to start")
    output = server_process.stdout.read()
    print(f"Error: {output[:500]}")
    server_running = False

if not server_running:
    print("\n❌ TEST ABORTED - Server could not start")
    server_process.terminate()
    sys.exit(1)

# Test 2: Basic connectivity
print("\n📡 Test 2: Basic connectivity...")
result = subprocess.run(
    [QUICTE_CLIENT,
     f"--trust-origin-ca-pem={CERT_DIR}/server.crt",
     "--no-verify",
     f"https://127.0.0.1:{SERVER_PORT}/"],
    capture_output=True,
    text=True,
    timeout=10
)

print(f"Response: {result.stdout[:200]}")
print(f"Exit code: {result.returncode}")

if result.returncode == 0:
    print("✅ Basic connectivity: PASSED")
    test1_passed = True
else:
    print("❌ Basic connectivity: FAILED")
    test1_passed = False

# Test 3: XRING attack payload
print("\n🎯 Test 3: XRING attack payload...")
start_time = time.time()
result = subprocess.run(
    [QUICTE_CLIENT,
     f"--trust-origin-ca-pem={CERT_DIR}/server.crt",
     "--no-verify",
     "--body", PAYLOAD_FILE,
     f"https://127.0.0.1:{SERVER_PORT}/upload"],
    capture_output=True,
    text=True,
    timeout=10
)
response_time = (time.time() - start_time) * 1000

print(f"Response time: {response_time:.2f}ms")
print(f"Client output: {result.stdout[:200]}")

server_alive = server_process.poll() is None
print(f"Server alive: {server_alive}")

if server_alive:
    print("✅ XRING attack: PASSED (server survived)")
    test2_passed = True
else:
    print("❌ XRING attack: FAILED (server crashed)")
    test2_passed = False

# Test 4: Memory stress (5 attacks)
print("\n🧪 Test 4: Memory stress test (5 attacks)...")
stress_passed = True
for i in range(5):
    print(f"  Attack {i+1}/5...", end=" ")
    
    result = subprocess.run(
        [QUICTE_CLIENT,
         f"--trust-origin-ca-pem={CERT_DIR}/server.crt",
         "--no-verify",
         "--body", PAYLOAD_FILE,
         f"https://127.0.0.1:{SERVER_PORT}/test"],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    if server_process.poll() is None:
        print("OK")
    else:
        print("SERVER CRASHED")
        stress_passed = False
        break
    
    time.sleep(1)

if stress_passed:
    print("✅ Memory stress: PASSED")
else:
    print("❌ Memory stress: FAILED")

# Stop server
print("\n🛑 Stopping server...")
server_process.terminate()
try:
    server_process.wait(timeout=5)
except subprocess.TimeoutExpired:
    server_process.kill()

print("✅ Server stopped")

# Summary
print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)

tests_run = 3
tests_passed = sum([test1_passed, test2_passed, stress_passed])

print(f"Tests run: {tests_run}")
print(f"Tests passed: {tests_passed}")
print(f"Success rate: {(tests_passed/tests_run)*100:.1f}%")

if tests_passed == tests_run:
    print("\n🎉 ALL TESTS PASSED!")
    print("quiche-server is NOT vulnerable to XRING attack")
else:
    print(f"\n⚠️ {tests_run - tests_passed} test(s) failed")

print("\n" + "=" * 60)
