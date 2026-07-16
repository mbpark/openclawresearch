# Production Deployment Checklist
## File Upload RCE Defense Systems
**Date:** July 16, 2026
**Target CVEs:** CVE-2026-48939, CVE-2026-56291, CVE-2026-48908

---

## Phase 1: SIEM Detection Rules Deployment ✅

### Pre-Deployment Checks
- [ ] Backup current SIEM configuration
- [ ] Verify SIEM connectivity and log ingestion
- [ ] Confirm detection rule syntax compatibility

### Deploy to Elastic SIEM
- [ ] Copy `siem_detection_rules_file_upload_rce.json` to Elastic cluster
- [ ] Import detection rules via Elastic Management API
- [ ] Enable real-time alerts to SIEM dashboard
- [ ] Test rule matching with sample malicious traffic

### Deploy to Snort IDS
```bash
# Backup current rules
cp /etc/snort/rules/local.rules /etc/snort/rules/local.rules.bak

# Add new rules
cat research/siem_detection_rules_file_upload_rce.json | grep -A20 '"snort"' >> /etc/snort/rules/local.rules

# Restart Snort
sudo systemctl restart snort

# Verify rules loaded
snort -T -c /etc/snort/snort.conf
```

### Deploy to Suricata IDS
```bash
# Backup current rules
cp /etc/suricata/rules/local.rules /etc/suricata/rules/local.rules.bak

# Add new rules
cat research/siem_detection_rules_file_upload_rce.json | grep -A20 '"suricata"' >> /etc/suricata/rules/local.rules

# Restart Suricata
sudo systemctl restart suricata

# Verify rules loaded
suricata -T -c /etc/suricata/suricata.yaml
```

### Post-Deployment Validation
- [ ] Send test malicious upload request
- [ ] Verify SIEM alerts trigger within 60 seconds
- [ ] Confirm detection IDs match expected values (1000001-1000005)
- [ ] Document successful deployment in incident log

---

## Phase 2: WAF Rules Deployment ✅

### Pre-Deployment Checks
- [ ] Backup current WAF configuration
- [ ] Identify WAF technology (ModSecurity, Cloudflare, AWS WAF, etc.)
- [ ] Schedule maintenance window for WAF changes

### Deploy to ModSecurity WAF
```bash
# Backup current configuration
cp /etc/modsecurity/modsecurity.conf /etc/modsecurity/modsecurity.conf.bak

# Add WAF rules
cat > /etc/modsecurity/rules/local-rules.conf << 'EOF'
# WAF Rules for File Upload RCE Prevention
# CVE-2026-48939, CVE-2026-56291, CVE-2026-48908

SecRule REQUEST_URI "(?i)(icagenda|balbooa|joomshaper).*\.php" \
    "id:900001,phase:2,deny,status:403,msg:'Blocked PHP upload to vulnerable Joomla extension'"

SecRule REQUEST_URI "(?i)/upload.*\.php" \
    "id:900002,phase:2,deny,status:403,msg:'Blocked PHP upload attempt'"

SecRule REQUEST_METHOD "POST" "@streq POST" \
    "id:900003,phase:2,chain,deny,status:403,msg:'Invalid content type for file upload'" \
    "t:lowercase" \
    SecRule REQUEST_HEADERS:Content-Type "(?i)^(text/|application/x-php|application/x-httpd-php)" "@rx .*" \
    "t:none"
EOF

# Restart web server and ModSecurity
sudo systemctl restart apache2   # or nginx, depending on setup
```

### Deploy to Cloudflare WAF (if applicable)
```bash
# Use Cloudflare API or dashboard
# Create custom rules:
# 1. Block requests to icagenda, balbooa, joomshaper with .php extension
# 2. Block POST requests with PHP content-type to upload paths
# 3. Set rate limiting for upload endpoints
```

### Post-Deployment Validation
- [ ] Test blocked requests return 403 status code
- [ ] Verify legitimate uploads still work
- [ ] Check WAF logs for rule matches
- [ ] Document deployment in change management system

---

## Phase 3: Image Protection Service Deployment ✅

### Production Deployment
- [ ] Deploy `image_protection_service.py` to production server
- [ ] Set up systemd service for automatic startup
- [ ] Configure log rotation and alerting
- [ ] Set up health check endpoint

### Create Systemd Service
```bash
sudo tee /etc/systemd/system/image-protection.service > /dev/null << 'EOF'
[Unit]
Description=Image Protection Service - File Upload Monitoring
After=network.target

[Service]
Type=simple
User=mitch
WorkingDirectory=/Users/mitchparker/.openclaw/workspace/research/ghostcommit-image-system
ExecStart=/usr/bin/python3 image_protection_service.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable image-protection
sudo systemctl start image-protection
```

