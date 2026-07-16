#!/usr/bin/env python3
"""
Hybrid Threat Intelligence Integration for BGP Monitoring
Handles both ASN/Prefix feeds and Domain feeds
"""

import requests
import csv
import json
import os
import logging
import ipaddress
import socket
import dns.resolver
import re
from datetime import datetime, timezone
from typing import Dict, List, Set, Optional, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HybridThreatIntelIntegrator:
    def __init__(self, virustotal_api_key=None):
        self.monitoring_dir = os.path.join(os.path.dirname(__file__), "monitoring_data")
        os.makedirs(self.monitoring_dir, exist_ok=True)
        self.cymru_cache = os.path.join(self.monitoring_dir, "cymru_cache.json")
        self.alphamountain_cache = os.path.join(self.monitoring_dir, "alphamountain_cache.json")
        self.virustotal_cache = os.path.join(self.monitoring_dir, "virustotal_cache.json")
        self.cache_age = 24 * 60 * 60  # 24 hours
        self.domain_ip_cache = {}  # In-memory cache for domain-to-IP resolution
        self.virustotal_api_key = virustotal_api_key or os.getenv("VIRUSTOTAL_API_KEY")
        self.virustotal_rate_limit = 4  # requests per second
        self.virustotal_recent = {}  # Cache for recent VT lookups

    def fetch_cymru_data(self) -> Optional[Dict]:
        """Fetch Team Cymru ASN/Prefix threat data"""
        try:
            url = "https://raw.githubusercontent.com/team-cymru/Community-Top-100/master/top100.csv"
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            if response.status_code != 200:
                return None

            data = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'raw': [],
                'malicious_asns': set(),
                'malicious_prefixes': set(),
                'malicious_ips': set()
            }

            reader = csv.DictReader(response.text.strip().splitlines())
            for row in reader:
                raw_entry = {
                    'timestamp': row.get('timestamp'),
                    'network': row.get('network'),
                    'num_events': row.get('num_events'),
                    'country_code': row.get('country_code'),
                    'asn': row.get('asn'),
                    'thving_score': row.get('thving_score')
                }
                data['raw'].append(raw_entry)

                if row.get('asn'):
                    data['malicious_asns'].add(row['asn'])
                if row.get('network'):
                    data['malicious_prefixes'].add(row['network'])
                if row.get('ip_address'):
                    data['malicious_ips'].add(row['ip_address'])

            with open(self.cymru_cache, 'w') as f:
                json.dump({
                    k: list(v) if isinstance(v, set) else v
                    for k, v in data.items()
                }, f)

            logger.info(f"Cymru fetched: {len(data['malicious_asns'])} ASNs, "
                       f"{len(data['malicious_prefixes'])} prefixes")
            return data

        except Exception as e:
            logger.error(f"Failed to fetch Cymru data: {e}")
            return None

    def fetch_alphamountain_data(self) -> Optional[Dict]:
        """Fetch alphaMountain domain threat data"""
        try:
            url = "https://files.alphamountain.ai/alphaMountain-community-threat-1000.csv"
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            if response.status_code != 200:
                return None

            data = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'malicious_domains': set(),
                'domain_risk_scores': {}
            }

            reader = csv.DictReader(response.text.strip().splitlines())
            for row in reader:
                domain = row.get('hostname')
                risk_score = row.get('risk_score')
                if domain:
                    data['malicious_domains'].add(domain)
                    if risk_score:
                        data['domain_risk_scores'][domain] = float(risk_score)

            with open(self.alphamountain_cache, 'w') as f:
                json.dump({
                    'timestamp': data['timestamp'],
                    'malicious_domains': list(data['malicious_domains']),
                    'domain_risk_scores': data['domain_risk_scores']
                }, f)

            logger.info(f"AlphaMountain fetched: {len(data['malicious_domains'])} domains")
            return data

        except Exception as e:
            logger.error(f"Failed to fetch AlphaMountain data: {e}")
            return None

    def resolve_domain_to_ip(self, domain: str) -> List[str]:
        """
        Resolve domain to IP addresses (multiple A records)
        Note: This may fail if DNS is blocked by network
        """
        if domain in self.domain_ip_cache:
            return self.domain_ip_cache[domain]

        try:
            # Try using dnspython for DNS resolution
            try:
                resolver = dns.resolver.Resolver()
                answers = resolver.resolve(domain, 'A')
                ips = [rdata.address for rdata in answers]
            except:
                # Fallback to standard socket
                ip = socket.gethostbyname(domain)
                ips = [ip]

            self.domain_ip_cache[domain] = ips
            return ips
        except Exception as e:
            logger.debug(f"Failed to resolve {domain}: {e}")
            return []

    def prefix_contains_ip(self, prefix: str, ip: str) -> bool:
        """Check if an IP falls within a network prefix"""
        try:
            network = ipaddress.ip_network(prefix, strict=False)
            ip_obj = ipaddress.ip_address(ip)
            return ip_obj in network
        except Exception as e:
            logger.debug(f"Failed to check prefix {prefix} against IP {ip}: {e}")
            return False

    def check_virustotal(self, domain: str) -> Optional[Dict]:
        """Check domain reputation using VirusTotal API"""
        if not self.virustotal_api_key:
            return None

        # Check recent cache
        if domain in self.virustotal_recent:
            cache_time = self.virustotal_recent[domain]['timestamp']
            if (datetime.now() - cache_time).total_seconds() < 60:
                return self.virustotal_recent[domain]['data']

        try:
            url = f"https://www.virustotal.com/api/v3/domains/{domain}"
            headers = {
                "x-apikey": self.virustotal_api_key
            }
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                vt_result = {
                    'id': data.get('id'),
                    'attributes': data.get('attributes', {})
                }
                # Cache result
                self.virustotal_recent[domain] = {
                    'timestamp': datetime.now(),
                    'data': vt_result
                }
                return vt_result
            else:
                logger.debug(f"VirusTotal API returned {response.status_code} for {domain}")
                return None
        except Exception as e:
            logger.debug(f"Failed to check {domain} on VirusTotal: {e}")
            return None

    def domain_has_malicious_rep(self, vt_data: Optional[Dict]) -> bool:
        """Check if domain has malicious reputation"""
        if not vt_data:
            return False

        attributes = vt_data.get('attributes', {})
        stats = attributes.get('last_analysis_stats', {})

        # If a domain is detected as malicious, it's suspicious
        return stats.get('malicious', 0) > 0 or stats.get('suspicious', 0) > 0

    def cross_reference_with_bgp(self, bgp_data: List[Dict],
                                 cymru_data: Optional[Dict],
                                 alphamountain_data: Optional[Dict],
                                 virustotal_cache: Optional[Dict] = None) -> List[Dict]:
        """Cross-reference BGP data against threat intelligence"""
        matched_events = []
        logger.info(f"Cross-referencing {len(bgp_data)} BGP events against threat intel")

        # Index domain threat data by IP for quick lookup
        domain_by_ip = {}  # IP -> set of domains
        domain_risk_scores = alphamountain_data.get('domain_risk_scores', {}) if alphamountain_data else {}

        for domain in alphamountain_data.get('malicious_domains', set()) if alphamountain_data else set():
            risk_score = domain_risk_scores.get(domain, 0)
            for ip in self.resolve_domain_to_ip(domain):
                if ip:
                    if ip not in domain_by_ip:
                        domain_by_ip[ip] = set()
                    domain_by_ip[ip].add((domain, risk_score))

        logger.info(f"Resolved {len(domain_by_ip)} unique IPs from threat domains")

        for bgp_event in bgp_data:
            prefix = bgp_event.get('prefix', '')
            origin = bgp_event.get('origin', '')
            risk_level = 'LOW'
            risk_reasons = []
            source = 'bgp'

            # Check Cymru ASN/Prefix threats
            if cymru_data:
                if origin in cymru_data.get('malicious_asns', set()):
                    risk_level = 'HIGH'
                    risk_reasons.append("Malicious ASN (Cymru Top 100)")
                    source = 'cymru'

                if prefix in cymru_data.get('malicious_prefixes', set()):
                    if risk_level != 'HIGH':
                        risk_level = 'CRITICAL'
                    risk_reasons.append("Malicious prefix (Cymru Top 100)")
                    source = 'cymru'

            # Check AlphaMountain domain threats + VirusTotal
            if alphamountain_data:
                # Extract IP from prefix if it's a specific host
                if '/' in prefix and prefix.split('/')[-1].isdigit():
                    # This might be a /32 or /24 network
                    try:
                        network = ipaddress.ip_network(prefix)
                        for ip in network:
                            if str(ip) in domain_by_ip:
                                for (domain, risk_score) in domain_by_ip[str(ip)]:
                                    # Enhanced check with VirusTotal
                                    vt_data = self.check_virustotal(domain)
                                    if self.domain_has_malicious_rep(vt_data):
                                        if risk_level not in ['CRITICAL', 'HIGH']:
                                            risk_level = 'MEDIUM'
                                        risk_reasons.append(f"Domain {domain} ({risk_score}/10) -> IP {str(ip)} in {prefix} (VT: Malicious)")
                                        source = 'alphamountain+virustotal'
                                    else:
                                        if risk_level == 'LOW':
                                            risk_level = 'LOW-MEDIUM'
                                        risk_reasons.append(f"Domain {domain} ({risk_score}/10) -> IP {str(ip)} in {prefix}")
                                        source = 'alphamountain'
                    except Exception as e:
                        logger.debug(f"Failed to analyze prefix {prefix}: {e}")

            if risk_level != 'LOW':
                matched_events.append({
                    'event': bgp_event,
                    'risk_level': risk_level,
                    'risk_reasons': risk_reasons,
                    'threat_source': source
                })

        return matched_events

    def load_cached_data(self, cache_file: str) -> Optional[Dict]:
        """Load cached threat data if still valid"""
        try:
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    data = json.load(f)

                cache_time = datetime.fromisoformat(data['timestamp']).replace(tzinfo=timezone.utc)
                age = (datetime.now(timezone.utc) - cache_time).total_seconds()

                if age < self.cache_age:
                    logger.info(f"Using cached {cache_file.split('/')[-1]} ({age/3600:.1f}h old)")
                    # Convert lists back to sets
                    if 'malicious_asns' in data:
                        data['malicious_asns'] = set(data['malicious_asns'])
                    if 'malicious_prefixes' in data:
                        data['malicious_prefixes'] = set(data['malicious_prefixes'])
                    if 'malicious_ips' in data:
                        data['malicious_ips'] = set(data['malicious_ips'])
                    if 'malicious_domains' in data:
                        data['malicious_domains'] = set(data['malicious_domains'])
                    return data
                else:
                    logger.info(f"Cache expired: {cache_file}")
        except Exception as e:
            logger.error(f"Failed to load cached data: {e}")

        return None

    def fetch_threat_data(self) -> Tuple[Optional[Dict], Optional[Dict]]:
        """Get threat data from both sources"""
        # Try Cymru cache first
        cymru_cached = self.load_cached_data(self.cymru_cache)
        if cymru_cached:
            cymru_data = cymru_cached
        else:
            cymru_data = self.fetch_cymru_data()

        # Try AlphaMountain cache first
        alphamountain_cached = self.load_cached_data(self.alphamountain_cache)
        if alphamountain_cached:
            alphamountain_data = alphamountain_cached
        else:
            alphamountain_data = self.fetch_alphamountain_data()

        return cymru_data, alphamountain_data

    def cross_reference_with_bgp(self, bgp_data: List[Dict],
                                 cymru_data: Optional[Dict],
                                 alphamountain_data: Optional[Dict]) -> List[Dict]:
        """Cross-reference BGP data against threat intelligence"""
        matched_events = []
        logger.info(f"Cross-referencing {len(bgp_data)} BGP events against threat intel")

        for bgp_event in bgp_data:
            prefix = bgp_event.get('prefix', '')
            origin = bgp_event.get('origin', '')
            risk_level = 'LOW'
            risk_reasons = []
            source = 'bgp'

            # Check Cymru ASN/Prefix threats
            if cymru_data:
                if origin in cymru_data.get('malicious_asns', set()):
                    risk_level = 'HIGH'
                    risk_reasons.append("Malicious ASN (Cymru Top 100)")
                    source = 'cymru'

                if prefix in cymru_data.get('malicious_prefixes', set()):
                    if risk_level != 'HIGH':
                        risk_level = 'CRITICAL'
                    risk_reasons.append("Malicious prefix (Cymru Top 100)")
                    source = 'cymru'

            # Check AlphaMountain domain threats
            if alphamountain_data:
                # This requires domain resolution - limited by DNS capability
                # For now, we'll log this as a potential future enhancement
                pass

            if risk_level != 'LOW':
                matched_events.append({
                    'event': bgp_event,
                    'risk_level': risk_level,
                    'risk_reasons': risk_reasons,
                    'threat_source': source
                })

        return matched_events

    def generate_threat_report(self, bgp_data: List[Dict],
                               cymru_data: Optional[Dict],
                               alphamountain_data: Optional[Dict],
                               virustotal_cache: Optional[Dict] = None) -> Dict:
        """Generate comprehensive threat intelligence report"""
        matched = self.cross_reference_with_bgp(bgp_data, cymru_data, alphamountain_data)

        high_risk = [e for e in matched if e['risk_level'] in ['HIGH', 'CRITICAL']]

        unique_malicious_asns = set()
        unique_malicious_prefixes = set()
        threat_sources = set()

        for event in matched:
            if 'Malicious ASN' in event['risk_reasons']:
                unique_malicious_asns.add(event['event']['origin'])
            if 'Malicious prefix' in event['risk_reasons']:
                unique_malicious_prefixes.add(event['event']['prefix'])
            threat_sources.add(event['threat_source'])

        report = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'threat_sources': list(threat_sources),
            'summary': {
                'total_bgp_events': len(bgp_data),
                'matched_threats': len(matched),
                'high_risk_events': len(high_risk),
                'unique_malicious_asns_seen': len(unique_malicious_asns),
                'unique_malicious_prefixes_seen': len(unique_malicious_prefixes)
            },
            'high_risk_events': [
                {
                    'prefix': e['event']['prefix'],
                    'origin': e['event']['origin'],
                    'risk_level': e['risk_level'],
                    'reasons': e['risk_reasons'],
                    'source': e['threat_source']
                }
                for e in high_risk[:20]
            ],
            'threat_intelligence': {
                'cymru_feed': {
                    'available': cymru_data is not None,
                    'malicious_asns_count': len(cymru_data.get('malicious_asns', set())) if cymru_data else 0,
                    'malicious_prefixes_count': len(cymru_data.get('malicious_prefixes', set())) if cymru_data else 0
                },
                'alphamountain_feed': {
                    'available': alphamountain_data is not None,
                    'malicious_domains_count': len(alphamountain_data.get('malicious_domains', set())) if alphamountain_data else 0
                },
                'asns_seen_in_bgp': list(unique_malicious_asns),
                'prefixes_seen_in_bgp': list(unique_malicious_prefixes)
            }
        }

        return report

    def run_integration(self, bgp_data: List[Dict]) -> Dict:
        """Run complete threat intelligence integration"""
        logger.info("Starting hybrid threat intelligence integration")

        cymru_data, alphamountain_data = self.fetch_threat_data()

        if not cymru_data and not alphamountain_data:
            logger.error("No threat data available. Skipping integration.")
            return {}

        report = self.generate_threat_report(bgp_data, cymru_data, alphamountain_data)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(self.monitoring_dir, f"threat_report_{timestamp}.json")

        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Threat intelligence report saved to {report_file}")

        print(f"\n{'='*60}")
        print("HYBRID THREAT INTELLIGENCE INTEGRATION SUMMARY")
        print(f"{'='*60}")
        print(f"Total BGP events analyzed: {report['summary']['total_bgp_events']}")
        print(f"Threat matches: {report['summary']['matched_threats']}")
        print(f"High risk events: {report['summary']['high_risk_events']}")
        print(f"Malicious ASNs seen in BGP: {report['summary']['unique_malicious_asns_seen']}")
        print(f"Malicious prefixes seen in BGP: {report['summary']['unique_malicious_prefixes_seen']}")
        print(f"Threat sources: {', '.join(report['threat_sources'])}")
        print(f"Cymru data available: {report['threat_intelligence']['cymru_feed']['available']}")
        print(f"AlphaMountain data available: {report['threat_intelligence']['alphamountain_feed']['available']}")
        print(f"{'='*60}\n")

        return report

    def test_threat_data_connection(self):
        """Test connectivity to threat data sources"""
        print("\nTesting threat data sources...\n")

        # Test Cymru
        try:
            response = requests.get(
                "https://raw.githubusercontent.com/team-cymru/Community-Top-100/master/top100.csv",
                timeout=10
            )
            if response.status_code == 200:
                print("✅ Team Cymru GitHub mirror is accessible")
            else:
                print(f"❌ Team Cymru GitHub returned status {response.status_code}")
        except Exception as e:
            print(f"❌ Team Cymru GitHub connection failed: {e}")

        # Test AlphaMountain
        try:
            response = requests.get(
                "https://files.alphamountain.ai/alphaMountain-community-threat-1000.csv",
                timeout=10
            )
            if response.status_code == 200:
                print("✅ AlphaMountain threat feed is accessible")
            else:
                print(f"❌ AlphaMountain returned status {response.status_code}")
        except Exception as e:
            print(f"❌ AlphaMountain connection failed: {e}")

        # Test VirusTotal
        if self.virustotal_api_key:
            try:
                url = "https://www.virustotal.com/api/v3/domains/google.com"
                headers = {"x-apikey": self.virustotal_api_key}
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    print("✅ VirusTotal API is accessible")
                else:
                    print(f"❌ VirusTotal API returned status {response.status_code}")
            except Exception as e:
                print(f"❌ VirusTotal connection failed: {e}")
        else:
            print("❌ VirusTotal API key not configured")

        print()


