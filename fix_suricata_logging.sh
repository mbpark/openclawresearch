#!/bin/bash
# Fix Suricata Logging Permissions and Verify Setup

echo "=== Suricata Logging Fix ==="
echo ""

# Configuration
SURICATA_DIR="/Users/mitchparker/.suricata"
LOG_DIR="$SURICATA_DIR/log"

echo "📁 Suricata directory: $SURICATA_DIR"
echo "📁 Log directory: $LOG_DIR"
echo ""

# Step 1: Check directory exists
if [ ! -d "$SURICATA_DIR" ]; then
    echo "❌ Suricata directory not found: $SURICATA_DIR"
    exit 1
fi
echo "✅ Suricata directory exists"

# Step 2: Create log directory if missing
if [ ! -d "$LOG_DIR" ]; then
    echo "📝 Creating log directory..."
    mkdir -p "$LOG_DIR"
    chmod -R 777 "$LOG_DIR"
    echo "✅ Log directory created"
else
    echo "✅ Log directory exists"
fi

# Step 3: Fix permissions on log directory
echo ""
echo "🔒 Fixing permissions..."
if [ ! -w "$LOG_DIR" ]; then
    echo "⚠️ Log directory is not writable. Fixing..."
    chmod 777 "$LOG_DIR"
    echo "✅ Permissions fixed"
else
    echo "✅ Log directory is writable"
fi

# Step 4: Fix permissions on config and rules
echo ""
echo "🔒 Fixing permissions on config and rules..."
if [ -f "$SURICATA_DIR/suricata.yaml" ]; then
    chmod 644 "$SURICATA_DIR/suricata.yaml"
    echo "✅ suricata.yaml permissions fixed"
fi

if [ -d "$SURICATA_DIR/rules" ]; then
    chmod -R 755 "$SURICATA_DIR/rules"
    echo "✅ Rules directory permissions fixed"
fi

# Step 5: Verify Eve JSON format
echo ""
echo "📋 Verifying EVE JSON configuration..."
if grep -q "json-logging:" "$SURICATA_DIR/suricata.yaml"; then
    echo "✅ JSON logging enabled in config"
else
    echo "⚠️ JSON logging not found in config"
fi

if grep -q "default-log-dir:" "$SURICATA_DIR/suricata.yaml"; then
    LOG_DIR_IN_CONF=$(grep "default-log-dir:" "$SURICATA_DIR/suricata.yaml" | awk '{print $2}')
    echo "✅ Log directory configured: $LOG_DIR_IN_CONF"
    
    if [ "$LOG_DIR_IN_CONF" != "$LOG_DIR" ]; then
        echo "⚠️ Config directory differs from actual: $LOG_DIR_IN_CONF vs $LOG_DIR"
    fi
fi

# Step 6: Test with a dummy rule
echo ""
echo "🔍 Testing rule loading..."
if [ -f "$SURICATA_DIR/rules/xring.rules" ]; then
    echo "✅ xring.rules found"
    
    # Count rules
    rule_count=$(grep -c "^alert" "$SURICATA_DIR/rules/xring.rules")
    echo "📄 Found $rule_count alert rules"
fi

# Step 7: Check Suricata process
echo ""
echo "🔄 Checking Suricata process..."
if ps aux | grep -q "suricata.*en0"; then
    echo "✅ Suricata is currently running"
    echo ""
    echo "Process details:"
    ps aux | grep "suricata.*en0" | grep -v grep
else
    echo "⚠️ Suricata is NOT running"
fi

# Step 8: Provide next steps
echo ""
echo "=== Next Steps ==="
echo ""
echo "Option 1: Start Suricata manually"
echo "  ./start_suricata_manual.sh (with sudo password)"
echo ""
echo "Option 2: Start in foreground"
echo "  sudo suricata -c $SURICATA_DIR/suricata.yaml -i en0"
echo ""
echo "Option 3: Test with offline PCAP (no sudo needed)"
echo "  suricata -c $SURICATA_DIR/suricata.yaml -r /path/to/packet.pcap"
echo ""
echo "After starting Suricata, check for EVE logs:"
echo "  tail -f $LOG_DIR/eve.json"
echo ""
echo "To verify detection is working, generate traffic and watch for alerts:"
echo "  ./manual_traffic_test.sh"
echo ""
echo "=== Fix Complete ==="
