#!/usr/bin/env python3
"""
BGP Hijack Monitoring System
Monitors for BGP hijacking events using RIPEstat API
"""

import requests
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API endpoint for RIPEstat BGP hijack monitoring
RIPESTAT_API = "https://stat.ripe.net/"

class BGPHijackMonitor:
    def __init__(self):
        self.monitoring_dir = os.path.join(os.path.dirname(__file__), "monitoring_data")
        os.makedirs(self.monitoring_dir, exist_ok=True)
        self.last_check = self.load_last_check()

    def load_last_check(self) -> Optional[str]:
        """Load last check timestamp from file"""
        last_check_file = os.path.join(self.monitoring_dir, "last_check.json")
        if os.path.exists(last_check_file):
            with open(last_check_file, 'r') as f:
                data = json.load(f)
                return data.get('last_check')
        return None

    def save_last_check(self, timestamp: str):
        """Save last check timestamp"""
        last_check_file = os.path.join(self.monitoring_dir, "last_check.json")
        with open(last_check_file, 'w') as f:
            json.dump({'last_check': timestamp}, f)

    def get_bgp_hijacks(self) -> List[Dict]:
        """
        Query RIPEstat API for BGP hijack data
        """
        try:
            # Get BGP hijack data
            response = requests.get(
                f"{RIPESTAT_API}data/ripecert-overview.json",
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            hijacks = []

            # Process hijack events
            if 'data' in data and 'reported_events' in data['data']:
                for event in data['data']['reported_events']:
                    if event.get('category') == 'bgp_hijack':
                        hijack_info = {
                            'timestamp': event.get('time_of_report'),
                            'destination': event.get('destination'),
                            'origin': event.get('origin'),
                            'prefix': event.get('prefix'),
                            'details': event.get('details', {}),
                            'analyst_generated': event.get('analyst_generated', False),
                            'status': event.get('status')
                        }
                        hijacks.append(hijack_info)

            return hijacks

        except Exception as e:
            logger.error(f"Error fetching BGP hijack data: {e}")
            return []

    def get_announced_prefixes(self) -> List[Dict]:
        """
        Get BGP announcements for monitoring
        """
        try:
            response = requests.get(
                f"{RIPESTAT_API}data/ripecert-announcements.json",
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            prefixes = []
            if 'data' in data and 'announcements' in data['data']:
                for announcement in data['data']['announcements']:
                    prefix_info = {
                        'timestamp': announcement.get('time_of_report'),
                        'prefix': announcement.get('prefix'),
                        'origin_as': announcement.get('origin_as'),
                        'next_hop': announcement.get('next_hop'),
                        'valid': announcement.get('valid', True)
                    }
                    prefixes.append(prefix_info)

            return prefixes

        except Exception as e:
            logger.error(f"Error fetching BGP announcements: {e}")
            return []

    def analyze_hijack_risk(self, hijack: Dict) -> Dict:
        """
        Analyze risk level of a BGP hijack event
        """
        risk_score = 0
        risk_factors = []

        # Check if analyst-generated (higher confidence)
        if hijack.get('analyst_generated'):
            risk_score += 30
            risk_factors.append("analyst_confirmed")

        # Check hijack status
        status = hijack.get('status', '')
        if 'ongoing' in status.lower():
            risk_score += 25
            risk_factors.append("ongoing_hijack")
        elif 'resolved' in status.lower():
            risk_score -= 20
            risk_factors.append("resolved")

        # Check prefix characteristics
        prefix = hijack.get('prefix', '')
        if self._is_critical_prefix(prefix):
            risk_score += 20
            risk_factors.append("critical_network")

        # Check origin AS
        origin = hijack.get('origin', '')
        if self._is_suspicious_origin(origin):
            risk_score += 25
            risk_factors.append("suspicious_origin")

        return {
            'risk_score': risk_score,
            'risk_level': self._get_risk_level(risk_score),
            'risk_factors': risk_factors
        }

    def _is_critical_prefix(self, prefix: str) -> bool:
        """Check if prefix belongs to critical infrastructure"""
        critical_patterns = [
            '.gov', '.mil', '.edu', '10.', '192.168.', '172.16.'
        ]
        for pattern in critical_patterns:
            if pattern in prefix:
                return True
        return False

    def _is_suspicious_origin(self, origin: str) -> bool:
        """Check if origin AS is suspicious"""
        suspicious_as = [
            'AS0', 'AS23456', 'AS65535'  # Reserved/invalid AS numbers
        ]
        return origin in suspicious_as

    def _get_risk_level(self, score: int) -> str:
        """Determine risk level from score"""
        if score >= 70:
            return "CRITICAL"
        elif score >= 50:
            return "HIGH"
        elif score >= 30:
            return "MEDIUM"
        elif score >= 10:
            return "LOW"
        return "MINIMAL"

    def generate_report(self, hijacks: List[Dict]) -> Dict:
        """
        Generate comprehensive BGP monitoring report
        """
        report = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'total_hijacks': len(hijacks),
            'hijacks_by_risk': {'CRITICAL': [], 'HIGH': [], 'MEDIUM': [], 'LOW': [], 'MINIMAL': []},
            'hijacks_by_status': {'ongoing': [], 'resolved': []},
            'analysis': []
        }

        for hijack in hijacks:
            analysis = self.analyze_hijack_risk(hijack)
            hijack['analysis'] = analysis

            # Categorize by risk level
            risk_level = analysis['risk_level']
            report['hijacks_by_risk'][risk_level].append(hijack)

            # Categorize by status
            status = hijack.get('status', '').lower()
            if 'ongoing' in status:
                report['hijacks_by_status']['ongoing'].append(hijack)
            elif 'resolved' in status:
                report['hijacks_by_status']['resolved'].append(hijack)

            report['analysis'].append({
                'prefix': hijack.get('prefix'),
                'origin': hijack.get('origin'),
                'risk_level': risk_level,
                'risk_score': analysis['risk_score'],
                'factors': analysis['risk_factors']
            })

        return report

    def save_report(self, report: Dict):
        """Save monitoring report to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(self.monitoring_dir, f"bgp_report_{timestamp}.json")

        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Report saved to {report_file}")
        return report_file

    def run_monitoring_cycle(self):
        """Run a complete monitoring cycle"""
        logger.info("Starting BGP hijack monitoring cycle...")

        # Fetch data
        hijacks = self.get_bgp_hijacks()
        announcements = self.get_announced_prefixes()

        logger.info(f"Found {len(hijacks)} BGP hijack events")

        # Generate and save report
        report = self.generate_report(hijacks)

        # Save report
        report_file = self.save_report(report)

        # Update last check timestamp
        self.save_last_check(datetime.now(timezone.utc).isoformat())

        # Log summary
        logger.info(f"Monitoring cycle complete. Found {len(hijacks)} hijacks.")
        logger.info(f"Ongoing hijacks: {len(report['hijacks_by_status']['ongoing'])}")
        logger.info(f"Critical risk hijacks: {len(report['hijacks_by_risk']['CRITICAL'])}")

        return report

    def get_alerts(self, report: Dict, threshold_risk: str = "MEDIUM") -> List[Dict]:
        """
        Generate alerts for high-risk hijacks
        """
        alerts = []

        # Map threshold to minimum risk score
        threshold_scores = {
            "LOW": 10,
            "MEDIUM": 30,
            "HIGH": 50,
            "CRITICAL": 70
        }

        min_score = threshold_scores.get(threshold_risk, 30)

        for analysis in report['analysis']:
            if analysis['risk_score'] >= min_score:
                alert = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'prefix': analysis['prefix'],
                    'origin': analysis['origin'],
                    'risk_level': analysis['risk_level'],
                    'risk_score': analysis['risk_score'],
                    'factors': analysis['factors'],
                    'alert_type': 'BGP_HIJACK_DETECTED',
                    'severity': 'HIGH' if analysis['risk_score'] >= 50 else 'MEDIUM'
                }
                alerts.append(alert)

        return alerts

    def create_github_issue(self, report: Dict, api_token: str = None):
        """
        Create GitHub issue for tracking BGP hijack incidents
        """
        if not api_token:
            logger.warning("GitHub token not provided, skipping issue creation")
            return

        # Implement GitHub API integration here if needed
        logger.info("GitHub issue creation would be implemented here")

def main():
    """Main monitoring loop"""
    monitor = BGPHijackMonitor()

    logger.info("BGP Hijack Monitor starting...")

    try:
        report = monitor.run_monitoring_cycle()

        # Print summary
        print("\n" + "="*60)
        print("BGP HIJACK MONITORING SUMMARY")
        print("="*60)
        print(f"Total Hijacks Found: {report['total_hijacks']}")
        print(f"Ongoing: {len(report['hijacks_by_status']['ongoing'])}")
        print(f"Resolved: {len(report['hijacks_by_status']['resolved'])}")

        print("\nRisk Distribution:")
        for risk_level, hijacks in report['hijacks_by_risk'].items():
            if hijacks:
                print(f"  {risk_level}: {len(hijacks)} hijacks")

        print("\n" + "="*60)

    except Exception as e:
        logger.error(f"Monitoring cycle failed: {e}")
        raise

if __name__ == "__main__":
    main()
