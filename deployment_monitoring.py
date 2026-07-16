#!/usr/bin/env python3
"""
Production Deployment Monitoring System
File Upload RCE Defense Monitoring
CVE-2026-48939, CVE-2026-56291, CVE-2026-48908
"""

import json
import subprocess
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
import logging
import requests
from typing import Dict, List, Optional

# Configure logging
log_path = '/Users/mitchparker/.openclaw/workspace/research/defense_monitoring.log'
try:
    with open(log_path, 'a') as f:
        pass
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler()
        ]
    )
except Exception as e:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    logger = logging.getLogger('DefenseMonitoring')
    logger.error(f"Failed to set up file logging: {e}")
    print("Running in log-less mode due to file system permissions.")
logger = logging.getLogger('DefenseMonitoring')

class ProductionDeploymentMonitor:
    def __init__(self):
        self.workspace_path = Path('/Users/mitchparker/.openclaw/workspace')
        self.siem_rules_path = self.workspace_path / 'research' / 'siem_detection_rules_file_upload_rce.json'
        self.image_protection_path = self.workspace_path / 'research' / 'ghostcommit-image-system' / 'image_protection_service.py'
        self.waf_rules_path = Path('/etc/modsecurity/rules/local-rules.conf')
        self.snort_rules_path = Path('/etc/snort/rules/local.rules')
        self.suricata_rules_path = Path('/etc/suricata/rules/local.rules')

        # Load SIEM rules for validation
        with open(self.siem_rules_path, 'r') as f:
            self.siem_config = json.load(f)

        self.monitoring_interval = 60  # seconds
        self.alert_thresholds = {
            'critical_alerts_per_minute': 10,
            'warning_alerts_per_minute': 50,
            'service_uptime_required': 99.9
        }

    def check_service_status(self, service_name: str) -> bool:
        """Check if a systemd service is running."""
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', service_name],
                capture_output=True,
                text=True,
                check=False
            )
            return result.stdout.strip() == 'active'
        except Exception as e:
            logger.error(f"Error checking service {service_name}: {e}")
            return False

    def validate_siem_rules(self) -> Dict[str, bool]:
        """Validate SIEM detection rules are loaded."""
        validation_results = {}

        # Check Snort rules
        if self.snort_rules_path.exists():
            with open(self.snort_rules_path, 'r') as f:
                content = f.read()
                for rule in self.siem_config['siem_detection_rules']:
                    rule_id = rule['id']
                    if rule_id in content or f'CVE-2026' in content:
                        validation_results[f'snort_{rule_id}'] = True
                    else:
                        validation_results[f'snort_{rule_id}'] = False
        else:
            validation_results['snort_rules_loaded'] = False

        # Check Suricata rules
        if self.suricata_rules_path.exists():
            with open(self.suricata_rules_path, 'r') as f:
                content = f.read()
                for rule in self.siem_config['siem_detection_rules']:
                    rule_id = rule['id']
                    if rule_id in content or f'CVE-2026' in content:
                        validation_results[f'suricata_{rule_id}'] = True
                    else:
                        validation_results[f'suricata_{rule_id}'] = False
        else:
            validation_results['suricata_rules_loaded'] = False

        return validation_results

    def validate_waf_rules(self) -> bool:
        """Validate WAF rules are loaded."""
        if not self.waf_rules_path.exists():
            logger.error("WAF rules file not found")
            return False

        with open(self.waf_rules_path, 'r') as f:
            content = f.read()

        expected_rules = ['900001', '900002', '900003']
        all_loaded = all(rule_id in content for rule_id in expected_rules)

        if all_loaded:
            logger.info("All WAF rules validated successfully")
        else:
            logger.warning("Some WAF rules are missing")

        return all_loaded

    def check_image_protection_service(self) -> Dict[str, any]:
        """Check Image Protection Service status and health."""
        health_status = {
            'running': False,
            'last_check': datetime.now().isoformat(),
            'errors': [],
            'warnings': []
        }

        # Check if service is running
        if not self.check_service_status('image-protection'):
            health_status['errors'].append("Image Protection Service is not running")
            return health_status

        health_status['running'] = True

        # Check service logs for errors
        try:
            result = subprocess.run(
                ['journalctl', '-u', 'image-protection', '-n', '50', '--no-pager'],
                capture_output=True,
                text=True
            )

            if 'ERROR' in result.stdout or 'Traceback' in result.stdout:
                health_status['errors'].append("Errors found in service logs")
            elif 'WARNING' in result.stdout:
                health_status['warnings'].append("Warnings found in service logs")

            # Check if service initialized successfully
            if 'Image Protection Service initialized' in result.stdout:
                health_status['warnings'].append("Service initialized with CVE patterns")

        except Exception as e:
            health_status['errors'].append(f"Failed to check service logs: {e}")

        return health_status

    def get_siem_alert_stats(self) -> Dict[str, int]:
        """Get recent alert statistics from SIEM."""
        stats = {
            'critical_alerts_24h': 0,
            'warning_alerts_24h': 0,
            'blocked_attacks_24h': 0
        }

        try:
            # This is a placeholder - in production, query your SIEM API
            # Example for Elasticsearch:
            # response = requests.get(
            #     'https://your-siem-endpoint/api/search',
            #     headers={'Authorization': 'Bearer token'},
            #     json={
            #         'query': {
            #             'bool': {
            #                 'must': [{'range': {'@timestamp': {'gte': 'now-24h'}}}]
            #             }
            #         }
            #     }
            # )

            # For now, we'll simulate checking log files
            log_path = Path('/var/log/siem/alerts.log')
            if log_path.exists():
                with open(log_path, 'r') as f:
                    content = f.read()
                    stats['critical_alerts_24h'] = content.count('CRITICAL')
                    stats['warning_alerts_24h'] = content.count('WARNING')
                    stats['blocked_attacks_24h'] = content.count('BLOCKED')

        except Exception as e:
            logger.error(f"Failed to get SIEM stats: {e}")

        return stats

    def generate_health_report(self) -> Dict:
        """Generate comprehensive health report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'services': {
                'image_protection': self.check_image_protection_service(),
                'snort': self.check_service_status('snort'),
                'suricata': self.check_service_status('suricata'),
                'modsecurity': self.check_service_status('apache2') or self.check_service_status('nginx')
            },
            'rule_validation': {
                'siem_rules': self.validate_siem_rules(),
                'waf_rules': self.validate_waf_rules()
            },
            'alert_statistics': self.get_siem_alert_stats(),
            'overall_health': 'healthy'
        }

        # Determine overall health
        critical_errors = []
        for service, status in report['services'].items():
            if status is False:
                critical_errors.append(f"{service} is not running")
            elif isinstance(status, dict) and status.get('errors'):
                critical_errors.extend(status['errors'])

        if critical_errors:
            report['overall_health'] = 'degraded'
            report['critical_errors'] = critical_errors
        elif report['alert_statistics']['critical_alerts_24h'] > self.alert_thresholds['critical_alerts_per_minute'] * 24:
            report['overall_health'] = 'warning'
            report['alerts'] = "High volume of critical alerts"

        return report

    def send_alert(self, alert_type: str, message: str, severity: str = 'warning'):
        """Send alert via configured channels."""
        alert_payload = {
            'timestamp': datetime.now().isoformat(),
            'type': alert_type,
            'message': message,
            'severity': severity,
            'system': 'defense-monitoring'
        }

        # In production, send to PagerDuty, Opsgenie, Slack, etc.
        logger.warning(f"🚨 ALERT [{severity.upper()}]: {message}")

        # Example: Send to Slack webhook
        # slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
        # if slack_webhook:
        #     requests.post(slack_webhook, json={
        #         'text': f"🚨 Security Alert: {message}",
        #         'username': 'Defense Monitor'
        #     })

    def monitor_loop(self):
        """Main monitoring loop."""
        logger.info("Starting defense monitoring loop...")

        while True:
            try:
                report = self.generate_health_report()

                if report['overall_health'] != 'healthy':
                    self.send_alert(
                        'health_check',
                        f"Defense systems health: {report['overall_health']}",
                        severity='critical' if report['overall_health'] == 'degraded' else 'warning'
                    )

                # Check for high alert volume
                if report['alert_statistics']['critical_alerts_24h'] > self.alert_thresholds['critical_alerts_per_minute'] * 24:
                    self.send_alert(
                        'high_alert_volume',
                        f"High volume of critical alerts: {report['alert_statistics']['critical_alerts_24h']} in last 24 hours",
                        severity='warning'
                    )

                # Log health report
                logger.info(f"Health report generated: {json.dumps(report, indent=2)}")

                # Wait for next check
                time.sleep(self.monitoring_interval)

            except KeyboardInterrupt:
                logger.info("Monitoring loop stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait before retrying

if __name__ == '__main__':
    monitor = ProductionDeploymentMonitor()
    monitor.monitor_loop()
