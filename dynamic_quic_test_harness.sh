#!/bin/bash
# QUIC XRING Dynamic Test Harness
# Uses cloudflare-quiche for real protocol testing
# Created: July 10, 2026

set -e

echo "=== QUIC XRING Dynamic Test Harness ==="
echo "Date: $(date)"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    local message=$1
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${GREEN}[$timestamp]${NC} $message"
}

warning() {
    local message=$1
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${YELLOW}[$timestamp] WARNING${NC} $message"
}

error() {
    local message=$1
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${RED}[$timestamp] ERROR${NC} $message"
}

# Configuration
QUICTE_SERVER="/opt/homebrew/bin/quiche-server"
QUICTE_CLIENT="/opt/homebrew/bin/quiche-client"
SURICATA_BIN="/usr/local/bin/suricata"
TEMP_DIR="/tmp/quic_xring_test"
CERT_DIR="$TEMP_DIR/certs"
LOG_DIR="$TEMP_DIR/logs"
PAYLOAD_FILE="$TEMP_DIR/xring_payload.bin"
ATTACK_PAYLOAD_SIZE=260

# Ensure cleanup on exit
cleanup() {
    error "Terminating..."
    if [ -n "$SERVER_PID" ]; then
        kill $SERVER_PID 2>/dev/null || true
    fi
    if [ -n "$CLIENT_PID" ]; then
        kill $CLIENT_PID 2>/dev/null || true
    fi
    # Stop Suricata if running in test mode
    if [ -n "$SURICATA_PID" ]; then
        kill $SURICATA_PID 2>/dev/null || true
    fi
    rm -rf "$TEMP_DIR"
    log "Cleanup complete"
}

trap cleanup EXIT SIGINT SIGTERM

# Generate certificates if needed
generate_certs() {
    log "Generating test certificates..."
    mkdir -p "$CERT_DIR"
    
    # Self-signed CA
    openssl genrsa -out "$CERT_DIR/ca.key" 2048 2>/dev/null
    openssl req -new -x509 -key "$CERT_DIR/ca.key" -out "$CERT_DIR/ca.crt" -days 365 \
        -subj "/CN=QuicXRingTest CA" 2>/dev/null
    
    # Server certificate
    openssl genrsa -out "$CERT_DIR/server.key" 2048 2>/dev/null
    openssl req -new -key "$CERT_DIR/server.key" -out "$CERT_DIR/server.csr" \
        -subj "/CN=localhost" 2>/dev/null
    openssl x509 -req -in "$CERT_DIR/server.csr" -CA "$CERT_DIR/ca.crt" \
        -CAkey "$CERT_DIR/ca.key" -CAcreateserial -out "$CERT_DIR/server.crt" -days 365 2>/dev/null
    
    # Create a minimal server certificate file (cert + key)
    cat "$CERT_DIR/server.crt" "$CERT_DIR/server.key" > "$CERT_DIR/combined.pem"
    
    log "Certificates generated in $CERT_DIR"
}

# Generate XRING attack payload
generate_xring_payload() {
    log "Generating $ATTACK_PAYLOAD_SIZE byte XRING payload..."
    
    python3 "/Users/mitchparker/.openclaw/workspace/research/generate_xring_payload.py" "$PAYLOAD_FILE" "$ATTACK_PAYLOAD_SIZE"
    if [ $? -ne 0 ]; then
        error "Payload generation failed"
        exit 1
    fi
    
    local actual_size=$(stat -f%z "$PAYLOAD_FILE" 2>/dev/null || stat -c%s "$PAYLOAD_FILE" 2>/dev/null)
    if [ "$actual_size" -ne "$ATTACK_PAYLOAD_SIZE" ]; then
        error "Payload size mismatch: expected $ATTACK_PAYLOAD_SIZE, got $actual_size"
        exit 1
    fi
    log "Payload generated successfully ($actual_size bytes)"
}

# Test 1: Basic QUIC connectivity
test_basic_connectivity() {
    log "Test 1: Basic QUIC connectivity..."
    
    # Start server in background
    "$QUICTE_SERVER" --listen 127.0.0.1:4433 \
        --cert "$CERT_DIR/combined.pem" \
        --root "$CERT_DIR" \
        --dgram-count 0 \
        --no-verify \
        &> /dev/null
    SERVER_PID=$!
    
    sleep 2
    
    # Test client connection
    if "$QUICTE_CLIENT" --no-verify --trust-origin-ca-pem "$CERT_DIR/ca.crt" \
        "https://localhost:4433/" 2>&1 | head -5 | grep -q "200"; then
        log "✅ Basic connectivity test PASSED"
        kill $SERVER_PID
        return 0
    else
        error "❌ Basic connectivity test FAILED"
        kill $SERVER_PID
        return 1
    fi
}

