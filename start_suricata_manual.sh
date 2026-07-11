#!/bin/bash
# Manual Suricata Start Script for XRING Security
# Run this script in your terminal with sudo privileges

echo "=== XRING Suricata Manual Start ==="
echo ""

# Configuration
RULES_PATH="/Users/mitchparker/.suricata/rules/xring.rules"
CONF_PATH="/Users/mitchparker/.suricata/suricata.yaml"
LOG_PATH="/Users/mitchparker/.suricata/log/eve.json"

echo "Checking dependencies..."

# Check if Suricata is installed
if ! command -v suricata &> /dev/null; then
    echo "❌ Suricata not found. Install with: brew install suricata"
    exit 1
fi

echo "✅ Suricata found"

# Check if rules file exists
if [ ! -f "$RULES_PATH" ]; then
    echo "❌ Rules file not found: $RULES_PATH"
    exit 1
fi

echo "✅ Rules file found"

# Check if config exists
if [ ! -f "$CONF_PATH" ]; then
    echo "❌ Config file not found: $CONF_PATH"
    exit 1
fi

echo "✅ Config file found"

# Create log directory if it doesn't exist
if [ ! -d "/Users/mitchparker/.suricata/log" ]; then
    mkdir -p /Users/mitchparker/.suricata/log
    chmod 777 /Users/mitchparker/.suricata/log
fi

echo "✅ Log directory ready"

# Check if Suricata is already running
if ps aux | grep -q "suricata.*en0"; then
    echo "⚠️ Suricata is already running!"
    read -p "Do you want to kill the existing process and restart? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pkill -f "suricata.*en0"
        sleep 2
    else
        echo "Aborted."
        exit 0
    fi
fi

# Start Suricata
echo ""
echo "🚀 Starting Suricata in workers mode..."
echo "Interface: en0"
echo "Rules: $RULES_PATH"
echo "Log dir: /Users/mitchparker/.suricata/log"
echo ""

# Run in foreground (detached from terminal)
cd /Users/mitchparker/.suricata
sudo suricata -c suricata.yaml -i en0 -D 2>&1

echo ""
echo "⏳ Waiting for Suricata to initialize..."
sleep 3

# Check if it started
if ps aux | grep -q "suricata.*en0"; then
    echo "✅ Suricata started successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Wait for traffic generation"
    echo "2. Check logs: tail -f /Users/mitchparker/.suricata/log/eve.json"
    echo "3. Open dashboard: http://127.0.0.1:5001"
    echo ""
    echo "To stop Suricata later:"
    echo "  sudo pkill -f 'suricata.*en0'"
    exit 0
else
    echo "❌ Suricata failed to start"
    echo ""
    echo "Please check the following:"
    echo "1. Permissions on /Users/mitchparker/.suricata/log (should be 777)"
    echo "2. Rules file syntax (run: sudo suricata -c suricata.yaml -T)"
    echo "3. Interface name (en0 is correct for Mac)"
    exit 1
fi
