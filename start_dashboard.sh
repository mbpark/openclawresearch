#!/bin/bash
# Start XRING Security Dashboard

echo "Starting XRING Security Dashboard..."

# Kill any existing dashboard processes
pkill -f suricata_dashboard.py 2>/dev/null || true
sleep 2

# Start the dashboard
cd /Users/mitchparker/.openclaw/workspace/research
python3 suricata_dashboard.py --port 5001 --debug
