#!/bin/bash
# Manual traffic generation and Suricata monitoring

echo "=== Manual XRING Traffic Test ==="
echo "Date: $(date)"
echo ""

# Configuration
SERVER_HOST="127.0.0.1"
SERVER_PORT=4433
PAYLOAD_FILE="/tmp/xring_payload_260.bin"

# Generate payload if needed
if [ ! -f "$PAYLOAD_FILE" ]; then
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
EOF
fi

echo "Using payload: $PAYLOAD_FILE"
echo "Payload size: $(stat -f%z "$PAYLOAD_FILE" 2>/dev/null || stat -c%s "$PAYLOAD_FILE" 2>/dev/null) bytes"

# Start quiche-server
echo "Starting quiche-server..."
cert_dir="/tmp/quic_test_certs_manual"
mkdir -p "$cert_dir"

if [ ! -f "$cert_dir/server.crt" ] || [ ! -f "$cert_dir/server.key" ]; then
    openssl genrsa -out "$cert_dir/server.key" 2048 2>/dev/null
    openssl req -new -x509 -key "$cert_dir/server.key" -out "$cert_dir/server.crt" -days 365 -subj "/CN=localhost" 2>/dev/null
fi

/opt/homebrew/bin/quiche-server \
    --listen="$SERVER_HOST:$SERVER_PORT" \
    --cert="$cert_dir/server.crt" \
    --key="$cert_dir/server.key" \
    --root="/tmp/quic_test_manual/" \
    --idle-timeout=10000 \
    > "/tmp/quiche_server.log" 2>&1 &

SERVER_PID=$!
echo "Server PID: $SERVER_PID"
sleep 3

if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo "❌ Server failed to start"
    cat "/tmp/quiche_server.log"
    exit 1
fi

echo "✅ quiche-server running on port $SERVER_PORT"

# Check Suricata status
echo ""
echo "Checking Suricata status..."
if ps aux | grep -q "suricata.*en0"; then
    echo "✅ Suricata is running"
    SURICATA_RUNNING=true
else
    echo "⚠️ Suricata is NOT running"
    echo "You may need to start it with: sudo suricata -c ~/.suricata/suricata.yaml -i en0"
    SURICATA_RUNNING=false
fi

# Generate traffic
echo ""
echo "=== Generating Traffic ==="

# Test 1: Basic GET
echo "1. Basic GET request..."
/opt/homebrew/bin/quiche-client \
    --trust-origin-ca-pem="$cert_dir/server.crt" \
    --no-verify \
    "https://$SERVER_HOST:$SERVER_PORT/" 2>&1 > /dev/null
echo "   ✅ GET completed"

# Test 2: XRING POST attacks
echo "2. XRING payload POST attacks..."
for i in 1 2 3; do
    echo "   POST $i/3..."
    /opt/homebrew/bin/quiche-client \
        --trust-origin-ca-pem="$cert_dir/server.crt" \
        --no-verify \
        --body="$PAYLOAD_FILE" \
        "https://$SERVER_HOST:$SERVER_PORT/upload$i" 2>&1 > /dev/null
done
echo "   ✅ 3 POST requests completed"

# Test 3: Varying sizes
echo "3. Different payload sizes..."
for size in 256 260 264; do
    test_file="/tmp/test_size_${size}.bin"
    head -c $size /dev/zero > "$test_file" 2>/dev/null
    echo "   Testing size $size..."
    /opt/homebrew/bin/quiche-client \
        --trust-origin-ca-pem="$cert_dir/server.crt" \
        --no-verify \
        --body="$test_file" \
        "https://$SERVER_HOST:$SERVER_PORT/size_$size" 2>&1 > /dev/null
done
echo "   ✅ Size variation completed"

# Stop server
echo ""
echo "Stopping quiche-server..."
kill $SERVER_PID 2>/dev/null || true
sleep 2
echo "✅ Server stopped"

# Check EVE logs
echo ""
echo "=== Checking EVE Logs ==="
eve_log="/Users/mitchparker/.suricata/log/eve.json"
if [ -f "$eve_log" ]; then
    echo "EVE log exists: $eve_log"
    line_count=$(wc -l < "$eve_log" 2>/dev/null || echo "0")
    echo "Total lines in EVE log: $line_count"
    
    # Look for recent XRING alerts
    xring_count=$(grep -c -i "xring" "$eve_log" 2>/dev/null || echo "0")
    echo "XRING-related entries: $xring_count"
    
    if [ "$xring_count" -gt 0 ]; then
        echo ""
        echo "=== Recent XRING Alerts ==="
        grep -i "xring" "$eve_log" | tail -20
    else
        echo ""
        echo "No XRING alerts found in EVE log."
        echo ""
        echo "Possible reasons:"
        echo "  - Suricata not capturing traffic to EVE format"
        echo "  - EVE log directory not writable"
        echo "  - Suricata not configured for live capture"
    fi
else
    echo "❌ EVE log not found: $eve_log"
fi

echo ""
echo "=== Manual Test Complete ==="
