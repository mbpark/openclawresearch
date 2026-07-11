#!/usr/bin/env python3
"""
XRING Security Monitor
Integrates detection signatures into existing security infrastructure
"""

import subprocess
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

@dataclass
class SecurityAlert:
    timestamp: str
    alert_type: str
    severity: str
    description: str
    evidence: dict
    action: str
    
    def to_dict(self):
        return asdict(self)
    
    def save(self, filename: str):
        with open(filename, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

class XRingSecurityMonitor:
    def __init__(self):
        self.alerts: List[SecurityAlert] = []
        self.log_files = []
        
    def analyze_process_output(self, process_name: str, output: str) -> List[SecurityAlert]:
        """Analyze process output for memory violation indicators"""
        alerts = []
        
        # Memory violation patterns
        memory_patterns = {
            '_FORTIFY_SOURCE': 'FORTIFY_SOURCE abort triggered',
            'buffer overflow detected': 'Buffer overflow detected',
            'ASAN: heap-buffer-overflow': 'AddressSanitizer detected heap overflow',
            'UBSAN: runtime error': 'UndefinedBehaviorSanitizer detected error',
            'round buffer overflow': 'Round buffer overflow',
            'memcpy.*length.*exceeds': 'Memcpy length exceeds available buffer'
        }
        
        # Crash signals
        signal_patterns = {
            'SIGSEGV': 'Segmentation fault',
            'SIGABRT': 'Abort signal',
            'SIGTRAP': 'Trap signal',
            'SIGBUS': 'Bus error'
        }
        
        # Check for memory violations
        for pattern, description in memory_patterns.items():
            if pattern.lower() in output.lower():
                alert = SecurityAlert(
                    timestamp=datetime.now().isoformat(),
                    alert_type='xring_memory_violation',
                    severity='critical',
                    description=f"{description} in {process_name}",
                    evidence={'pattern': pattern, 'process': process_name},
                    action='kill_process_capture_dump'
                )
                alerts.append(alert)
        
        # Check for crash signals
        for signal, description in signal_patterns.items():
            if signal in output:
                alert = SecurityAlert(
                    timestamp=datetime.now().isoformat(),
                    alert_type='xring_crash',
                    severity='critical',
                    description=f"{description} ({signal}) in {process_name}",
                    evidence={'signal': signal, 'process': process_name},
                    action='kill_process_capture_dump'
                )
                alerts.append(alert)
        
        return alerts
    
    def analyze_network_traffic(self, packet_data: bytes, protocol: str) -> List[SecurityAlert]:
        """Analyze network traffic for XRING attack patterns"""
        alerts = []
        
        # Check for QPACK encoder stream pattern
        if b'QPACK' in packet_data or protocol == 'http/3':
            # Check payload size anomaly
            if len(packet_data) in range(256, 265):
                # Check for capacity sequence
                if b'\x20\x40' in packet_data and b'\x20\x41' in packet_data:
                    alert = SecurityAlert(
                        timestamp=datetime.now().isoformat(),
                        alert_type='xring_network_pattern',
                        severity='high',
                        description='XRING QPACK attack pattern detected in network traffic',
                        evidence={
                            'packet_size': len(packet_data),
                            'protocol': protocol,
                            'pattern': 'capacity_64_65_sequence'
                        },
                        action='block_source_ip_capture_traffic'
                    )
                    alerts.append(alert)
        
        return alerts
    
    def check_workflow_graph(self, operations: List[Dict]) -> List[SecurityAlert]:
        """Check workflow graph operations for XRING attack patterns"""
        alerts = []
        
        capacity_changes = []
        insert_operations = []
        
        for i, op in enumerate(operations):
            if op.get('type') == 'set_dynamic_table_capacity':
                capacity_changes.append({
                    'index': i,
                    'timestamp': datetime.now().isoformat(),
                    'capacity': op.get('capacity')
                })
            elif op.get('type') == 'insert':
                name_len = len(op.get('name', ''))
                value_len = len(op.get('value', ''))
                
                if name_len == 1 and value_len == 1:
                    insert_operations.append({
                        'index': i,
                        'type': 'small_insert'
                    })
                elif name_len == 5 and value_len == 5:
                    insert_operations.append({
                        'index': i,
                        'type': 'large_insert'
                    })
        
        # Check for XRing capacity sequence (64 -> 65)
        if len(capacity_changes) >= 2:
            recent = capacity_changes[-2:]
            if recent[0]['capacity'] == 64 and recent[1]['capacity'] == 65:
                time_diff = 0  # Would need timestamps
                if time_diff < 5.0:  # Within 5 seconds
                    alert = SecurityAlert(
                        timestamp=datetime.now().isoformat(),
                        alert_type='xring_workflow_pattern',
                        severity='high',
                        description='XRING capacity change pattern detected in workflow operations',
                        evidence={
                            'capacity_sequence': [64, 65],
                            'time_window': time_diff
                        },
                        action='block_workflow_suspend_operations'
                    )
                    alerts.append(alert)
        
        # Check for insert pattern (61 small, 1 large)
        small_count = len([op for op in insert_operations if op['type'] == 'small_insert'])
        large_count = len([op for op in insert_operations if op['type'] == 'large_insert'])
        
        if small_count >= 61 and large_count >= 1:
            alert = SecurityAlert(
                timestamp=datetime.now().isoformat(),
                alert_type='xring_workflow_pattern',
                severity='high',
                description='XRING insert operation pattern detected in workflow',
                evidence={
                    'small_inserts': small_count,
                    'large_inserts': large_count
                },
                action='block_workflow_suspend_operations'
            )
            alerts.append(alert)
        
        return alerts
    
    def generate_report(self, alerts: List[SecurityAlert]) -> str:
        """Generate security incident report"""
        report = f"XRING Security Alert Report\n"
        report += "=" * 50 + "\n\n"
        report += f"Generated: {datetime.now().isoformat()}\n"
        report += f"Total Alerts: {len(alerts)}\n\n"
        
        severity_counts = {}
        alert_types = {}
        
        for alert in alerts:
            sev = alert.severity
            alert_type = alert.alert_type
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
            alert_types[alert_type] = alert_types.get(alert_type, 0) + 1
        
        report += "Severity Distribution:\n"
        for severity, count in severity_counts.items():
            report += f"  {severity.upper()}: {count}\n"
        
        report += "\nAlert Types:\n"
        for alert_type, count in alert_types.items():
            report += f"  {alert_type}: {count}\n"
        
        report += "\nDetailed Alerts:\n"
        for i, alert in enumerate(alerts, 1):
            report += f"\nAlert {i}:\n"
            report += f"  Type: {alert.alert_type}\n"
            report += f"  Severity: {alert.severity}\n"
            report += f"  Description: {alert.description}\n"
            report += f"  Action Required: {alert.action}\n"
        
        return report
    
    def save_alerts(self, filename: str = "xring_alerts.json"):
        """Save all alerts to a JSON file"""
        with open(filename, 'w') as f:
            json.dump([alert.to_dict() for alert in self.alerts], f, indent=2)
        print(f"Saved {len(self.alerts)} alerts to {filename}")
    
    def load_alerts(self, filename: str = "xring_alerts.json"):
        """Load alerts from a JSON file"""
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                data = json.load(f)
                self.alerts = [SecurityAlert(**alert_data) for alert_data in data]
            print(f"Loaded {len(self.alerts)} alerts from {filename}")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='XRING Security Monitor')
    parser.add_argument('--analyze', type=str, help='Analyze process output or network traffic')
    parser.add_argument('--check-workflow', action='store_true', help='Check workflow graph operations')
    parser.add_argument('--report', action='store_true', help='Generate alert report')
    parser.add_argument('--save', action='store_true', help='Save current alerts')
    parser.add_argument('--load', action='store_true', help='Load previous alerts')
    
    args = parser.parse_args()
    
    monitor = XRingSecurityMonitor()
    
    if args.analyze:
        # Analyze process output or network traffic
        with open(args.analyze, 'r') as f:
            content = f.read()
        
        # Try to detect if it's process output or network traffic
        if 'process' in args.analyze.lower():
            alerts = monitor.analyze_process_output('analyzed_process', content)
        else:
            alerts = monitor.analyze_network_traffic(content.encode(), 'http/3')
        
        monitor.alerts.extend(alerts)
        print(f"Analysis complete. Found {len(alerts)} alerts.")
    
    if args.check_workflow:
        # For demo, create sample operations
        sample_operations = [
            {'type': 'set_dynamic_table_capacity', 'capacity': 64},
            {'type': 'insert', 'name': 'x', 'value': 'y'},
            {'type': 'insert', 'name': 'x', 'value': 'y'},
            # ... 61 small inserts would be here ...
            {'type': 'insert', 'name': 'AAAAA', 'value': 'BBBBB'},
            {'type': 'set_dynamic_table_capacity', 'capacity': 65}
        ]
        alerts = monitor.check_workflow_graph(sample_operations)
        monitor.alerts.extend(alerts)
        print(f"Workflow check complete. Found {len(alerts)} alerts.")
    
    if args.report:
        report = monitor.generate_report(monitor.alerts)
        print(report)
        with open('xring_report.txt', 'w') as f:
            f.write(report)
    
    if args.save:
        monitor.save_alerts()
    
    if args.load:
        monitor.load_alerts()
        print(f"Loaded {len(monitor.alerts)} alerts.")
    
    # Always save after operation
    if args.save or args.analyze or args.check_workflow:
        monitor.save_alerts()
