# PolinRider Incident Response Playbook

## Overview

This playbook provides step-by-step procedures for detecting, responding to, and recovering from PolinRider supply chain attacks.

### Quick Reference

- **Detection Time Target (MTTD):** < 1 hour
- **Response Time Target (MTTR):** < 4 hours
- **Recovery Time Target (RTO):** < 24 hours
- **Contact:** security@yourorganization.com

---

## Phase 1: Detection

### 1.1 Alert Monitoring

**Automated Detection:**
- Real-time network monitoring for suspicious outbound connections
- Package integrity monitoring for unexpected file changes
- Maintainer account change alerts
- Dependency audit failures

**Manual Detection:**
- Daily security scans (`scripts/suspicious_package_detector.sh`)
- Weekly maintainer audits (`scripts/maintainer_audit.py`)
- Monthly supply chain reviews

### 1.2 Initial Assessment

```bash
# Quick diagnostic checklist
./polinrider_monitor.py --status
./suspicious_package_detector.sh --quick-check
grep -r "PolinRider\|malicious" polinrider_alerts.log
```

**Indicators of Compromise (IoCs):**
- Unexpected network connections to ports: 4444, 5555, 6666, 31337
- New or modified package.json scripts
- Maintenance account email changes
- Unusual package sizes or recent updates

---

## Phase 2: Analysis

### 2.1 Threat Classification

| Severity | Criteria | Response Time |
|----------|----------|---------------|
| **CRITICAL** | Active exploitation, data exfiltration | Immediate |
| **HIGH** | Confirmed malicious package, network activity | < 1 hour |
| **MEDIUM** | Suspicious patterns, potential compromise | < 4 hours |
| **LOW** | Anomalous behavior, monitoring only | < 24 hours |

### 2.2 Mitre ATT&CK Mapping

```yaml
T1195: Supply Chain Compromise
  - T1195.001: Compromise Software Supply Chain
    Technique: Infected dependencies via npm/Packagist/Go packages

T1055: Process Injection
  - T1055.012: Process Injection via Package Scripts
    Technique: Malicious npm scripts execute system commands

T1071: Application Layer Protocol
  - T1071.001: Web Protocols
    Technique: HTTPS connections to command and control servers
```

### 2.3 Evidence Collection

```bash
# Network traffic capture
tcpdump -i any -w polinrider_capture.pcap port 4444 or port 5555 or port 6666

# System process dump
ps aux | grep -E "npm|node|python|go" > process_list.txt

# Package integrity check
find . -name "package.json" -exec md5sum {} \; > package_hashes.txt

# Timeline analysis
last -f /var/log/wtmp > login_history.txt
```

---

## Phase 3: Containment

### 3.1 Immediate Actions (0-15 minutes)

```bash
# 1. Isolate affected systems
systemctl stop polinrider-monitor
iptables -A INPUT -p tcp --dport 4444 -j DROP
iptables -A OUTPUT -p tcp --dport 5555 -j DROP

# 2. Block malicious network destinations
echo "BLOCKING malicious IPs and domains..."
# Add to blocklist based on detected IoCs

# 3. Preserve evidence
tar -czf polinrider_evidence_$(date +%s).tar.gz /var/log /etc /root
```

### 3.2 Network Containment

```yaml
firewall_rules:
  - action: BLOCK
    direction: OUTBOUND
    ports: [4444, 5555, 6666, 31337, 12345, 54321]
    protocol: TCP

  - action: BLOCK
    direction: BOTH
    destinations: 
      - malicious-c2-server.example.com
      - evil-domain.net
    protocol: ALL

  - action: LOG
    direction: OUTBOUND
    log_level: WARNING
    include_all: true
```

### 3.3 System Isolation

- **Disconnect affected systems** from network
- **Preserve memory** for forensic analysis
- **Maintain evidence chain of custody**
- **Document all actions** with timestamps

---

## Phase 4: Eradication

### 4.1 Malware Removal

```bash
# Remove malicious packages
npm uninstall --force malicious-package
yarn remove --force suspicious-module
go mod edit -dropreplace malicious-module

# Clean compromised scripts
find . -name "package.json" -exec grep -l "eval\|exec\|system" {} \; -exec sed -i '/eval\|exec\|system/d' {} \;

# Reset compromised credentials
reset_credentials --affected-systems
rotate_api_keys --all-services
```

