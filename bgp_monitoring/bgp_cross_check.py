#!/usr/bin/env python3
"""
BGP Cross-Check and Validation Script
Cross-validates BGP data across multiple sources and enriches with BGPView API
"""

import subprocess
import requests
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Set, Tuple
import logging
import ipaddress

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BGPCrossChecker:
    def __init__(self):
        self.monitoring_dir = os.path.join(os.path.dirname(__file__), "monitoring_data")
        os.makedirs(self.monitoring_dir, exist_ok=True)
        self.confidence_threshold = 2  # Minimum sources agreeing for high confidence

    def fetch_routeviews(self) -> List[Dict]:
        """Fetch RouteViews data using bgpreader"""
        try:
            result = subprocess.run(['which', 'bgpreader'], capture_output=True, text=True)
            if result.returncode != 0:
                logger.error("bgpreader not found in PATH")
                return []

            rib_date = datetime.now().strftime('%Y%m%d')
            rib_path = f"https://archive.routeviews.org/route-views5/bgpdata/{datetime.now().strftime('%Y.%m')}/RIBS/rib.{rib_date}.1400.bz2"
            local_file = f"/tmp/routeviews_{rib_date}.bz2"

            download_result = subprocess.run(
                ['curl', '-s', '--connect-timeout', '10', '-o', local_file, rib_path],
                capture_output=True,
                text=True,
                timeout=15
            )

            if download_result.returncode == 0 and os.path.exists(local_file):
                cmd = [
                    'bgpreader',
                    '-d', 'singlefile',
                    '-o', 'rib-file=' + local_file,
                    '-n', '50',
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
                    return self.parse_bgpreader_output(result.stdout)
                else:
                    logger.warning(f"bgpreader failed: {result.stderr}")

        except Exception as e:
            logger.error(f"RouteViews fetch error: {e}")

        return []

    def fetch_ripe_ris(self) -> List[Dict]:
        """Fetch RIPE RIS data using bgpreader"""
        try:
            result = subprocess.run(['which', 'bgpreader'], capture_output=True, text=True)
            if result.returncode != 0:
                logger.error("bgpreader not found in PATH")
                return []

            rib_date = datetime.now().strftime('%Y%m%d')
            rib_path = f"https://archive.ripe.org/ripensbgp/rib.{rib_date}.1400.bz2"
            local_file = f"/tmp/ripe_ris_{rib_date}.bz2"

            download_result = subprocess.run(
                ['curl', '-s', '--connect-timeout', '10', '-o', local_file, rib_path],
                capture_output=True,
                text=True,
                timeout=15
            )

            if download_result.returncode == 0 and os.path.exists(local_file):
                cmd = [
                    'bgpreader',
                    '-d', 'singlefile',
                    '-o', 'rib-file=' + local_file,
                    '-n', '50',
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
                    return self.parse_bgpreader_output(result.stdout)
                else:
                    logger.warning(f"bgpreader failed: {result.stderr}")

        except Exception as e:
            logger.error(f"RIPE RIS fetch error: {e}")

        return []

    def fetch_bgpview(self) -> List[Dict]:
        """Fetch BGPView API data"""
        try:
            response = requests.get(
                "https://api.bgpview.io/prefixes",
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
                            'source': 'bgpview',
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        })
            return prefixes

        except Exception as e:
            logger.error(f"BGPView fetch error: {e}")
            return []

    def parse_bgpreader_output(self, output: str) -> List[Dict]:
        """Parse bgpreader output"""
        prefixes = []

        for line in output.splitlines():
            line = line.strip()

            if line.startswith('#') or not line:
                continue

            if line.startswith('R|R|'):
                parts = line.split('|')
                if len(parts) >= 13:
                    try:
                        timestamp = int(parts[2].split('.')[0])
                        prefix = parts[9]
                        origin = parts[12]

                        if self.is_valid_ip_prefix(prefix):
                            prefixes.append({
                                'prefix': prefix,
                                'origin': origin,
                                'timestamp': timestamp,
                                'status': 'active',
                                'source': 'routeviews' if 'route-views' in line else 'ripe_ris'
                            })
                    except (ValueError, IndexError):
                        pass

        return prefixes

    def is_valid_ip_prefix(self, prefix: str) -> bool:
        """Validate IP prefix"""
        try:
            network = ipaddress.ip_network(prefix, strict=False)
            return True
        except ValueError:
            return False

    def is_rfc1918_private(self, prefix: str) -> bool:
        """Check if prefix is private"""
        try:
            network = ipaddress.ip_network(prefix, strict=False)
            return network.is_private
        except ValueError:
            return False

    def cross_check_sources(self, routeviews_data: List[Dict], ripe_ris_data: List[Dict], bgpview_data: List[Dict]) -> Dict:
        """Cross-check data across all sources"""

        # Create dictionaries keyed by prefix+origin
        prefix_origin_map = {}

        for item in routeviews_data:
            key = (item['prefix'], item['origin'])
            if key not in prefix_origin_map:
                prefix_origin_map[key] = {
                    'prefix': item['prefix'],
                    'origin': item['origin'],
                    'sources': set(),
                    'confidence': 0
                }
            prefix_origin_map[key]['sources'].add('routeviews')
            prefix_origin_map[key]['confidence'] += 1

        for item in ripe_ris_data:
            key = (item['prefix'], item['origin'])
            if key not in prefix_origin_map:
                prefix_origin_map[key] = {
                    'prefix': item['prefix'],
                    'origin': item['origin'],
                    'sources': set(),
                    'confidence': 0
                }
            prefix_origin_map[key]['sources'].add('ripe_ris')
            prefix_origin_map[key]['confidence'] += 1

        for item in bgpview_data:
            key = (item['prefix'], item['origin'])
            if key not in prefix_origin_map:
                prefix_origin_map[key] = {
                    'prefix': item['prefix'],
                    'origin': item['origin'],
                    'sources': set(),
                    'confidence': 0
                }
            prefix_origin_map[key]['sources'].add('bgpview')
            prefix_origin_map[key]['confidence'] += 1

        # Calculate confidence and categorize
        results = {
            'high_confidence': [],      # 2+ sources agree
            'medium_confidence': [],    # 1 source, but not suspicious
            'low_confidence': [],       # Only BGPView (no BGP data agreement)
            'suspicious': [],           # Suspicious patterns
            'summary': {
                'total_prefixes': len(prefix_origin_map),
                'routeviews_only': 0,
                'ripe_ris_only': 0,
                'bgpview_only': 0,
                'routeviews_ripe_ris_agreement': 0,
                'all_three_sources': 0
            }
        }

        for key, data in prefix_origin_map.items():
            source_count = len(data['sources'])
            data['source_list'] = list(data['sources'])
            # Convert set to list for JSON serialization
            data['sources'] = list(data['sources'])

            if source_count >= 2:
                data['confidence_level'] = 'HIGH'
                results['high_confidence'].append(data)
                if 'routeviews' in data['sources'] and 'ripe_ris' in data['sources']:
                    results['summary']['routeviews_ripe_ris_agreement'] += 1
                if len(data['sources']) == 3:
                    results['summary']['all_three_sources'] += 1
            elif source_count == 1:
                if 'bgpview' in data['sources']:
                    data['confidence_level'] = 'LOW'
                    results['low_confidence'].append(data)
                    results['summary']['bgpview_only'] += 1
                else:
                    data['confidence_level'] = 'MEDIUM'
                    results['medium_confidence'].append(data)
                    if 'routeviews' in data['sources']:
                        results['summary']['routeviews_only'] += 1
                    elif 'ripe_ris' in data['sources']:
                        results['summary']['ripe_ris_only'] += 1

            # Check for suspicious patterns
            if data['origin'] in ['AS0', 'AS23456', 'AS65535']:
                data['suspicious'] = True
                results['suspicious'].append(data)
            else:
                data['suspicious'] = False

        return results

    def generate_cross_check_report(self, cross_check_results: Dict) -> str:
        """Generate markdown report"""

        report = []
        report.append("# BGP Cross-Check Validation Report")
        report.append("")
        report.append(f"**Generated:** {datetime.now().isoformat()}")
        report.append("")

        summary = cross_check_results['summary']
        report.append("## Summary")
        report.append("")
        report.append(f"- **Total Prefixes Observed:** {summary['total_prefixes']}")
        report.append(f"- **High Confidence (2+ sources):** {len(cross_check_results['high_confidence'])}")
        report.append(f"- **Medium Confidence (1 BGP source):** {len(cross_check_results['medium_confidence'])}")
        report.append(f"- **Low Confidence (BGPView only):** {len(cross_check_results['low_confidence'])}")
        report.append(f"- **Suspicious Patterns:** {len(cross_check_results['suspicious'])}")
        report.append("")

        report.append("## Source Agreement")
        report.append("")
        report.append(f"- **RouteViews only:** {summary['routeviews_only']}")
        report.append(f"- **RIPE RIS only:** {summary['ripe_ris_only']}")
        report.append(f"- **BGPView only:** {summary['bgpview_only']}")
        report.append(f"- **RouteViews + RIPE RIS agreement:** {summary['routeviews_ripe_ris_agreement']}")
        report.append(f"- **All three sources:** {summary['all_three_sources']}")
        report.append("")

        report.append("## High Confidence Findings (2+ sources)")
        report.append("")
        if cross_check_results['high_confidence']:
            report.append("| Prefix | Origin AS | Sources |")
            report.append("|--------|-----------|---------|")
            for item in cross_check_results['high_confidence'][:20]:
                report.append(f"| `{item['prefix']}` | AS{item['origin']} | {', '.join(item['source_list'])} |")
            if len(cross_check_results['high_confidence']) > 20:
                report.append(f"| *...and {len(cross_check_results['high_confidence']) - 20} more* |")
        else:
            report.append("No high confidence findings.")
        report.append("")

        report.append("## Medium Confidence Findings (BGP data only)")
        report.append("")
        if cross_check_results['medium_confidence']:
            report.append("| Prefix | Origin AS | Source |")
            report.append("|--------|-----------|--------|")
            for item in cross_check_results['medium_confidence'][:20]:
                report.append(f"| `{item['prefix']}` | AS{item['origin']} | {', '.join(item['source_list'])} |")
            if len(cross_check_results['medium_confidence']) > 20:
                report.append(f"| *...and {len(cross_check_results['medium_confidence']) - 20} more* |")
        else:
            report.append("No medium confidence findings.")
        report.append("")

        report.append("## Low Confidence Findings (BGPView only)")
        report.append("")
        if cross_check_results['low_confidence']:
            report.append("| Prefix | Origin AS | Source |")
            report.append("|--------|-----------|--------|")
            for item in cross_check_results['low_confidence'][:20]:
                report.append(f"| `{item['prefix']}` | AS{item['origin']} | {', '.join(item['source_list'])} |")
            if len(cross_check_results['low_confidence']) > 20:
                report.append(f"| *...and {len(cross_check_results['low_confidence']) - 20} more* |")
        else:
            report.append("No low confidence findings.")
        report.append("")

        report.append("## Suspicious Findings")
        report.append("")
        if cross_check_results['suspicious']:
            report.append("| Prefix | Origin AS | Sources |")
            report.append("|--------|-----------|---------|")
            for item in cross_check_results['suspicious']:
                report.append(f"| `{item['prefix']}` | AS{item['origin']} | {', '.join(item['source_list'])} |")
        else:
            report.append("No suspicious patterns detected.")
        report.append("")

        return "\n".join(report)

    def run_cross_check(self):
        """Run complete cross-check workflow"""
        logger.info("Starting BGP cross-check validation...")

        # Fetch data from all sources
        routeviews_data = self.fetch_routeviews()
        logger.info(f"RouteViews: {len(routeviews_data)} prefixes")

        ripe_ris_data = self.fetch_ripe_ris()
        logger.info(f"RIPE RIS: {len(ripe_ris_data)} prefixes")

        bgpview_data = self.fetch_bgpview()
        logger.info(f"BGPView: {len(bgpview_data)} prefixes")

        # Filter out private ranges
        def filter_private(data):
            return [item for item in data if not self.is_rfc1918_private(item['prefix'])]

        routeviews_data = filter_private(routeviews_data)
        ripe_ris_data = filter_private(ripe_ris_data)
        bgpview_data = filter_private(bgpview_data)

        # Cross-check
        cross_check_results = self.cross_check_sources(routeviews_data, ripe_ris_data, bgpview_data)

        # Generate report
        report = self.generate_cross_check_report(cross_check_results)

        # Save reports
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(self.monitoring_dir, f"bgp_crosscheck_{timestamp}.md")
        json_file = os.path.join(self.monitoring_dir, f"bgp_crosscheck_{timestamp}.json")

        with open(report_file, 'w') as f:
            f.write(report)

        with open(json_file, 'w') as f:
            json.dump(cross_check_results, f, indent=2)

        logger.info(f"Cross-check report saved to {report_file}")
        logger.info(f"Cross-check data saved to {json_file}")

        # Print summary
        print(f"\n{'='*60}")
        print("BGP CROSS-CHECK SUMMARY")
        print(f"{'='*60}")
        print(f"RouteViews prefixes: {len(routeviews_data)}")
        print(f"RIPE RIS prefixes: {len(ripe_ris_data)}")
        print(f"BGPView prefixes: {len(bgpview_data)}")
        print(f"High confidence (2+ sources): {len(cross_check_results['high_confidence'])}")
        print(f"Medium confidence: {len(cross_check_results['medium_confidence'])}")
        print(f"Low confidence: {len(cross_check_results['low_confidence'])}")
        print(f"Suspicious patterns: {len(cross_check_results['suspicious'])}")
        print(f"{'='*60}\n")

        return cross_check_results

if __name__ == "__main__":
    checker = BGPCrossChecker()
    checker.run_cross_check()
