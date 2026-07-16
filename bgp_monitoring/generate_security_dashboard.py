#!/usr/bin/env python3
"""
Security Dashboard Generator
Combines BGP monitoring and threat intelligence into a unified view
"""

import json
import os
import glob
from datetime import datetime, timezone
from typing import Dict, List

class SecurityDashboard:
    def __init__(self, monitoring_dir: str):
        self.monitoring_dir = monitoring_dir

    def get_latest_reports(self) -> tuple:
        """Get the latest BGP and threat reports"""
        # Find BGP reports
        bgp_reports = sorted(
            glob.glob(os.path.join(self.monitoring_dir, "bgp_report_*.json")),
            key=lambda x: x
        )

        # Pick the most comprehensive BGP report (largest by file size)
        latest_bgp = None
        max_size = 0
        for report in bgp_reports:
            try:
                size = os.path.getsize(report)
                # Also check event count as backup
                with open(report, 'r') as f:
                    data = json.load(f)
                    event_count = len(data.get('analysis', []))
                
                # Prefer reports with more events (larger content = more data)
                if size > max_size or event_count > 100:
                    max_size = size
                    latest_bgp = report
            except Exception as e:
                pass

        # Find latest threat report
        threat_reports = sorted(
            glob.glob(os.path.join(self.monitoring_dir, "threat_report_*.json")),
            key=lambda x: x
        )

        latest_threat = None
        if threat_reports:
            latest_threat = threat_reports[-1]

        return latest_bgp, latest_threat

    def generate_dashboard(self) -> str:
        """Generate a combined security dashboard"""
        bgp_file, threat_file = self.get_latest_reports()

        dashboard = []
        dashboard.append("=" * 70)
        dashboard.append("SECURITY MONITORING DASHBOARD")
        dashboard.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
        dashboard.append("=" * 70)
        dashboard.append("")

        # BGP Monitoring Section
        if bgp_file:
            dashboard.append("-" * 70)
            dashboard.append("🛡️ BGP MONITORING")
            dashboard.append("-" * 70)

            with open(bgp_file, 'r') as f:
                bgp_data = json.load(f)

            # Extract key metrics
            total_events = len(bgp_data.get('analysis', []))
            hijacks_by_risk = bgp_data.get('hijacks_by_risk', {})

            dashboard.append(f"Total BGP Events: {total_events}")
            dashboard.append("")
            dashboard.append("Risk Breakdown:")

            for risk_level in ['CRITICAL', 'HIGH', 'MEDIUM', 'MINIMAL']:
                count = len(hijacks_by_risk.get(risk_level, []))
                if count > 0:
                    dashboard.append(f"  {risk_level}: {count}")

            dashboard.append("")

            # Show recent high-risk events
            high_risk = hijacks_by_risk.get('HIGH', []) + hijacks_by_risk.get('CRITICAL', [])
            if high_risk:
                dashboard.append("Recent High-Risk Events:")
                for event in high_risk[:5]:
                    prefix = event.get('prefix', 'N/A')
                    origin = event.get('origin', 'N/A')
                    dashboard.append(f"  {prefix} from AS{origin}")
            else:
                dashboard.append("No high-risk events detected")

            dashboard.append("")

        # Threat Intelligence Section
        if threat_file:
            dashboard.append("-" * 70)
            dashboard.append("🚨 THREAT INTELLIGENCE")
            dashboard.append("-" * 70)

            with open(threat_file, 'r') as f:
                threat_data = json.load(f)

            dashboard.append(f"Threat Sources: {', '.join(threat_data.get('threat_sources', []))}")
            dashboard.append(f"Total Threat Matches: {threat_data['summary']['matched_threats']}")
            dashboard.append(f"High Risk Events: {threat_data['summary']['high_risk_events']}")
            dashboard.append("")

            # Feed status
            ti_summary = threat_data.get('threat_intelligence', {})
            dashboard.append("Feed Status:")

            cymru = ti_summary.get('cymru_feed', {})
            dashboard.append(f"  Cymru Top 100: {'✅ Active' if cymru.get('available') else '❌ Inactive'}")
            if cymru.get('available'):
                dashboard.append(f"    Malicious ASNs: {cymru.get('malicious_asns_count', 0)}")
                dashboard.append(f"    Malicious Prefixes: {cymru.get('malicious_prefixes_count', 0)}")

            alphamountain = ti_summary.get('alphamountain_feed', {})
            dashboard.append(f"  AlphaMountain: {'✅ Active' if alphamountain.get('available') else '❌ Inactive'}")
            if alphamountain.get('available'):
                dashboard.append(f"    Malicious Domains: {alphamountain.get('malicious_domains_count', 0)}")

            dashboard.append("")

            # Recent high-risk matches
            high_risk = threat_data.get('high_risk_events', [])
            if high_risk:
                dashboard.append("Recent Threat Matches:")
                for event in high_risk[:5]:
                    prefix = event.get('prefix', 'N/A')
                    origin = event.get('origin', 'N/A')
                    reasons = ', '.join(event.get('reasons', []))
                    dashboard.append(f"  {prefix} from AS{origin} ({reasons})")
            else:
                dashboard.append("No threat intelligence matches")

            dashboard.append("")

        # Footer
        dashboard.append("=" * 70)
        dashboard.append("END OF DASHBOARD")
        dashboard.append("=" * 70)

        return "\n".join(dashboard)

    def save_dashboard(self, filename: str = None):
        """Save dashboard to a file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(self.monitoring_dir, f"security_dashboard_{timestamp}.txt")

        dashboard_text = self.generate_dashboard()

        with open(filename, 'w') as f:
            f.write(dashboard_text)

        print(f"Dashboard saved to: {filename}")
        return filename


if __name__ == "__main__":
    monitoring_dir = "/Users/mitchparker/.openclaw/workspace/research/bgp_monitoring/monitoring_data"
    dashboard = SecurityDashboard(monitoring_dir)

    # Generate and print dashboard
    print(dashboard.generate_dashboard())

    # Save dashboard
    dashboard.save_dashboard()