### 4.2 System Hardening

```bash
# Update all packages
npm audit fix --force
pip install --upgrade --all-packages
go get -u ./...

# Enable strict package verification
npm config set audit-level high
npm config set strict-ssl true

# Deploy runtime protection
systemctl enable polinrider-monitor
systemctl start polinrider-monitor
```

---

## Phase 5: Recovery

### 5.1 System Restoration

```yaml
recovery_steps:
  - name: "Database restoration"
    procedure: Restore from clean backup (pre-incident)
    verification: "Check database integrity checksums"

  - name: "Application deployment"
    procedure: Deploy clean application version
    verification: "Run automated test suite"

  - name: "Network connectivity"
    procedure: Re-enable network access gradually
    verification: "Monitor for suspicious activity"

  - name: "User access"
    procedure: Reset all user credentials
    verification: "Test authentication systems"
```

### 5.2 Validation Testing

```bash
# Security scan validation
./suspicious_package_detector.sh --full-scan > validation_scan.json

# Network monitoring test
./polinrider_monitor.py --test-mode

# Penetration testing
# Schedule third-party security audit within 48 hours
```

---

## Phase 6: Lessons Learned

### 6.1 Post-Incident Review

**Meeting Agenda (within 72 hours):**
- Timeline of incident
- Effectiveness of response
- Gaps in detection and response
- Improvements needed

**Questions to Answer:**
- Could this have been detected earlier?
- Were response procedures followed correctly?
- What tools or processes need improvement?
- What additional training is needed?

### 6.2 Documentation

**Incident Report Template:**
```markdown
# Incident Report: [Incident ID]

## Executive Summary
- Date/Time: [Incident start]
- Duration: [Total time]
- Impact: [Systems affected, data impact]
- Root Cause: [Initial compromise vector]

## Timeline
- [Timestamp] - Initial detection
- [Timestamp] - Containment actions
- [Timestamp] - Eradication complete
- [Timestamp] - Recovery verified

## Findings
- **What happened:** [Detailed description]
- **How it happened:** [Attack vector]
- **What was affected:** [Systems, data, users]

## Response Effectiveness
- **Detection:** [Time to detect, accuracy]
- **Containment:** [Actions taken, effectiveness]
- **Recovery:** [Time to restore, success rate]

## Recommendations
1. [Specific improvement]
2. [Process change]
3. [Technology investment]
4. [Training requirement]

## Next Steps
- [Action item] - [Owner] - [Deadline]
- [Action item] - [Owner] - [Deadline]
```

### 6.3 Continuous Improvement

```yaml
improvement_plan:
  quarterly:
    - Update detection rules based on new IoCs
    - Conduct table-top exercises
    - Review and update contact lists

  monthly:
    - Run PolinRider detection drills
    - Verify backup integrity
    - Review alert thresholds

  weekly:
    - Run full security scans
    - Update threat intelligence feeds
    - Review monitoring effectiveness
```

---

## Appendices

### Appendix A: Contact Information

```markdown
## Internal Contacts
- **Security Team:** security@yourorganization.com
- **Incident Response:** ir@yourorganization.com
- **Management:** ciso@yourorganization.com

## External Contacts
- **CISA:** https://www.cisa.gov/cybersecurity
- **FBI:** https://www.fbi.gov/contact-us
- **ISAC:** [Industry-specific Information Sharing and Analysis Center]
```

### Appendix B: Tools and Scripts

```bash
# Quick access to all defense tools
polinrider_monitor.py -h
suspicious_package_detector.sh -h
maintainer_audit.py -h
```

### Appendix C: Checklists

#### Initial Response Checklist
- [ ] Document detection and alert details
- [ ] Isolate affected systems
- [ ] Activate incident response team
- [ ] Begin evidence collection
- [ ] Notify management
- [ ] Preserve chain of custody

#### Containment Checklist
- [ ] Block malicious network traffic
- [ ] Disable compromised accounts
- [ ] Remove malicious packages
- [ ] Apply emergency patches
- [ ] Document all containment actions

#### Recovery Checklist
- [ ] Restore from clean backups
- [ ] Validate system integrity
- [ ] Monitor for reinfection
- [ ] Gradual service restoration
- [ ] User notification (if required)
- [ ] Post-incident review

---

## Revision History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-07-04 | Initial release | Security Team |

---

**This is a living document. Review and update quarterly or after each incident.**