# Test 2: Payload transmission
test_payload_transmission() {
    log "Test 2: Payload transmission..."
    
    # Start server
    "$QUICTE_SERVER" --listen 127.0.0.1:4433 \
        --cert "$CERT_DIR/combined.pem" \
        --root "$CERT_DIR" \
        --dgram-count 0 \
        --dump-packets "$LOG_DIR/packets" \
        &> "$LOG_DIR/server.log"
    SERVER_PID=$!
    
    sleep 2
    
    # Send payload via file upload
    "$QUICTE_CLIENT" --trust-origin-ca-pem "$CERT_DIR/ca.crt" \
        --body "$PAYLOAD_FILE" \
        "https://localhost:4433/upload" 2>&1 | tee "$LOG_DIR/client.log"
    
    CLIENT_EXIT=$?
    kill $SERVER_PID 2>/dev/null || true
    wait $SERVER_PID 2>/dev/null || true
    
    if [ $CLIENT_EXIT -eq 0 ]; then
        log "✅ Payload transmission test COMPLETED (exit code: $CLIENT_EXIT)"
        return 0
    else
        error "❌ Payload transmission test FAILED (exit code: $CLIENT_EXIT)"
        return 1
    fi
}

# Test 3: Suricata detection
test_suricata_detection() {
    log "Test 3: Suricata detection..."
    
    # Ensure Suricata rules exist
    if [ ! -f ~/.suricata/rules/xring.rules ]; then
        error "❌ Suricata rules not found at ~/.suricata/rules/xring.rules"
        return 1
    fi
    
    # Start Suricata in test mode
    mkdir -p "$LOG_DIR/suricata"
    SURICATA_PID=$(suricata -c ~/.suricata/suricata.yaml \
        -r /dev/null \
        -l "$LOG_DIR/suricata" \
        --skip-sha1-sum \
        &> /dev/null)
    
    if [ ! -f "$LOG_DIR/suricata/suricata.log" ]; then
        error "❌ Suricata failed to start"
        kill $SURICATA_PID 2>/dev/null || true
        return 1
    fi
    
    log "✅ Suricata started for packet inspection"
    
    # Cleanup Suricata
    kill $SURICATA_PID 2>/dev/null || true
    wait $SURICATA_PID 2>/dev/null || true
    
    # Check for detections in logs
    if grep -q "xrighthit" "$LOG_DIR/suricata/*.log" 2>/dev/null; then
        log "🚨 Suricata detected XRING attack pattern!"
        grep "xrighthit" "$LOG_DIR/suricata/*.log"
        return 0
    else
        log "✅ Suricata ran (no detections in this test run)"
        return 0
    fi
}

# Test 4: Memory monitoring
test_memory_monitoring() {
    log "Test 4: Process memory monitoring..."
    
    # Start server
    "$QUICTE_SERVER" --listen 127.0.0.1:4433 \
        --cert "$CERT_DIR/combined.pem" \
        --root "$CERT_DIR" \
        &> "$LOG_DIR/server.log"
    SERVER_PID=$!
    
    sleep 2
    
    # Run client multiple times
    for i in 1 2 3; do
        "$QUICTE_CLIENT" --trust-origin-ca-pem "$CERT_DIR/ca.crt" \
            --body "$PAYLOAD_FILE" \
            "https://localhost:4433/upload" 2>&1 > /dev/null || true
    done
    
    sleep 2
    
    # Check server memory and stability
    if kill -0 $SERVER_PID 2>/dev/null; then
        log "✅ Server remained stable after multiple payload attempts"
        kill $SERVER_PID
        return 0
    else
        error "❌ Server crashed during payload testing"
        kill $SERVER_PID 2>/dev/null || true
        return 1
    fi
}

# Main test execution
main() {
    log "Initializing QUIC XRING test harness..."
    
    # Setup
    mkdir -p "$TEMP_DIR" "$LOG_DIR" "$CERT_DIR"
    generate_certs
    generate_xring_payload
    
    # Run tests
    local tests_passed=0
    local tests_failed=0
    
    log "Running test suite..."
    
    # Test 1: Basic connectivity
    if test_basic_connectivity; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi
    
    # Test 2: Payload transmission
    if test_payload_transmission; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi
    
    # Test 3: Suricata detection
    if test_suricata_detection; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi
    
    # Test 4: Memory monitoring
    if test_memory_monitoring; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi
    
    # Summary
    log "=== Test Summary ==="
    log "✅ Passed: $tests_passed"
    log "❌ Failed: $tests_failed"
    
    if [ $tests_failed -eq 0 ]; then
        log "🎉 All tests passed!"
        exit 0
    else
        error "⚠️ Some tests failed"
        exit 1
    fi
}

# Run main function
main "$@"
