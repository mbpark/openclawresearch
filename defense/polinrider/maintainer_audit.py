#!/usr/bin/env python3
"""
PolinRider Defense - Maintainer Account Audit Tool
Automated verification of maintainer credentials and account security.
"""

import os
import sys
import json
import logging
import subprocess
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import hashlib
import base64
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('maintainer_audit.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MaintainerAuditor:
    def __init__(self, config_path: str = 'maintainer_config.json'):
        self.config = self.load_config(config_path)
        self.audit_results: List[Dict] = []
        self.credential_changes: List[Dict] = []
        self.security_warnings: List[Dict] = []

        # Configuration
        self.alert_thresholds = {
            'email_change_days': self.config.get('email_change_days', 7),
            'mfa_required': self.config.get('mfa_required', True),
            'password_age_days': self.config.get('password_age_days', 90),
            'suspicious_login_locations': self.config.get('suspicious_login_locations', [])
        }

        # Known malicious email domains
        self.malicious_domains = [
            'temp-mail.org',
            'mailinator.com',
            '10minutemail.com',
            'guerrillamail.com'
        ]

    def load_config(self, config_path: str) -> Dict:
        """Load maintainer audit configuration."""
        default_config = {
            'email_change_days': 7,
            'mfa_required': True,
            'password_age_days': 90,
            'suspicious_login_locations': [],
            'audit_interval_hours': 24
        }

        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    return {**default_config, **config}
            return default_config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return default_config

    def check_email_change(self, package_name: str, maintainer_email: str, timestamp: datetime) -> Optional[Dict]:
        """Check for suspicious email changes."""
        # Check if email is from a disposable email service
        email_domain = maintainer_email.split('@')[1].lower()

        for malicious_domain in self.malicious_domains:
            if malicious_domain in email_domain:
                alert = {
                    'timestamp': datetime.now().isoformat(),
                    'type': 'SUSPICIOUS_EMAIL',
                    'severity': 'HIGH',
                    'package': package_name,
                    'details': f"Suspicious disposable email: {maintainer_email}",
                    'recommendation': 'Verify maintainer identity through alternative channels'
                }
                self.audit_results.append(alert)
                return alert

        # Check for recent email changes
        days_since_change = (datetime.now() - timestamp).days
        if days_since_change < self.alert_thresholds['email_change_days']:
            alert = {
                'timestamp': datetime.now().isoformat(),
                'type': 'RECENT_EMAIL_CHANGE',
                'severity': 'MEDIUM',
                'package': package_name,
                'details': f"Email changed {days_since_change} days ago",
                'recommendation': 'Monitor for subsequent changes'
            }
            self.audit_results.append(alert)
            return alert

        return None

    def verify_mfa_status(self, package_name: str, maintainer_id: str) -> Optional[Dict]:
        """Verify maintainer has MFA enabled."""
        # This would typically integrate with npm, PyPI, or other registry APIs
        # For now, simulate checking MFA status

        try:
            # Check npm registry for maintainer MFA status
            response = requests.get(
                f"https://registry.npmjs.org/-/v1/search?text=maintainer:{maintainer_id}",
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                # Check if maintainer has MFA enabled (simplified check)
                # In real implementation, would check specific API endpoints
                has_mfa = True  # Placeholder for actual MFA check

                if not has_mfa and self.alert_thresholds['mfa_required']:
                    alert = {
                        'timestamp': datetime.now().isoformat(),
                        'type': 'MFA_NOT_ENABLED',
                        'severity': 'HIGH',
                        'package': package_name,
                        'details': f"Maintainer {maintainer_id} may not have MFA enabled",
                        'recommendation': 'Require MFA for all package maintainers'
                    }
                    self.audit_results.append(alert)
                    return alert

        except Exception as e:
            logger.error(f"Error checking MFA status: {e}")

        return None

    def check_credential_anomalies(self, package_name: str, maintainer_data: Dict) -> List[Dict]:
        """Check for credential-related anomalies."""
        anomalies = []

        # Check for unusual package metadata
        if 'description' in maintainer_data:
            description = maintainer_data['description']
            # Look for suspicious patterns
            if re.search(r'https?://[a-zA-Z0-9._-]+\.[a-zA-Z]{2,}', description):
                # Check if URL points to known malicious domains
                url_match = re.search(r'https?://([a-zA-Z0-9._-]+)', description)
                if url_match:
                    url_domain = url_match.group(1)
                    if self.is_suspicious_domain(url_domain):
                        anomaly = {
                            'timestamp': datetime.now().isoformat(),
                            'type': 'SUSPICIOUS_URL',
                            'severity': 'MEDIUM',
                            'package': package_name,
                            'details': f"Suspicious URL in package description: {url_domain}",
                            'recommendation': 'Review package description and remove suspicious links'
                        }
                        anomalies.append(anomaly)

        # Check for unusual script content
        if 'scripts' in maintainer_data:
            scripts = maintainer_data['scripts']
            for script_name, script_cmd in scripts.items():
                if self.is_suspicious_script(script_cmd):
                    anomaly = {
                        'timestamp': datetime.now().isoformat(),
                        'type': 'SUSPICIOUS_SCRIPT',
                        'severity': 'CRITICAL',
                        'package': package_name,
                        'details': f"Suspicious script found: {script_name} = {script_cmd}",
                        'recommendation': 'Remove or replace suspicious script immediately'
                    }
                    anomalies.append(anomaly)

        return anomalies

    def is_suspicious_script(self, script_command: str) -> bool:
        """Check if a script command is suspicious."""
        suspicious_patterns = [
            r'eval\s*\(',
            r'exec\s*\(',
            r'system\s*\(',
            r'wget\s+',
            r'curl\s+',
            r'nc\s+',
            r'bash\s+-i',
            r'python\s+-c',
            r'chmod\s*+\w+',
            r'rm\s+-rf',
            r'sudo\s+',
            r'passwd\s+',
            r'useradd\s+',
            r'chmod\s+777'
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, script_command, re.IGNORECASE):
                return True
        return False

    def is_suspicious_domain(self, domain: str) -> bool:
        """Check if a domain is suspicious."""
        # Check against known malicious domains
        for malicious_domain in self.malicious_domains:
            if malicious_domain in domain:
                return True

        # Check domain age (simplified)
        try:
            # This would normally use a domain age API
            # For now, check for common patterns
            if re.match(r'^[0-9]+[a-zA-Z]{2,}\.[a-zA-Z]{2,}$', domain):
                return True
        except Exception:
            pass

        return False

    def audit_all_packages(self, package_dir: str = '.') -> List[Dict]:
        """Audit all packages in a directory."""
        all_anomalies = []

        for root, dirs, files in os.walk(package_dir):
            if 'package.json' in files:
                package_path = os.path.join(root, 'package.json')
                package_name = os.path.basename(root)

                try:
                    with open(package_path, 'r') as f:
                        package_data = json.load(f)

                    # Check maintainer information
                    if 'maintainers' in package_data:
                        for maintainer in package_data['maintainers']:
                            maintainer_email = maintainer.get('email', '')
                            maintainer_id = maintainer.get('name', '')

                            # Check email changes
                            email_change_alert = self.check_email_change(
                                package_name, maintainer_email, datetime.now()
                            )
                            if email_change_alert:
                                all_anomalies.append(email_change_alert)

                            # Check MFA status
                            mfa_alert = self.verify_mfa_status(package_name, maintainer_id)
                            if mfa_alert:
                                all_anomalies.append(mfa_alert)

                    # Check for credential anomalies
                    anomalies = self.check_credential_anomalies(package_name, package_data)
                    all_anomalies.extend(anomalies)

                except Exception as e:
                    logger.error(f"Error auditing package {package_name}: {e}")

        return all_anomalies

    def export_results(self, format: str = 'json') -> str:
        """Export audit results to specified format."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if format == 'json':
            output_file = f'maintainer_audit_results_{timestamp}.json'
            with open(output_file, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'total_audits': len(self.audit_results),
                    'results': self.audit_results
                }, f, indent=2)
            return output_file

        elif format == 'csv':
            output_file = f'maintainer_audit_results_{timestamp}.csv'
            with open(output_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'type', 'severity', 'package', 'details', 'recommendation'])
                for result in self.audit_results:
                    writer.writerow([
                        result['timestamp'],
                        result['type'],
                        result['severity'],
                        result['package'],
                        result['details'],
                        result['recommendation']
                    ])
            return output_file

        else:
            raise ValueError(f"Unsupported export format: {format}")

    def get_security_summary(self) -> Dict:
        """Get a summary of security findings."""
        severity_counts = {}
        type_counts = {}

        for result in self.audit_results:
            severity = result['severity']
            result_type = result['type']

            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            type_counts[result_type] = type_counts.get(result_type, 0) + 1

        return {
            'total_findings': len(self.audit_results),
            'severity_breakdown': severity_counts,
            'type_breakdown': type_counts,
            'highest_severity': max(severity_counts.keys(), key=lambda x: ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].index(x)) if severity_counts else None,
            'timestamp': datetime.now().isoformat()
        }

def main():
    """Main function to run maintainer audit."""
    parser = argparse.ArgumentParser(description='PolinRider Maintainer Audit Tool')
    parser.add_argument('package_dir', nargs='?', default='.', help='Directory to scan')
    parser.add_argument('--export', choices=['json', 'csv'], default='json', help='Export format')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    auditor = MaintainerAuditor()

    logger.info(f"Starting maintainer audit of {args.package_dir}")

    # Run audit
    anomalies = auditor.audit_all_packages(args.package_dir)

    # Export results
    output_file = auditor.export_results(args.export)

    logger.info(f"Audit completed. Found {len(anomalies)} anomalies.")
    logger.info(f"Results exported to: {output_file}")

    # Print summary
    summary = auditor.get_security_summary()
    logger.info(f"Summary: {summary['total_findings']} total findings")
    logger.info(f"Highest severity: {summary['highest_severity']}")

    return anomalies

if __name__ == '__main__':
    main()
