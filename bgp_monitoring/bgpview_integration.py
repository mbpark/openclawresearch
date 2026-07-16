#!/usr/bin/env python3
"""
BGPView API Integration Script
Tests BGPView API connectivity and retrieves data
"""

import requests
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BGPViewIntegration:
    def __init__(self):
        self.base_url = "https://api.bgpview.io"
        self.api_key = os.environ.get('BGPVIEW_API_KEY', '')
        
    def test_connection(self) -> bool:
        """Test BGPView API connectivity"""
        try:
            response = requests.get(f"{self.base_url}/prefixes", timeout=10)
            if response.status_code == 200:
                logger.info("BGPView API connection successful")
                return True
            else:
                logger.warning(f"BGPView API returned status {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"BGPView API connection failed: {e}")
            return False
    
    def get_prefixes(self, limit: int = 100) -> List[Dict]:
        """Get BGP prefixes from BGPView"""
        try:
            params = {
                'limit': limit,
                'is_unallocated': 'false'
            }
            
            if self.api_key:
                params['apikey'] = self.api_key
            
            response = requests.get(
                f"{self.base_url}/prefixes",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            prefixes = []
            if 'data' in data and isinstance(data['data'], list):
                for item in data['data']:
                    try:
                        prefix_entry = {
                            'prefix': item.get('prefix'),
                            'origin': str(item.get('asn')),
                            'timestamp': datetime.now(timezone.utc).isoformat(),
                            'status': 'active',
                            'source': 'bgpview',
                            'description': item.get('description'),
                            'rir': item.get('rir'),
                            'is_connected': item.get('is_connected', False)
                        }
                        prefixes.append(prefix_entry)
                    except (KeyError, TypeError):
                        continue
            
            logger.info(f"Retrieved {len(prefixes)} prefixes from BGPView")
            return prefixes
            
        except Exception as e:
            logger.error(f"Failed to fetch BGPView prefixes: {e}")
            return []
    
    def get_asn_info(self, asn: str) -> Optional[Dict]:
        """Get AS information from BGPView"""
        try:
            response = requests.get(
                f"{self.base_url}/asn/{asn}",
                timeout=20
            )
            response.raise_for_status()
            data = response.json()
            return data.get('data', {})
        except Exception as e:
            logger.error(f"Failed to get AS info for {asn}: {e}")
            return None
    
    def get_bogons(self) -> List[Dict]:
        """Get bogon prefixes from BGPView"""
        try:
            response = requests.get(
                f"{self.base_url}/bogons",
                timeout=20
            )
            response.raise_for_status()
            data = response.json()
            
            bogons = []
            if 'data' in data and isinstance(data['data'], list):
                for item in data['data']:
                    try:
                        bogon_entry = {
                            'prefix': item.get('prefix'),
                            'origin': str(item.get('asn')),
                            'timestamp': datetime.now(timezone.utc).isoformat(),
                            'status': 'bogon',
                            'source': 'bgpview_bogons'
                        }
                        bogons.append(bogon_entry)
                    except (KeyError, TypeError):
                        continue
            
            logger.info(f"Retrieved {len(bogons)} bogon prefixes from BGPView")
            return bogons
            
        except Exception as e:
            logger.error(f"Failed to fetch BGPView bogons: {e}")
            return []
    
    def run_full_integration(self):
        """Run comprehensive BGPView integration test"""
        logger.info("Starting BGPView integration test")
        
        # Test connection
        connection_ok = self.test_connection()
        if not connection_ok:
            logger.warning("BGPView API is not accessible. Skipping integration.")
            return {}
        
        # Get prefixes
        prefixes = self.get_prefixes(limit=50)
        
        # Get bogons
        bogons = self.get_bogons()
        
        # Sample AS info
        if prefixes:
            sample_asn = prefixes[0].get('origin')
            asn_info = self.get_asn_info(sample_asn) if sample_asn else None
        else:
            asn_info = None
        
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'connection_status': 'success' if connection_ok else 'failed',
            'prefixes': prefixes,
            'bogons': bogons,
            'sample_asn_info': asn_info,
            'stats': {
                'total_prefixes': len(prefixes),
                'total_bogons': len(bogons)
            }
        }

if __name__ == "__main__":
    integration = BGPViewIntegration()
    result = integration.run_full_integration()
    
    # Print summary
    if result:
        print(f"\n{'='*60}")
        print("BGPVIEW INTEGRATION TEST RESULTS")
        print(f"{'='*60}")
        print(f"Status: {result['connection_status']}")
        print(f"Prefixes retrieved: {result['stats']['total_prefixes']}")
        print(f"Bogons retrieved: {result['stats']['total_bogons']}")
        print(f"{'='*60}\n")
        
        # Save report
        report_file = os.path.join(
            os.path.dirname(__file__),
            "monitoring_data",
            f"bgpview_integration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        with open(report_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"Report saved to: {report_file}")
    else:
        print("BGPView integration test failed or was skipped")