def setup_cron_jobs():
    """Set up automated cron jobs for security monitoring"""
    import subprocess

    print("\n🤖 Setting up automation...")

    cron_job_file = """
# BGP Security Monitoring Automation
# Generated: {timestamp}

# Run BGP monitoring every 6 hours
0 */6 * * * /usr/bin/python3 /Users/mitchparker/.openclaw/workspace/research/bgp_monitoring/bgp_hijack_monitor_v2.py >> /Users/mitchparker/.openclaw/workspace/research/bgp_monitoring/logs/bgp_monitor.log 2>&1

# Run threat intelligence integration daily at 2 AM
0 2 * * * /usr/bin/python3 /Users/mitchparker/.openclaw/workspace/research/bgp_monitoring/integrate_threat_intel.py >> /Users/mitchparker/.openclaw/workspace/research/bgp_monitoring/logs/threat_intel.log 2>&1

# Generate security dashboard every 6 hours
0 */6 * * * /usr/bin/python3 /Users/mitchparker/.openclaw/workspace/research/bgp_monitoring/generate_security_dashboard.py >> /Users/mitchparker/.openclaw/workspace/research/bgp_monitoring/logs/dashboard.log 2>&1
"""

    # Create logs directory
    logs_dir = "/Users/mitchparker/.openclaw/workspace/research/bgp_monitoring/logs"
    os.makedirs(logs_dir, exist_ok=True)

    # Write cron job file
    cron_path = "/Users/mitchparker/.openclaw/workspace/research/bgp_monitoring/cron_jobs.txt"
    with open(cron_path, 'w') as f:
        f.write(cron_job_file.format(timestamp=datetime.now().isoformat()))

    print(f"✅ Cron jobs configuration written to {cron_path}")
    print("\nTo install these cron jobs, run:")
    print(f"  crontab {cron_path}")
    print("\n⚠️  This will replace your existing crontab.")
    print("Review the file first and consider:")
    print("  - Adding to existing crontab instead of replacing")
    print("  - Adjusting the schedule to your needs")
    print("  - Adding a database cleanup job")


