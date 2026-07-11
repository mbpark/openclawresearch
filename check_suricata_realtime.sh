#!/bin/bash
# Real-time EVE Log Checker
# Watches for alerts and processes them

echo "=== Real-time EVE Log Monitor ==="
echo "Monitoring: /Users/mitchparker/.suricata/log/eve.json"
echo "Ctrl+C to exit"
echo ""

# Check if file exists
if [ ! -f "/Users/mitchparker/.suricata/log/eve.json" ]; then
    echo "❌ EVE log not found. Creating empty file..."
    touch /Users/mitchparker/.suricata/log/eve.json
fi

# Function to check if Suricata is running
check_suricata() {
    if ps aux | grep -q "suricata.*en0"; then
        echo "✅ Suricata running"
    else
        echo "❌ Suricata not running"
        exit 1
    fi
}

# Initial check
check_suricata

# Tail the log file
echo "🔍 Following EVE log..."
echo ""

# Process log entries
while true; do
    tail -n 1 /Users/mitchparker/.suricata/log/eve.json
    
    # Check for XRING alerts
    xring_count=$(grep -c "xring" /Users/mitchparker/.suricata/log/eve.json 2>/dev/null || echo 0)
    echo "📊 Total XRING alerts: $xring_count"
    
    sleep 2
done
