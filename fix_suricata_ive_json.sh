#!/bin/bash
# Fix EVE JSON logging configuration for Suricata 8.x

echo "=== Fixing EVE JSON Logging ==="
echo ""

# Configuration
CONF_PATH="/Users/mitchparker/.suricata/suricata.yaml"
BACKUP_PATH="/Users/mitchparker/.suricata/suricata.yaml.backup"

# Backup original config
cp "$CONF_PATH" "$BACKUP_PATH"
echo "✅ Configuration backed up to $BACKUP_PATH"

# Create new configuration with proper EVE JSON settings
cat > "$CONF_PATH" << 'EOF'
%YAML 1.1
---

# XRING Security Suricata Configuration for macOS
# Fixed for EVE JSON logging
# Date: July 10, 2026

default-log-dir: /Users/mitchparker/.suricata/log

# Network settings
pcap-engine: pcap
pcap-buffer-size: 131072

# Run mode - use 'workers' for multi-threaded pcap live mode
runmode: workers

# Workers (adjust based on CPU)
workers: 4

# Rules file path (explicitly loaded)
rules:
  - /Users/mitchparker/.suricata/rules/xring.rules

# Classification and reference configuration
classification-file: /opt/homebrew/etc/suricata/classification.config
reference-config-file: /opt/homebrew/etc/suricata/reference.config

# Memory limit
memcap: 512mb

# EVE JSON Logging Configuration
eve-log:
  enabled: yes
  filetype: regular
  filename: eve.json
  config:
    logging:
      enabled: yes
      format: json

# Additional logging (for debugging)
# syslog:
#   enabled: yes
#   facility: local0

EOF

echo "✅ New configuration written with EVE JSON enabled"
echo ""
echo "Configuration contents:"
grep -A 5 "eve-log:" "$CONF_PATH"
echo ""
echo "=== Next Steps ==="
echo "1. Stop Suricata: sudo pkill -f 'suricata.*en0'"
echo "2. Remove old logs: rm -f /Users/mitchparker/.suricata/log/*"
echo "3. Start Suricata: sudo suricata -c ~/.suricata/suricata.yaml -i en0"
echo ""
echo "Then generate traffic and check logs."