if __name__ == "__main__":
    import subprocess
    import sys

    # Parse command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--automation":
        setup_cron_jobs()
        sys.exit(0)

    # Set the monitoring data directory directly
    monitoring_dir = "/Users/mitchparker/.openclaw/workspace/research/bgp_monitoring/monitoring_data"

    logger.info(f"Looking for BGP reports in {monitoring_dir}...")

    reports = sorted(
        [f for f in os.listdir(monitoring_dir) if f.startswith("bgp_report_") and f.endswith(".json")],
        key=lambda x: x
    )

    if reports:
        # Pick the report with the most events (most recent comprehensive run)
        best_report = None
        max_events = 0
        for report in reports:
            report_path = os.path.join(monitoring_dir, report)
            try:
                with open(report_path, 'r') as f:
                    data = json.load(f)
                
                if 'hijacks_by_risk' in data:
                    event_count = sum(len(items) for items in data['hijacks_by_risk'].values())
                else:
                    event_count = len(data.get('analysis', []))
                
                # Prefer reports with more events
                if event_count > max_events:
                    max_events = event_count
                    best_report = report_path
            except Exception as e:
                pass

        if best_report:
            with open(best_report, 'r') as f:
                bgp_data = json.load(f)

            if 'hijacks_by_risk' in bgp_data:
                all_hijacks = []
                for risk_level, items in bgp_data['hijacks_by_risk'].items():
                    all_hijacks.extend(items)
                bgp_data_list = all_hijacks
            else:
                bgp_data_list = bgp_data.get('analysis', [])

            # Get VirusTotal API key from environment
            virustotal_key = os.getenv("VIRUSTOTAL_API_KEY")
            integrator = HybridThreatIntelIntegrator(virustotal_api_key=virustotal_key)

            # Test threat data sources
            integrator.test_threat_data_connection()

            # Run integration
            report = integrator.run_integration(bgp_data_list)

            if report:
                # Generate dashboard
                from generate_security_dashboard import SecurityDashboard
                dashboard = SecurityDashboard(monitoring_dir)
                dashboard.save_dashboard()
                print("\n✅ Security monitoring and dashboard generation complete.")
            else:
                print("\n❌ Integration failed or no data available.")
        else:
            print("Could not find valid BGP report with events")
            sys.exit(1)
    else:
        print("No BGP reports found to analyze")
        sys.exit(1)
