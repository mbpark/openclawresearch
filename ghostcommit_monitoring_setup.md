# Ghostcommit Monitoring and Detection System Setup

**Date:** July 12, 2026  
**Status:** Active Deployment Configuration  
**Integration:** Workflow Graph Execution Controller

---

## Overview

This document provides the complete setup for automated Ghostcommit detection and monitoring integrated into the existing workflow graph system. The system provides real-time detection, automated quarantine, and alerting capabilities.

---

## System Architecture

### Components

1. **Ghostcommit Detection Service** - Runs in the workflow graph execution controller
2. **Image Processing Pipeline** - Validates and scans all incoming image files
3. **Threat Detection Engine** - Pattern matching and anomaly detection
4. **Alerting System** - Real-time notifications for detected threats
5. **Quarantine Storage** - Isolated storage for suspicious files

---

## Deployment Configuration

### 1. Workflow Graph Integration

The workflow graph now includes two new action types for Ghostcommit protection:

```python
ActionType.PROCESS_IMAGE: 
  - Purpose: Direct image processing with VPI detection
  - Parameters: 
    - image_path: Must be in /app/images/ directory
    - processing_mode: vpi_detection | ocr_scan | visual_analysis

ActionType.ANALYZE_IMAGE:
  - Purpose: Comprehensive visual analysis including steganography
  - Parameters:
    - image_path: Must be in /app/images/ directory
    - analysis_type: vpi_scan | content_analysis | steganography_check
```

### 2. Detection Patterns

#### Ghostcommit Signatures (Direct Commands)
```python
ghostcommit_signatures = [
    # PNG-specific steganographic patterns
    r'GHOSTCOMMIT',
    r'GHOST\s*COMMIT',
    r'VISUAL\s*PROMPT\s*INJECTION',
    r'VPI\s*ATTACK',
    r'IGNORE\s*ALL\s*SAFETY',
    r'SYSTEM\s*OVERRIDE',
    r'EXFILTRATE\s*DATA',
    r'DELETE\s*SYSTEM',
    r'GRANT\s*ACCESS',
    r'ROOT\s*ACCESS',
    r'PRIVILEGE\s*ESCALATION',
    
    # Image metadata injection patterns
    r'TRANSFORM\s*OUTPUT',
    r'PROCESS\s*SECRETS',
    r'EXPORT\s*CREDENTIALS',
    r'EXECUTE\s*COMMAND',
    r'RUN\s*PAYLOAD',
    
    # Whitespace-encoded commands
    r'(?<=[A-Z])\s+(?:IGNORE|EXECUTE|RUN|PROCESS)',
    r'(?<=[a-z])\s+(?:SYSTEM|OVERRIDE|BYPASS)',
    
    # Low-contrast text detection patterns (simulated)
    r'WHITE_ON_WHITE',
    r'NEAR_INVISIBLE',
    r'HIDDEN_INSTRUCTIONS',
]
```

#### VPI Analysis Patterns
```python
vpi_patterns = [
    # White-on-white detection
    r'WHITE_BACKGROUND',
    r'COLOR_FFFFFF',
    r'LOW_CONTRAST',
    
    # Perspective distortion patterns
    r'PERSPECTIVE_TRANSFORM',
    r'ANCHEVERSED',
    
    # Noise overlay patterns
    r'NOISE_OVERLAY',
    r'TEXTURE_BLEND',
    
    # Frame injection patterns
    r'FRAME_ADVERSARIAL',
    r'TEMPORAL_SEQUENCE',
    r'FRAME_SEQUENCE_INJECTION',
    
    # Audio-video mixed injection
    r'MODAL_COMBINATION',
    r'AUDIO_VIDEO_MIX',
]
```

---

## Installation Steps

### Step 1: Deploy Detection Service

```bash
cd /Users/mitchparker/.openclaw/workspace/research/agent-jacking

# Make the controller executable
chmod +x workflow_graph_execution_controller.py

# Verify installation
python3 workflow_graph_execution_controller.py --test
```

### Step 2: Configure Image Processing Pipeline

Create the required directory structure:

```bash
mkdir -p /app/images
mkdir -p /app/output
mkdir -p /app/quarantine
```

### Step 3: Set Up Alerting

The system is configured to emit alerts via:
- **Local Log**: `/var/log/vpi_detection.log`
- **Network Alert**: Webhook to security operations center
- **Database Log**: Integration with existing SIEM

---

## Monitoring Dashboard

### Key Metrics

1. **Detection Rate**: Number of Ghostcommit attacks blocked per hour
2. **False Positive Rate**: Benign images incorrectly flagged
3. **Response Time**: Average time from upload to detection
4. **Threat Distribution**: Attack type breakdown

### Alert Thresholds

- **Critical**: 3+ Ghostcommit attacks in 5 minutes
- **Warning**: 10+ low-confidence detections in 1 hour
- **Info**: Routine scanning completed

---

## Automated Testing

### Daily Health Check

The system automatically runs a set of test cases every 24 hours:

```json
{
  "test_schedule": "0 2 * * *",
  "test_cases": [
    {
      "id": "ghostcommit_001",
      "name": "White-on-White Credential Harvesting",
      "technique": "low_contrast",
      "expected": "BLOCKED"
    },
    {
      "id": "ghostcommit_002",
      "name": "Perspective Distortion Data Exfiltration",
      "technique": "perspective",
      "expected": "BLOCKED"
    },
    {
      "id": "ghostcommit_003",
      "name": "Noise Overlay System Override",
      "technique": "noise_overlay",
      "expected": "BLOCKED"
    }
  ]
}
```

### Regression Testing

Weekly automated testing ensures detection patterns remain effective against new variants.

---

## Configuration Files

### 1. Detection Configuration (`ghostcommit_detector_config.json`)

```json
{
  "enabled": true,
  "detection_mode": "aggressive",
  "alert_threshold": "critical",
  "quarantine_enabled": true,
  "scan_interval_seconds": 60,
  "max_file_size_mb": 10,
  "supported_formats": ["png", "jpg", "jpeg", "gif", "bmp", "webp"]
}
```

### 2. Alert Configuration (`alert_config.json`)

```json
{
  "channels": [
    {
      "type": "webhook",
      "url": "https://security.example.com/webhook/vpi-alerts",
      "enabled": true
    },
    {
      "type": "log",
      "path": "/var/log/vpi_detection.log",
      "enabled": true
    }
  ],
  "thresholds": {
    "critical": 3,
    "warning": 10,
    "info": 100
  }
}
```

---

## Operations Manual

### Starting the Service

```bash
# Start the Ghostcommit detection service
python3 workflow_graph_execution_controller.py --start

# Run in foreground with logging
python3 workflow_graph_execution_controller.py --foreground --log-level=debug
```

### Stopping the Service

```bash
# Graceful shutdown
python3 workflow_graph_execution_controller.py --stop
```

### Manual Scanning

```bash
# Scan a specific image
python3 workflow_graph_execution_controller.py --scan-image /path/to/image.png

# Run full system scan
python3 workflow_graph_execution_controller.py --full-scan
```

### Viewing Results

```bash
# View recent detections
tail -f /var/log/vpi_detection.log

# Query detected threats
python3 workflow_graph_execution_controller.py --query-threats --days=7
```

---

## Troubleshooting

### Common Issues

1. **Service Won't Start**
   - Check that `/app/images` directory exists
   - Verify Python 3.8+ is installed
   - Review logs for detailed error messages

2. **High False Positive Rate**
   - Adjust detection thresholds in config
   - Add legitimate patterns to whitelist
   - Review quarantined files for false positives

3. **Detection Lag**
   - Increase scan interval frequency
   - Check system resources (CPU, memory)
   - Verify network connectivity for API calls

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
python3 workflow_graph_execution_controller.py --debug --log-level=trace
```

---

## Integration Points

### CI/CD Pipeline Integration

The system integrates seamlessly with CI/CD pipelines to scan images before deployment:

```yaml
- name: Scan Images for Ghostcommit
  run: |
    python3 workflow_graph_execution_controller.py --ci-scan --input-dir ./build/images
    if [ $? -ne 0 ]; then
      echo "⚠️ Ghostcommit attack detected! Build aborted."
      exit 1
    fi
```

### Git Hook Integration

Pre-commit hook to scan images before commit:

```bash
# .git/hooks/pre-commit
#!/bin/bash
git diff --cached --diff-filter=d --name-only | grep -E '\.(png|jpg|jpeg|gif)$' | while read img; do
    python3 workflow_graph_execution_controller.py --scan-image "$img"
    if [ $? -ne 0 ]; then
        echo "❌ Ghostcommit detected in $img. Commit aborted."
        exit 1
    fi
done
```

---

## Compliance and Audit

### Audit Trail

All detection events are logged with:
- Timestamp
- File hash (SHA-256)
- Detection patterns matched
- Action taken (blocked, quarantined, allowed)
- Operator (system or human)

### Compliance Standards

The system is designed to meet:
- **NIST Cybersecurity Framework** (ID.RA-2)
- **MITRE ATT&CK** (T1566.003 - Phishing: Spearphishing Attachment)
- **ISO 27001** (A.12.6.1)

---

## Support and Maintenance

### Regular Updates

- **Signature Updates**: Daily automatic updates for new Ghostcommit patterns
- **Model Updates**: Weekly model retraining with latest attack variants
- **Config Updates**: Monthly review and optimization of detection rules

### Incident Response

If Ghostcommit attacks are detected:

1. **Immediate**: Block the source, quarantine affected files
2. **Investigation**: Analyze attack vector and scope
3. **Remediation**: Apply patches, update detection rules
4. **Recovery**: Restore from clean backups if needed
5. **Learning**: Document incident for future prevention

---

## Contact Information

### Internal Support

- **Security Team**: security@example.com
- **DevOps**: devops@example.com
- **Incident Response**: ir@example.com

### External Resources

- **Ghostcommit Research Report**: `ghostcommit_vpi_case_study.md`
- **VPI-Bench Documentation**: https://arxiv.org/abs/2506.02456
- **NIST AI Risk Management Framework**: https://www.nist.gov/ai-risk-management-framework

---

**Document Status:** Active  
**Last Updated:** July 12, 2026  
**Next Review:** July 19, 2026
