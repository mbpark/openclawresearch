#!/usr/bin/env python3
"""
BGP Hijack Monitoring System v2
Monitors for BGP hijacking events using BGPStream API
"""

import subprocess
import requests
import json
import time
import ipaddress
import shlex
from datetime import datetime, timezone
from typing import Dict, List, Optional
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BGPHijackMonitorV2:
    def __init__(self):
        self.bgpstream_key = os.environ.get('BGPSTREAM_API_KEY', '')  # Would need API key for production
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

    def is_rfc1918_private(self, prefix: str) -> bool:
        """Check if a prefix is in RFC1918 private address space"""
        try:
            network = ipaddress.ip_network(prefix, strict=False)
            if network.is_private:
                return True
            return False
        except ValueError:
            return False
    
    def get_routeviews_feed(self, feed_type: str = "rib") -> List[Dict]:
        """
        Query RouteViews BGP data using bgpreader CLI (single file mode)
        """
        try:
            result = subprocess.run(['which', 'bgpreader'], capture_output=True, text=True)
            if result.returncode != 0:
                logger.error("bgpreader not found in PATH")
                return []
            
            # Try to get recent RouteViews data - local file mode
            current_date = datetime.now().strftime('%Y%m%d')
            base_path = f"https://archive.routeviews.org/route-views5/bgpdata/{datetime.now().strftime('%Y.%m')}/RIBS/rib.{current_date}.1400.bz2"
            
            # First try today's data, then yesterday, then 2 days ago
            dates_to_try = [
                (0, current_date),
                (1, (datetime.now().replace(day=datetime.now().day-1)).strftime('%Y%m%d')),
                (2, (datetime.now().replace(day=datetime.now().day-2)).strftime('%Y%m%d'))
            ]
            
            downloaded = False
            for offset, rib_date in dates_to_try:
                rib_path = f"https://archive.routeviews.org/route-views5/bgpdata/{datetime.now().strftime('%Y.%m')}/RIBS/rib.{rib_date}.1400.bz2"
                local_file = f"/tmp/routeviews_{rib_date}.bz2"
                
                logger.info(f"Downloading RouteViews RIB (offset={offset}d): {rib_path}")
                
                download_result = subprocess.run(
                    ['curl', '-s', '--connect-timeout', '10', '-o', local_file, rib_path],
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                
                if download_result.returncode == 0 and os.path.exists(local_file):
                    logger.info(f"Successfully downloaded {local_file}")
                    cmd = [
                        'bgpreader',
                        '-d', 'singlefile',
                        '-o', 'rib-file=' + local_file,
                        '-n', '100',
                        '-e',
                        '-i'
                    ]
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if result.returncode == 0 and result.stdout.strip():
                        logger.info(f"RouteViews data retrieved: {len(self.parse_bgpreader_output(result.stdout))} prefixes")
                        downloaded = True
                        return self.parse_bgpreader_output(result.stdout)
                    else:
                        logger.warning(f"bgpreader failed: {result.stderr}")
                        # Clean up failed file
                        try:
                            os.remove(local_file)
                        except:
                            pass
            
            if not downloaded:
                logger.warning("All RouteViews RIB downloads failed")
            
            return []

        except Exception as e:
            logger.error(f"Error fetching RouteViews data via bgpreader: {e}")
            return []
    
    def parse_bgpreader_output(self, output: str) -> List[Dict]:
        """
        Parse bgpreader output (bgpdump -m format)
        """
        prefixes = []
        
        for line in output.splitlines():
            line = line.strip()
            
            # Skip header lines
            if line.startswith('#') or not line:
                continue
            
            # Check for R|R lines (RIB announcements)
            # Format: R|R|timestamp|project|collector|router|router-ip|peer-ASN|peer-IP|prefix|next-hop-IP|AS-path|origin-AS|communities|old-state|new-state
            if line.startswith('R|R|'):
                parts = line.split('|')
                if len(parts) >= 13:
                    try:
                        timestamp = int(parts[2].split('.')[0])
                        prefix = parts[9]
                        origin = parts[12]
                        
                        # Validate and store prefix
                        if self.is_valid_ip_prefix(prefix):
                            prefixes.append({
                                'prefix': prefix,
                                'origin': origin,
                                'timestamp': timestamp,
                                'status': 'active'
                            })
                    except (ValueError, IndexError) as e:
                        logger.debug(f"Error parsing R|R line: {e}")
        
        return prefixes
    
    def is_valid_ip_prefix(self, prefix: str) -> bool:
        """Validate that the prefix is a valid IP network"""
        try:
            ipaddress.ip_network(prefix, strict=False)
            return True
        except ValueError:
            return False
    
    def get_ripe_ris_feed(self, feed_type: str = "rib") -> List[Dict]:
        """
        Query RIPE RIS (Routing Information Service) for BGP data using local file mode
        """
        try:
            result = subprocess.run(['which', 'bgpreader'], capture_output=True, text=True)
            if result.returncode != 0:
                logger.error("bgpreader not found in PATH")
                return []
            
            # Try recent RIPE RIS data
            current_date = datetime.now().strftime('%Y%m%d')
            dates_to_try = [
                (0, current_date),
                (1, (datetime.now().replace(day=datetime.now().day-1)).strftime('%Y%m%d')),
                (2, (datetime.now().replace(day=datetime.now().day-2)).strftime('%Y%m%d'))
            ]
            
            downloaded = False
            for offset, rib_date in dates_to_try:
                rib_path = f"https://archive.ripe.org/ripensbgp/rib.{rib_date}.1400.bz2"
                local_file = f"/tmp/ripe_ris_{rib_date}.bz2"
                
                logger.info(f"Downloading RIPE RIS RIB (offset={offset}d): {rib_path}")
                
                download_result = subprocess.run(
                    ['curl', '-s', '--connect-timeout', '10', '-o', local_file, rib_path],
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                
                if download_result.returncode == 0 and os.path.exists(local_file):
                    logger.info(f"Successfully downloaded {local_file}")
                    cmd = [
                        'bgpreader',
                        '-d', 'singlefile',
                        '-o', 'rib-file=' + local_file,
                        '-n', '100',
                        '-e',
                        '-i'
                    ]
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if result.returncode == 0 and result.stdout.strip():
                        logger.info(f"RIPE RIS data retrieved: {len(self.parse_bgpreader_output(result.stdout))} prefixes")
                        downloaded = True
                        return self.parse_bgpreader_output(result.stdout)
                    else:
                        logger.warning(f"bgpreader failed: {result.stderr}")
                        try:
                            os.remove(local_file)
                        except:
                            pass
            
            if not downloaded:
                logger.warning("All RIPE RIS RIB downloads failed")
            
            return []

        except Exception as e:
            logger.error(f"Error fetching RIPE RIS data: {e}")
            return []
    
    def get_bgpview_feed(self, feed_type: str = "prefixes") -> List[Dict]:
        """
        Query BGPView API for BGP data (public API, lightweight)
        """
        try:
            # Try BGPView main API - get prefixes
            response = requests.get(
                "https://api.bgpview.io/prefixes",
                params={'limit': 100, 'is_unallocated': 'false'},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            prefixes = []
            if 'data' in data and isinstance(data['data'], list):
                for item in data['data']:
                    if 'prefix' in item and 'asn' in item:
                        prefixes.append({
                            'prefix': item['prefix'],
                            'origin': str(item['asn']),
                            'timestamp': datetime.now(timezone.utc).isoformat(),
                            'status': 'active',
                            'source': 'bgpview',
                            'description': item.get('description'),
                            'rir': item.get('rir')
                        })
            
            if prefixes:
                logger.info(f"BGPView prefixes retrieved {len(prefixes)} prefixes")
                return prefixes
            
            # Try BGPView bogons endpoint as fallback
            try:
                response = requests.get(
                    "https://api.bgpview.io/bogons",
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()
                
                prefixes = []
                if 'data' in data and isinstance(data['data'], list):
                    for item in data['data']:
                        if 'prefix' in item and 'asn' in item:
                            prefixes.append({
                                'prefix': item['prefix'],
                                'origin': str(item['asn']),
                                'timestamp': datetime.now(timezone.utc).isoformat(),
                                'status': 'bogon',
                                'source': 'bgpview_bogons'
                            })
                
                if prefixes:
                    logger.info(f"BGPView bogons endpoint retrieved {len(prefixes)} prefixes")
                return prefixes
                
            except Exception as fallback_error:
                logger.warning(f"BGPView fallback failed: {fallback_error}")
                return []

        except Exception as e:
            logger.error(f"Error fetching BGPView data: {e}")
            return []
    
    def get_bgpstream_feed(self, feed_type: str = "prefixes") -> List[Dict]:
        """
        Query BGPStream API for BGP data
        """
        try:
            # Use BGPStream API (requires API key for production)
            # For demonstration, we'll use a sample dataset
            response = requests.get(
                f"https://bgpstream.com/feed/{feed_type}",
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            return data.get('feed', [])

        except Exception as e:
            logger.error(f"Error fetching BGPStream data: {e}")
            return []

    def simulate_bgp_hijack_data(self) -> List[Dict]:
        """
        Generate sample BGP hijack data for demonstration
        """
        # Sample hijack events for demonstration - using PUBLIC IP ranges only
        sample_hijacks = [
            {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'destination': 'RIPE NCC',
                'origin': 'AS12345',
                'prefix': '203.0.113.0/24',  # Documentation range (PUBLIC)
                'details': {
                    'legit_owner': 'AS12345',
                    'expected_origin': 'AS65432',
                    'detection_method': 'community_bgpmon',
                    'severity': 'high'
                },
                'analyst_generated': False,
                'status': 'ongoing'
            },
            {
                'timestamp': (datetime.now(timezone.utc).timestamp() - 3600),
                'destination': 'ARIN',
                'origin': 'AS99999',
                'prefix': '198.51.100.0/16',  # Documentation range (PUBLIC)
                'details': {
                    'legit_owner': 'AS11111',
                    'expected_origin': 'AS11111',
                    'detection_method': 'manual',
                    'severity': 'medium'
                },
                'analyst_generated': True,
                'status': 'resolved'
            },
            {
                'timestamp': (datetime.now(timezone.utc).timestamp() - 7200),
                'destination': 'LACNIC',
                'origin': 'AS55555',
                'prefix': '192.0.2.0/24',  # Documentation range (PUBLIC)
                'details': {
                    'legit_owner': 'AS22222',
                    'expected_origin': 'AS22222',
                    'detection_method': 'community_bgpmon',
                    'severity': 'low'
                },
                'analyst_generated': False,
                'status': 'resolved'
            }
        ]

        return sample_hijacks

    def get_bgp_hijacks(self) -> List[Dict]:
        """
        Get BGP hijack data (try real APIs, fallback to simulation)
        """
        all_hijacks = []
        
        # Try RouteViews with bgpreader first (free, open source)
        try:
            routeviews_hijacks = self.get_routeviews_feed()
            if routeviews_hijacks:
                logger.info(f"Retrieved {len(routeviews_hijacks)} BGP events from RouteViews (via bgpreader)")
                all_hijacks.extend(routeviews_hijacks)
        except Exception as e:
            logger.warning(f"RouteViews/bgpreader failed: {e}")
        
        # Try RIPE RIS with bgpreader (free, open source, European coverage)
        try:
            ripe_ris_hijacks = self.get_ripe_ris_feed()
            if ripe_ris_hijacks:
                logger.info(f"Retrieved {len(ripe_ris_hijacks)} BGP events from RIPE RIS (via bgpreader)")
                all_hijacks.extend(ripe_ris_hijacks)
        except Exception as e:
            logger.warning(f"RIPE RIS/bgpreader failed: {e}")
        
        # Try BGPView API for lightweight enrichment (public API)
        try:
            bgpview_hijacks = self.get_bgpview_feed()
            if bgpview_hijacks:
                logger.info(f"Retrieved {len(bgpview_hijacks)} BGP events from BGPView API")
                all_hijacks.extend(bgpview_hijacks)
        except Exception as e:
            logger.warning(f"BGPView API failed: {e}")
        
        # Filter out private IP ranges if we have data
        if all_hijacks:
            filtered_hijacks = []
            for hijack in all_hijacks:
                prefix = hijack.get('prefix', '')
                if not self.is_rfc1918_private(prefix):
                    filtered_hijacks.append(hijack)
                else:
                    logger.debug(f"Skipping private prefix {prefix}")
            
            logger.info(f"Retrieved {len(filtered_hijacks)} BGP events from all sources (after filtering private ranges)")
            return filtered_hijacks

        # Fall back to simulated data
        logger.info("No real API data available. Using simulated BGP hijack data for demonstration")
        return self.simulate_bgp_hijack_data()

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

        # Check severity
        severity = hijack.get('details', {}).get('severity', 'low')
        if severity == 'high':
            risk_score += 25
            risk_factors.append("high_severity")
        elif severity == 'medium':
            risk_score += 15
            risk_factors.append("medium_severity")

        # Check origin AS
        origin = hijack.get('origin', '')
        if self._is_suspicious_origin(origin):
            risk_score += 20
            risk_factors.append("suspicious_origin")

        return {
            'risk_score': risk_score,
            'risk_level': self._get_risk_level(risk_score),
            'risk_factors': risk_factors
        }

    def _is_suspicious_origin(self, origin: str) -> bool:
        """Check if origin AS is suspicious"""
        suspicious_as = ['AS0', 'AS23456', 'AS65535']
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
        logger.info(f"Found {len(hijacks)} BGP hijack events")

        # Generate and save report
        report = self.generate_report(hijacks)
        report_file = self.save_report(report)

        # Update last check timestamp
        self.save_last_check(datetime.now(timezone.utc).isoformat())

        # Log summary
        logger.info(f"Monitoring cycle complete. Found {len(hijacks)} hijacks.")
        logger.info(f"Ongoing hijacks: {len(report['hijacks_by_status']['ongoing'])}")
        logger.info(f"Critical risk hijacks: {len(report['hijacks_by_risk']['CRITICAL'])}")

        return report

    def create_summary(self, report: Dict) -> str:
        """Create a human-readable summary of the report"""
        summary = f"""
BGP HIJACK MONITORING REPORT
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

SUMMARY:
- Total Hijacks Found: {report['total_hijacks']}
- Ongoing Hijacks: {len(report['hijacks_by_status']['ongoing'])}
- Resolved Hijacks: {len(report['hijacks_by_status']['resolved'])}

RISK DISTRIBUTION:
- CRITICAL: {len(report['hijacks_by_risk']['CRITICAL'])} hijacks
- HIGH: {len(report['hijacks_by_risk']['HIGH'])} hijacks
- MEDIUM: {len(report['hijacks_by_risk']['MEDIUM'])} hijacks
- LOW: {len(report['hijacks_by_risk']['LOW'])} hijacks
- MINIMAL: {len(report['hijacks_by_risk']['MINIMAL'])} hijacks

DETAILED FINDINGS:
"""

        for analysis in report['analysis']:
            summary += f"""
Prefix: {analysis['prefix']}
  Origin AS: {analysis['origin']}
  Risk Level: {analysis['risk_level']} (Score: {analysis['risk_score']})
  Factors: {', '.join(analysis['factors'])}
"""

        return summary

def main():
    """Main monitoring loop"""
    monitor = BGPHijackMonitorV2()

    logger.info("BGP Hijack Monitor v2 starting...")

    try:
        report = monitor.run_monitoring_cycle()

        # Print summary
        print("\n" + "="*60)
        print(monitor.create_summary(report))
        print("\n" + "="*60)

    except Exception as e:
        logger.error(f"Monitoring cycle failed: {e}")
        raise

if __name__ == "__main__":
    main()
