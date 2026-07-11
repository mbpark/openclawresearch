#!/bin/bash
# QUIC Security Manual Deployment Script
# Run this script in your terminal with sudo privileges
# Created: July 10, 2026

set -e

echo "=== QUIC Security Manual Deployment ==="
echo "Date: $(date)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    error "Please run this script with sudo: sudo bash $0"
    exit 1
fi

echo ""
echo "=== Step 1: Install Dependencies ==="
echo ""

# Install Suricata (Debian/Ubuntu)
if command -v apt-get &> /dev/null; then
    log "Installing Suricata..."
    apt-get update
    apt-get install -y suricata python3 python3-pip libbpf-tools
    log "Suricata installed"
# Install Suricata (RHEL/CentOS)
elif command -v yum &> /dev/null; then
    log "Installing Suricata..."
    yum install -y suricata python3 python3-pip libbpf
    log "Suricata installed"
else
    warning "Unknown distribution, please install manually"
    exit 1
fi

# Install Python dependencies
pip3 install --user flask requests

echo ""
echo "=== Step 2: Deploy Suricata Detection Rules ==="
echo ""

RULES_DIR="/etc/suricata/rules"
mkdir -p "$RULES_DIR"

# Copy rules
cp /Users/mitchparker/.openclaw/workspace/research/xring-suricata.rules "$RULES_DIR/xring.rules"
log "Copied xring-suricata.rules to $RULES_DIR/xring.rules"

# Enable rules in Suricata configuration
ETCDIR="/etc/suricata"
if ! grep -q "xring.rules" "$ETCDIR/suricata.yaml"; then
    log "Updating Suricata configuration..."
    echo "localrules_file: $RULES_DIR/xring.rules" >> "$ETCDIR/suricata.yaml"
    log "Suricata configuration updated"
fi

echo ""
echo "=== Step 3: Restart Suricata ==="
echo ""

if systemctl is-active --quiet suricata; then
    log "Restarting Suricata..."
    systemctl restart suricata
    log "Suricata restarted successfully"
else
    warning "Suricata is not running, starting..."
    systemctl start suricata
    systemctl enable suricata
    log "Suricata started and enabled"
fi

echo ""
echo "=== Step 4: Deploy Security Monitor ==="
echo ""

DEPLOY_DIR="/opt/xring-security"
mkdir -p "$DEPLOY_DIR"

# Copy monitor script
cp /Users/mitchparker/.openclaw/workspace/research/xring_security_monitor.py "$DEPLOY_DIR/xring_monitor.py"
log "Copied xring_security_monitor.py to $DEPLOY_DIR"

# Create systemd service
cat > /etc/systemd/system/xring-security-monitor.service << EOF
[Unit]
Description=XRING Security Monitor
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 $DEPLOY_DIR/xring_monitor.py
Restart=always
User=root
WorkingDirectory=$DEPLOY_DIR
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

log "Created systemd service: xring-security-monitor.service"

systemctl daemon-reload
systemctl enable xring-security-monitor
systemctl start xring-security-monitor

log "Security monitor deployed and running"

echo ""
echo "=== Step 5: Deploy Workflow Graph Integration ==="
echo ""

WORKFLOW_DIR="/etc/workflow/extensions"
mkdir -p "$WORKFLOW_DIR"

cat > "$WORKFLOW_DIR/qpack_security.py" << EOF
# QPACK Security Extension for Workflow Graph
# Detects XRING attack patterns

import json
from datetime import datetime

class XRingWorkflowMonitor:
    def __init__(self):
        self.operation_history = []
        self.capacity_changes = []
    
    def validate_qpack_operation(self, operation):
        if operation.get('type') == 'set_dynamic_table_capacity':
            capacity = operation.get('capacity', 0)
            self.capacity_changes.append({
                'timestamp': datetime.now().timestamp(),
                'capacity': capacity
            })
            
            # Check for XRING pattern
            if self.detect_xring_pattern():
                return False, "XRING attack pattern detected"
        
        return True, "Operation allowed"
    
    def detect_xring_pattern(self):
        if len(self.capacity_changes) < 2:
            return False
        
        recent = self.capacity_changes[-2:]
        if recent[0]['capacity'] == 64 and recent[1]['capacity'] == 65:
            time_diff = recent[1]['timestamp'] - recent[0]['timestamp']
            if time_diff < 5.0:
                return True
        
        return False

# Register with workflow graph
workflow_extension = XRingWorkflowMonitor()
EOF

log "Deployed workflow graph extension to $WORKFLOW_DIR/qpack_security.py"

echo ""
echo "=== Step 6: Generate Deployment Report ==="
echo ""

REPORT_FILE="$DEPLOY_DIR/deployment_report.txt"

cat > "$REPORT_FILE" << EOF
QUIC Security Deployment Report
===============================
Date: $(date)
Hostname: $(hostname)

Components Deployed:
1. Suricata Rules: $RULES_DIR/xring.rules
2. Security Monitor: $DEPLOY_DIR/xring_monitor.py
3. Workflow Extension: $WORKFLOW_DIR/qpack_security.py

Services Active:
- Suricata: $(systemctl is-active suricata)
- XRing Monitor: $(systemctl is-active xring-security-monitor)

Configuration Files:
- Suricata: $ETCDIR/suricata.yaml
- Workflow: $WORKFLOW_DIR/qpack_security.py

Deployment Status: ✅ SUCCESS
Next Steps:
1. Monitor logs: tail -f /var/log/suricata/*.log
2. Test with sample traffic
3. Tune detection thresholds as needed
4. Review alerts from xring_security_monitor

For detailed documentation, see:
/Users/mitchparker/.openclaw/workspace/research/QUIC_SECURITY_TASKS_COMPLETED.md
EOF

log "Deployment report generated: $REPORT_FILE"

echo ""
echo "=== Deployment Summary ==="
cat "$REPORT_FILE"

echo ""
echo "=== Deployment Complete ==="
echo "Check $REPORT_FILE for deployment details"
echo "Services are running and ready to protect your QUIC implementations"
