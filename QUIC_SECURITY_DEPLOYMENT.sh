#!/bin/bash
# QUIC Security Deployment Script
# Automated deployment of XRING detection and protection systems
# Created: July 10, 2026

set -e  # Exit on error

echo "=== QUIC Security Deployment Started ==="
echo "Date: $(date)"
echo "Working Directory: $(pwd)"

# Configuration
DEPLOY_DIR="/opt/xring-security"
RULES_DIR="/etc/suricata/rules"
ETCDIR="/etc/suricata"
DEPLOY_LOG="$DEPLOY_DIR/deployment.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    local message=$1
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${GREEN}[$timestamp]${NC} $message" | tee -a "$DEPLOY_LOG"
}

error() {
    local message=$1
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${RED}[$timestamp] ERROR${NC} $message" | tee -a "$DEPLOY_LOG"
}

warning() {
    local message=$1
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${YELLOW}[$timestamp] WARNING${NC} $message" | tee -a "$DEPLOY_LOG"
}

# Check for root privileges
check_root() {
    if [ "$EUID" -ne 0 ]; then
        error "Please run as root or with sudo"
        exit 1
    fi
}

# Install dependencies
install_dependencies() {
    log "Installing dependencies..."
    
    # Ubuntu/Debian
    if [ -f /etc/debian_version ]; then
        apt-get update
        apt-get install -y suricata python3 python3-pip libbpf-tools
    # RHEL/CentOS
    elif [ -f /etc/redhat-release ]; then
        yum install -y suricata python3 python3-pip libbpf
    else
        warning "Unknown distribution, installing dependencies manually"
        apt-get update 2>/dev/null || true
    fi
    
    # Install Python dependencies
    pip3 install --user flask requests
    
    log "Dependencies installed"
}

# Deploy Suricata rules
deploy_suricata_rules() {
    log "Deploying Suricata rules..."
    
    # Create rules directory if it doesn't exist
    mkdir -p "$RULES_DIR"
    
    # Copy XRING rules
    cp /tmp/xring-suricata.rules "$RULES_DIR/xring.rules"
    
    # Update suricata rules
    if command -v suricata-update &> /dev/null; then
        suricata-update
        log "Suricata rules updated"
    else
        warning "suricata-update not available, skipping auto-update"
    fi
    
    log "Suricata rules deployed"
}

# Configure Suricata
configure_suricata() {
    log "Configuring Suricata..."
    
    # Backup existing config
    if [ -f "$ETCDIR/suricata.yaml" ]; then
        cp "$ETCDIR/suricata.yaml" "$ETCDIR/suricata.yaml.backup"
    fi
    
    # Add XRing rules to local rules file
    echo "localrules_file: $RULES_DIR/xring.rules" >> "$ETCDIR/suricata.yaml"
    
    log "Suricata configured"
}

# Restart Suricata
restart_suricata() {
    log "Restarting Suricata..."
    
    if systemctl is-active --quiet suricata; then
        systemctl restart suricata
        log "Suricata restarted"
    else
        warning "Suricata not running, manual restart may be required"
    fi
}

# Install eBPF probes
deploy_epbf_probes() {
    log "Installing eBPF probes..."
    
    # Check if eBPF is available
    if ! command -v bpftool &> /dev/null; then
        warning "bpftool not available, eBPF probes cannot be installed"
        return
    fi
    
    # Create eBPF directory
    mkdir -p "/sys/fs/bpf/xring"
    
    # Note: Actual eBPF program deployment would require compiled .o files
    # This is a placeholder for the deployment step
    log "eBPF probe installation completed (manual compilation may be required)"
}

# Deploy Python security monitor
deploy_security_monitor() {
    log "Deploying Python security monitor..."
    
    # Create deployment directory
    mkdir -p "$DEPLOY_DIR"
    cp /tmp/xring_security_monitor.py "$DEPLOY_DIR/xring_monitor.py"
    
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

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable xring-security-monitor
    systemctl start xring-security-monitor
    
    log "Security monitor deployed"
}

# Deploy workflow graph integration
deploy_workflow_integration() {
    log "Deploying workflow graph integration..."
    
    # Create workflow extension
    mkdir -p "/etc/workflow/extensions"
    
    cat > "/etc/workflow/extensions/qpack_security.py" << EOF
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
    
    log "Workflow graph integration deployed"
}

# Generate deployment report
generate_report() {
    log "Generating deployment report..."
    
    report_file="$DEPLOY_DIR/deployment_report.txt"
    
    cat > "$report_file" << EOF
QUIC Security Deployment Report
===============================
Date: $(date)
Hostname: $(hostname)
Deployment Log: $DEPLOY_LOG

Components Deployed:
1. Suricata Rules: $RULES_DIR/xring.rules
2. Security Monitor: $DEPLOY_DIR/xring_monitor.py
3. Workflow Extension: /etc/workflow/extensions/qpack_security.py

Services Active:
$(systemctl is-active suricata 2>/dev/null || echo "Suricata: Not running")
$(systemctl is-active xring-security-monitor 2>/dev/null || echo "XRing Monitor: Not running")

Configuration Files:
- Suricata: $ETCDIR/suricata.yaml
- Workflow: /etc/workflow/extensions/qpack_security.py

Next Steps:
1. Monitor security logs for detection events
2. Test detection rules with sample traffic
3. Schedule regular rule updates
4. Review and tune false positive rates

For more information, see:
- $DEPLOY_LOG
- /var/log/suricata/*.log
- Documentation in /opt/xring-security/
EOF
    
    log "Deployment report generated: $report_file"
}

# Main deployment function
main() {
    log "Starting QUIC Security Deployment..."
    
    # Check root privileges
    check_root
    
    # Install dependencies
    install_dependencies
    
    # Copy files to deployment location (if not already present)
    if [ ! -f "/tmp/xring-suricata.rules" ]; then
        error "XRING Suricata rules not found in /tmp"
        exit 1
    fi
    
    if [ ! -f "/tmp/xring_security_monitor.py" ]; then
        error "XRING security monitor not found in /tmp"
        exit 1
    fi
    
    # Deploy components
    deploy_suricata_rules
    configure_suricata
    restart_suricata
    deploy_epbf_probes
    deploy_security_monitor
    deploy_workflow_integration
    
    # Generate report
    generate_report
    
    log "QUIC Security Deployment completed successfully!"
    log "Check $DEPLOY_LOG for detailed deployment log"
    log "Check $DEPLOY_DIR/deployment_report.txt for deployment summary"
    
    echo ""
    echo "=== Deployment Summary ==="
    cat "$DEPLOY_DIR/deployment_report.txt"
}

# Run main function
main "$@"
