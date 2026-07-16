#!/bin/bash

# BGP Hijack Monitoring Cron Job
# Automated daily BGP security monitoring

MONITORING_SCRIPT="/Users/mitchparker/.openclaw/workspace/research/bgp_monitoring/bgp_hijack_monitor.py"
LOG_DIR="/Users/mitchparker/.openclaw/workspace/research/bgp_monitoring/logs"
REPORT_DIR="/Users/mitchparker/.openclaw/workspace/research/bgp_monitoring/reports"
CONFIG_FILE="/Users/mitchparker/.openclaw/workspace/research/bgp_monitoring/config.json"

# Create directories if they don't exist
mkdir -p "$LOG_DIR"
mkdir -p "$REPORT_DIR"

# Generate timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/bgp_monitor_${TIMESTAMP}.log"

# Log start
echo "[$(date)] Starting BGP monitoring cycle" | tee "$LOG_FILE"

# Check configuration
if [ ! -f "$CONFIG_FILE" ]; then
    echo "[$(date)] ERROR: Configuration file not found: $CONFIG_FILE" | tee -a "$LOG_FILE"
    exit 1
fi

# Run monitoring script
echo "[$(date)] Executing BGP monitoring script..." | tee -a "$LOG_FILE"
python3 "$MONITORING_SCRIPT" 2>&1 | tee -a "$LOG_FILE"

# Check exit code
EXIT_CODE=${PIPESTATUS[0]}

if [ $EXIT_CODE -eq 0 ]; then
    echo "[$(date)] BGP monitoring completed successfully" | tee -a "$LOG_FILE"
else
    echo "[$(date)] ERROR: BGP monitoring failed with exit code $EXIT_CODE" | tee -a "$LOG_FILE"
    exit $EXIT_CODE
fi

# Generate alert if critical hijacks detected
CRITICAL_HIJACKS=$(grep -c "CRITICAL" "$LOG_FILE" 2>/dev/null || echo "0")
if [ "$CRITICAL_HIJACKS" -gt 0 ]; then
    echo "[$(date)] WARNING: $CRITICAL_HIJACKS critical hijack(s) detected!" | tee -a "$LOG_FILE"
    # Add alerting logic here (email, Slack, etc.)
fi

echo "[$(date)] BGP monitoring cycle completed" | tee -a "$LOG_FILE"
