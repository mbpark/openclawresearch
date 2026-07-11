#!/usr/bin/env python3
"""
Check Suricata status and test network traffic
"""

import subprocess
import os
import json

print("Checking Suricata status...")

# Check if Suricata is running
result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
suricata_running = "suricata -c /Users/mitchparker/.suricata/suricata.yaml -i en0" in result.stdout

print(f"Suricata running: {suricata_running}")

if suricata_running:
    print("✅ Suricata is running on en0")
    
    # Check log directory
    log_dir = "/Users/mitchparker/.suricata/log"
    if os.path.exists(log_dir):
        log_files = os.listdir(log_dir)
        print(f"Log files: {log_files}")
        
        if "eve.json" in log_files:
            # Check last few lines
            with open(f"{log_dir}/eve.json", "r") as f:
                lines = f.readlines()[-10:]
            
            print(f"Last 10 lines of eve.json:")
            for line in lines:
                try:
                    event = json.loads(line.strip())
                    if event.get('event_type') == 'alert':
                        print(f" - Alert: {event.get('alert', {}).get('signature', 'Unknown')}")
                    else:
                        print(f" - {event.get('event_type', 'unknown')} event")
                except json.JSONDecodeError:
                    print(f" - (non-JSON line: {line[:50]}...)")
    else:
        print(f"❌ Log directory not found: {log_dir}")
else:
    print("❌ Suricata is NOT running")
    print("You need to start Suricata manually with sudo privileges")

# Test sending some network traffic
print("\nTesting network traffic generation...")
import socket

try:
    test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    test_socket.settimeout(2)
    
    print("Attempting to connect to a public HTTPS server to generate traffic...")
    
    # This will generate some network traffic
    test_socket.connect(("8.8.8.8", 443))
    print("✅ Network connection successful")
    
    test_socket.sendall(b"GET / HTTP/1.1\r\nHost: example.com\r\nConnection: close\r\n\r\n")
    
    try:
        response = test_socket.recv(4096)
        if response:
            print(f"Received {len(response)} bytes from server")
    except socket.timeout:
        print("No response from server (network may block outbound)")
    
    test_socket.close()
    
except Exception as e:
    print(f"❌ Network test failed: {e}")

print("\nDone!")
