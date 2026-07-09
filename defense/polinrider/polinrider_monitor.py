#!/usr/bin/env python3
"""
PolinRider Defense - Automated Dependency Monitoring Script
Real-time monitoring of dependencies for suspicious network activity and file system changes.
"""

import os
import sys
import json
import time
import logging
import subprocess
import hashlib
import ipaddress
import socket
import threading
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Optional, Any
import argparse
import csv
import socket
import psutil
import netifaces

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('polinrider_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PolinRiderMonitor:
    def __init__(self, config_path: str = 'config.json'):
        self.config = self.load_config(config_path)
        self.alerts: List[Dict] = []
        self.file_hashes: Dict[str, str] = {}
        self.network_connections: Set[tuple] = set()
        self.lock = threading.Lock()
        self.running = True
        self.last_live_status_save = 0  # Track last save time for dashboard

        # Alert thresholds
        self.thresholds = {
            'network_connections_per_minute': self.config.get('network_connections_per_minute', 50),
            'file_changes_per_hour': self.config.get('file_changes_per_hour', 100),
            'suspicious_port_ports': [4444, 5555, 6666, 31337, 12345, 54321],
            'known_malicious_ips': self.config.get('known_malicious_ips', [])
        }

        self.database_path = 'polinrider_database.json'
        self.load_database()

    def load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file."""
        default_config = {
            'network_connections_per_minute': 50,
            'file_changes_per_hour': 100,
            'known_malicious_ips': [
                '192.168.1.100',  # Example malicious IP
                '10.0.0.1'        # Example malicious IP
            ],
            'suspicious_ports': [4444, 5555, 6666, 31337, 12345, 54321],
            'monitoring_interval': 30,
            'export_format': 'json'
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

    def load_database(self):
        """Load the research database."""
        if os.path.exists(self.database_path):
            try:
                with open(self.database_path, 'r') as f:
                    database = json.load(f)
                    self.file_hashes = database.get('file_hashes', {})
                    self.alerts = database.get('alerts', [])
                    logger.info(f"Loaded database with {len(self.file_hashes)} file hashes and {len(self.alerts)} alerts")
            except Exception as e:
                logger.error(f"Failed to load database: {e}")

    def save_database(self):
        """Save the research database."""
        try:
            with open(self.database_path, 'w') as f:
                json.dump({
                    'file_hashes': self.file_hashes,
                    'alerts': self.alerts
                }, f, indent=2)
            logger.debug("Database saved successfully")
        except Exception as e:
            logger.error(f"Failed to save database: {e}")

    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of a file."""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"Failed to hash file {file_path}: {e}")
            return ""

    def get_package_files(self, package_name: str) -> List[str]:
        """Get list of files installed by a package."""
        try:
            # Check for pip installed packages
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'show', package_name],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                # Get package location
                for line in result.stdout.split('\n'):
                    if line.startswith('Location:'):
                        package_path = line.split(':')[1].strip()
                        if os.path.exists(package_path):
                            return [os.path.join(root, file)
                                   for root, _, files in os.walk(package_path)
                                   for file in files]
        except Exception as e:
            logger.error(f"Failed to get package files for {package_name}: {e}")

        return []

    def monitor_network_connections(self) -> List[Dict]:
        """Monitor network connections for suspicious activity."""
        suspicious_connections = []

        try:
            connections = psutil.net_connections(kind='inet')

            for conn in connections:
                laddr = conn.laddr
                raddr = conn.raddr

                # Check for suspicious remote addresses
                is_suspicious = False
                reason = []

                # Check suspicious ports
                if raddr and raddr.port in self.thresholds['suspicious_port_ports']:
                    is_suspicious = True
                    reason.append(f"Connection to suspicious port {raddr.port}")

                # Check known malicious IPs
                if raddr and raddr.ip in self.thresholds['known_malicious_ips']:
                    is_suspicious = True
                    reason.append(f"Connection to known malicious IP {raddr.ip}")

                # Check for private IP ranges that shouldn't be connecting out
                try:
                    if raddr and ipaddress.ip_address(raddr.ip).is_private:
                        if not raddr.ip.startswith('192.168.') and not raddr.ip.startswith('10.'):
                            is_suspicious = True
                            reason.append(f"Connection to unexpected private IP {raddr.ip}")
                except ValueError:
                    pass

                if is_suspicious:
                    connection_info = {
                        'timestamp': datetime.now().isoformat(),
                        'protocol': conn.type.name,
                        'local_address': f"{laddr.ip}:{laddr.port}",
                        'remote_address': f"{raddr.ip}:{raddr.port}" if raddr else "N/A",
                        'pid': conn.pid,
                        'process_name': self.get_process_name(conn.pid),
                        'reason': '; '.join(reason),
                        'threat_level': 'high' if raddr and raddr.port in [4444, 31337] else 'medium'
                    }

                    suspicious_connections.append(connection_info)

                    self.trigger_alert({
                        'type': 'suspicious_network_connection',
                        'connection': connection_info,
                        'severity': 'high' if connection_info['threat_level'] == 'high' else 'medium'
                    })

        except Exception as e:
            logger.error(f"Network monitoring error: {e}")

        return suspicious_connections

    def get_process_name(self, pid: int) -> str:
        """Get process name from PID."""
        try:
            process = psutil.Process(pid)
            return process.name()
        except Exception:
            return f"PID {pid}"

    def is_path_in_allowlist(self, file_path: str) -> tuple:
        """Check if a file path is in the allowlist.
        
        Returns:
            tuple: (is_allowed: bool, should_override_severity: bool)
        """
        allowlist = self.config.get('allowlist', {})
        
        if not allowlist.get('enabled', True):
            return (False, False)
        
        # Check known directories
        known_dirs = allowlist.get('known_directories', [])
        for directory in known_dirs:
            if directory in file_path:
                return (True, True)
        
        return (False, False)

    def monitor_file_system_changes(self) -> List[Dict]:
        """Monitor file system changes for suspicious activity."""
        changes = []

        # Get current file hashes for monitored directories
        current_hashes = {}

        # Sensitive directories (reduced from broad scan)
        monitored_dirs = ['/usr/local/bin', '/usr/bin', '/etc', '/root', '/home']

        for directory in monitored_dirs:
            if os.path.exists(directory):
                for root, _, files in os.walk(directory):
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            # Skip large files and binary files
                            if file.endswith(('.pyc', '.pyo', '.so', '.dll', '.exe', '.bin')):
                                continue

                            file_hash = self.calculate_file_hash(file_path)
                            if file_hash:
                                # Check if file was previously tracked
                                if file_path in self.file_hashes:
                                    if self.file_hashes[file_path] != file_hash:
                                        # File has changed
                                        change_info = {
                                            'timestamp': datetime.now().isoformat(),
                                            'file_path': file_path,
                                            'old_hash': self.file_hashes[file_path],
                                            'new_hash': file_hash,
                                            'change_type': 'modification',
                                            'threat_level': 'medium'
                                        }

                                        changes.append(change_info)
                                        # Only trigger alert for modifications to known files
                                        self.trigger_alert({
                                            'type': 'file_system_change',
                                            'change': change_info,
                                            'severity': 'medium'
                                        })
                                else:
                                    # New file detected - only alert for sensitive subdirectories
                                    change_info = {
                                        'timestamp': datetime.now().isoformat(),
                                        'file_path': file_path,
                                        'new_hash': file_hash,
                                        'change_type': 'creation',
                                        'threat_level': 'medium'
                                    }
                                    changes.append(change_info)
                                    # Only alert for truly sensitive locations
                                    if any(sensitive in file_path for sensitive in ['/etc/', '/usr/bin/', '/usr/local/bin/', '/root/']):
                                        self.trigger_alert({
                                            'type': 'new_file_detected',
                                            'change': change_info,
                                            'severity': 'high'
                                        })

                                current_hashes[file_path] = file_hash
                        except Exception as e:
                            logger.debug(f"Could not hash file {file_path}: {e}")

        # Update tracked file hashes
        with self.lock:
            self.file_hashes.update(current_hashes)

        return changes

    def trigger_alert(self, alert_data: Dict):
        """Trigger an alert and log it.
        
        Checks allowlist and may override severity for known-good paths.
        """
        alert = {
            'id': len(self.alerts) + 1,
            'timestamp': datetime.now().isoformat(),
            **alert_data
        }
        
        # Check if alert is from a known-good path
        change = alert_data.get('change', {})
        file_path = change.get('file_path', '')
        
        if file_path:
            is_allowed, should_override_severity = self.is_path_in_allowlist(file_path)
            
            if is_allowed and should_override_severity:
                # Override severity to low for allowlisted paths
                alert['severity'] = self.config.get('allowlist', {}).get('severity_override', 'low')
                # Add a note that this is allowlisted
                alert['allowlisted'] = True
                alert['allowlist_reason'] = f"Path {file_path} matches allowlist"
                logger.info(f"Allowlisted alert: {alert['type']} - {file_path} (Severity: {alert['severity']})")
        
        with self.lock:
            self.alerts.append(alert)

        # Keep only last 1000 alerts
        with self.lock:
            if len(self.alerts) > 1000:
                self.alerts = self.alerts[-1000:]

        # Log based on severity
        if alert['severity'] in ['high', 'medium']:
            logger.warning(f"Alert triggered: {alert['type']} - Severity: {alert['severity']}")
        elif alert['severity'] == 'low':
            logger.info(f"Allowlisted alert triggered: {alert['type']} - Severity: {alert['severity']}")
        else:
            logger.debug(f"Alert triggered: {alert['type']} - Severity: {alert['severity']}")

        # Save database after alert
        self.save_database()

    def export_alerts(self, format: str = 'json', output_file: str = None):
        """Export alerts to specified format."""
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f'polinrider_alerts_{timestamp}.{format}'

        try:
            if format == 'json':
                with open(output_file, 'w') as f:
                    json.dump(self.alerts, f, indent=2)
            elif format == 'csv':
                with open(output_file, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['ID', 'Timestamp', 'Type', 'Severity', 'Details'])
                    for alert in self.alerts:
                        writer.writerow([
                            alert['id'],
                            alert['timestamp'],
                            alert['type'],
                            alert['severity'],
                            json.dumps(alert.get('connection', alert.get('change', {})))
                        ])
            logger.info(f"Exported {len(self.alerts)} alerts to {output_file}")
        except Exception as e:
            logger.error(f"Failed to export alerts: {e}")

    def get_status(self) -> Dict:
        """Get current monitoring status."""
        return {
            'timestamp': datetime.now().isoformat(),
            'alerts_count': len(self.alerts),
            'monitored_files': len(self.file_hashes),
            'running': self.running,
            'thresholds': self.thresholds
        }

    def save_live_status(self, status_path: str = '../../deploy/polinrider/polinrider_live_status.json'):
        """Save live status to JSON file for dashboard."""
        status = self.get_status()
        
        # Keep last 50 alerts (instead of 10) for better visibility
        status['recent_alerts'] = self.alerts[-50:]  # Last 50 alerts
        
        # Add summary statistics by alert type
        alert_summary = {}
        for alert in self.alerts:
            alert_type = alert.get('type', 'unknown')
            if alert_type not in alert_summary:
                alert_summary[alert_type] = {'total': 0, 'high': 0, 'medium': 0, 'low': 0}
            alert_summary[alert_type]['total'] += 1
            severity = alert.get('severity', 'low').lower()
            if severity in alert_summary[alert_type]:
                alert_summary[alert_type][severity] += 1
        
        status['alert_summary'] = alert_summary
        status['network_connections_count'] = len(self.network_connections)
        status['file_hashes_count'] = len(self.file_hashes)
        
        # Archive old alerts (keep only last 1000 in database)
        if len(self.alerts) > 1000:
            archived_alerts = self.alerts[:-1000]
            archive_file = f'polinrider_alerts_archive_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            try:
                with open(archive_file, 'w') as f:
                    json.dump(archived_alerts, f, indent=2)
                logger.info(f"Archived {len(archived_alerts)} old alerts to {archive_file}")
            except Exception as e:
                logger.error(f"Failed to archive alerts: {e}")
            # Keep only recent alerts in memory
            self.alerts = self.alerts[-1000:]
        
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(status_path)), exist_ok=True)
            with open(status_path, 'w') as f:
                json.dump(status, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save live status: {e}")

    def run(self):
        """Main monitoring loop."""
        logger.info("Starting PolinRider monitoring...")

        try:
            while self.running:
                start_time = time.time()

                # Monitor network connections
                network_alerts = self.monitor_network_connections()
                if network_alerts:
                    logger.warning(f"Detected {len(network_alerts)} suspicious network connections")

                # Monitor file system changes
                file_changes = self.monitor_file_system_changes()
                if file_changes:
                    logger.warning(f"Detected {len(file_changes)} file system changes")

                # Save database periodically
                if int(time.time()) % 60 == 0:  # Every minute
                    self.save_database()
                
                # Save live status for dashboard every 30 seconds (using elapsed time, not modulo)
                if int(time.time()) - self.last_live_status_save >= 30:  # Every 30 seconds
                    logger.info("SAVING LIVE STATUS TO DASHBOARD")
                    try:
                        self.save_live_status()
                        self.last_live_status_save = int(time.time())
                        logger.info("LIVE STATUS SAVED SUCCESSFULLY")
                    except Exception as e:
                        logger.error(f"Failed to save live status: {e}")
                        import traceback
                        traceback.print_exc()

                # Calculate sleep time
                elapsed = time.time() - start_time
                sleep_time = max(0, self.config.get('monitoring_interval', 30) - elapsed)

                time.sleep(sleep_time)

        except KeyboardInterrupt:
            logger.info("Shutting down PolinRider monitoring...")
            self.running = False
        except Exception as e:
            logger.error(f"Monitoring error: {e}")
            self.running = False

        # Final save
        self.save_database()
        logger.info("PolinRider monitoring stopped")

    def stop(self):
        """Stop the monitoring loop."""
        self.running = False


def main():
    parser = argparse.ArgumentParser(description='PolinRider Dependency Monitor')
    parser.add_argument('--config', type=str, default='config.json', help='Configuration file path')
    parser.add_argument('--export', type=str, choices=['json', 'csv'], help='Export alerts to file')
    parser.add_argument('--status', action='store_true', help='Show current status')

    args = parser.parse_args()

    monitor = PolinRiderMonitor(args.config)

    if args.status:
        status = monitor.get_status()
        print(json.dumps(status, indent=2))
    elif args.export:
        monitor.export_alerts(args.export)
    else:
        monitor.run()


if __name__ == '__main__':
    main()