### Verify Service Status
- [ ] Check service is running: `systemctl status image-protection`
- [ ] Verify log output shows successful initialization
- [ ] Confirm CVE patterns loaded correctly
- [ ] Test with controlled malicious upload

---

## Phase 4: Monitoring & Alerting Setup ✅

### SIEM Alert Configuration
- [ ] Set up PagerDuty/Opsgenie integration for critical alerts
- [ ] Configure email notifications for security team
- [ ] Create dashboards for real-time threat visualization
- [ ] Set up automated response playbooks

### Application Monitoring
- [ ] Add health check endpoints to Image Protection Service
- [ ] Set up uptime monitoring (e.g., UptimeRobot, Pingdom)
- [ ] Configure log aggregation (ELK stack, Splunk, etc.)
- [ ] Set up anomaly detection for upload patterns

### Network Monitoring
- [ ] Add Suricata/Snort to network monitoring stack
- [ ] Configure alerting for detection rule matches
- [ ] Set up IP reputation blocking for repeated attempts
- [ ] Implement automated IP blocking for confirmed attackers

---

## Phase 5: Verification & Testing ✅

### End-to-End Testing Plan
- [ ] **Test 1:** Malicious PHP file upload to iCagenda
  - Expected: Detection in SIEM, WAF block, Image Protection alert
- [ ] **Test 2:** Malicious PHP file upload to Balbooa Forms
  - Expected: Detection in SIEM, WAF block, Image Protection alert
- [ ] **Test 3:** Malicious PHP file upload to JoomShaper
  - Expected: Detection in SIEM, WAF block, Image Protection alert
- [ ] **Test 4:** Legitimate file upload (PNG, JPG, PDF)
  - Expected: No alerts, upload succeeds
- [ ] **Test 5:** Test uploaded files are properly scanned and blocked

### Performance Testing
- [ ] Verify detection latency < 2 seconds
- [ ] Confirm system can handle 100+ uploads per minute
- [ ] Check resource usage (CPU, memory) remains under 50%
- [ ] Validate log volume doesn't overwhelm SIEM

### Documentation
- [ ] Update incident response procedures
- [ ] Document detection rules and WAF configurations
- [ ] Create runbooks for common alert scenarios
- [ ] Schedule regular security audits

---

## Deployment Verification Script

```bash
#!/bin/bash
# Production Deployment Verification Script
# Runs all verification checks for File Upload RCE defenses

echo "🔍 Running Production Deployment Verification..."
echo "=============================================="

# Check SIEM rules
echo -e "\n📋 Checking SIEM Detection Rules..."
if [ -f "/etc/snort/rules/local.rules" ]; then
    grep -q "CVE-2026-48939" /etc/snort/rules/local.rules && echo "✅ Snort rules deployed"
    grep -q "CVE-2026-56291" /etc/snort/rules/local.rules && echo "✅ Snort rules deployed"
    grep -q "CVE-2026-48908" /etc/snort/rules/local.rules && echo "✅ Snort rules deployed"
fi

# Check WAF rules
echo -e "\n🛡️  Checking WAF Rules..."
if [ -f "/etc/modsecurity/rules/local-rules.conf" ]; then
    grep -q "900001" /etc/modsecurity/rules/local-rules.conf && echo "✅ WAF rule 900001 active"
    grep -q "900002" /etc/modsecurity/rules/local-rules.conf && echo "✅ WAF rule 900002 active"
    grep -q "900003" /etc/modsecurity/rules/local-rules.conf && echo "✅ WAF rule 900003 active"
fi

# Check Image Protection Service
echo -e "\n🖼️  Checking Image Protection Service..."
if systemctl is-active --quiet image-protection; then
    echo "✅ Image Protection Service running"
else
    echo "❌ Image Protection Service not running"
    exit 1
fi

# Test all systems
echo -e "\n🧪 Running End-to-End Tests..."
# Add test commands here

echo -e "\n✅ Production Deployment Verification Complete!"
```

---

## Emergency Procedures

### Rollback Plan
If deployment causes issues:
1. **WAF Rollback:**
   ```bash
   cp /etc/modsecurity/modsecurity.conf.bak /etc/modsecurity/modsecurity.conf
   sudo systemctl restart apache2
   ```
2. **IDS Rollback:**
   ```bash
   cp /etc/snort/rules/local.rules.bak /etc/snort/rules/local.rules
   sudo systemctl restart snort
   ```
3. **Service Rollback:**
   ```bash
   sudo systemctl stop image-protection
   ```

### Escalation Contacts
- **Security Team:** security@company.com
- **Operations:** ops@company.com
- **On-Call:** pagerduty.com/initiate?priority=P1

---

## Sign-off

- [ ] **Deployment Team Lead:** ___________________ Date: _________
- [ ] **Security Team:** ___________________ Date: _________
- [ ] **Operations Team:** ___________________ Date: _________

---

**Next Review:** July 23, 2026 (7-day post-deployment review)
