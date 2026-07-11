#!/usr/bin/env python3
"""
XRING Suricata Real-Time Alert Dashboard
Monitors Suricata alerts and displays them on a web dashboard
"""

from flask import Flask, render_template, jsonify, request
import subprocess
import json
import os
import threading
import queue
from datetime import datetime
from pathlib import Path
import re
import time

app = Flask(__name__)

# Global state
class SecurityDashboard:
    def __init__(self):
        self.alerts = []
        self.metrics = {
            "last_update": None,
            "total_alerts": 0,
            "critical_alerts": 0,
            "high_alerts": 0,
            "medium_alerts": 0,
            "low_alerts": 0,
            "suricata_status": "checking",
            "last_suricata_run": None,
            "suricata_output": "",
            "workflow_status": "active"
        }
        self.log_queue = queue.Queue()
        self.running = True
    
    def add_alert(self, alert_data):
        """Add a security alert"""
        alert = {
            "timestamp": datetime.now().isoformat(),
            **alert_data
        }
        self.alerts.insert(0, alert)
        self.metrics["total_alerts"] += 1
        
        # Update severity counts
        severity = alert.get("severity", "low")
        if severity == "critical":
            self.metrics["critical_alerts"] += 1
        elif severity == "high":
            self.metrics["high_alerts"] += 1
        elif severity == "medium":
            self.metrics["medium_alerts"] += 1
        else:
            self.metrics["low_alerts"] += 1
        
        # Keep only last 100 alerts
        if len(self.alerts) > 100:
            self.alerts = self.alerts[:100]
    
    def update_suricata_status(self, output):
        """Update Suricata status"""
        self.metrics["suricata_status"] = "running"
        self.metrics["last_suricata_run"] = datetime.now().isoformat()
        self.metrics["suricata_output"] = output[-2000:] if len(output) > 2000 else output
    
    def get_alerts(self, limit=50, severity=None):
        """Get alerts with optional filtering"""
        alerts = self.alerts
        
        if severity:
            alerts = [a for a in alerts if a.get("severity") == severity]
        
        return alerts[:limit]
    
    def get_metrics(self):
        """Get current metrics"""
        return self.metrics.copy()

# Initialize dashboard
dashboard = SecurityDashboard()

@app.route('/')
def dashboard_index():
    """Main dashboard page"""
    return render_template('dashboard.html', dashboard=dashboard)

@app.route('/api/alerts')
def api_get_alerts():
    """API endpoint for alerts"""
    limit = request.args.get('limit', 50, type=int)
    severity = request.args.get('severity')
    
    return jsonify({
        "alerts": dashboard.get_alerts(limit, severity),
        "count": len(dashboard.get_alerts(limit, severity))
    })

@app.route('/api/metrics')
def api_get_metrics():
    """API endpoint for metrics"""
    return jsonify(dashboard.get_metrics())

@app.route('/api/alerts', methods=['POST'])
def api_add_alert():
    """API endpoint to add alerts"""
    alert_data = request.json
    
    if not alert_data:
        return jsonify({"error": "No alert data provided"}), 400
    
    dashboard.add_alert(alert_data)
    
    return jsonify({
        "success": True,
        "alert_id": len(dashboard.alerts),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/status')
def api_get_status():
    """API endpoint for component status"""
    return jsonify({
        "suricata": dashboard.metrics["suricata_status"],
        "workflow": dashboard.metrics["workflow_status"],
        "last_update": dashboard.metrics["last_update"]
    })

def parse_suricata_alerts():
    """Parse Suricata alerts from recent log"""
    print("Parsing Suricata alerts...")
    
    # Check if Suricata is running
    try:
        result = subprocess.run(
            ["ps", "aux", "|", "grep", "suricata", "|", "grep", "v", "grep"],
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print("✅ Suricata is running")
            dashboard.update_suricata_status("Suricata detected running")
        else:
            print("❌ Suricata not running")
            dashboard.update_suricata_status("Suricata not running")
            return
        
        # Parse Suricata EVE JSON logs
        eve_log = "/Users/mitchparker/.suricata/log/eve.json"
        
        if os.path.exists(eve_log):
            with open(eve_log, 'r') as f:
                lines = f.readlines()[-20:]  # Read last 20 lines
            
            for line in lines:
                try:
                    event = json.loads(line.strip())
                    if event.get('event_type') == 'alert' and 'xring' in event.get('alert', {}).get('signature', '').lower():
                        alert = {
                            "alert_id": event.get('alert', {}).get('gid', 1) + event.get('alert', {}).get('sig_id', 0),
                            "signature": event.get('alert', {}).get('signature', 'Unknown'),
                            "severity": event.get('alert', {}).get('severity', 'low'),
                            "description": event.get('alert', {}).get('category', 'Security Alert'),
                            "timestamp": event.get('timestamp', datetime.now().isoformat()),
                            "src_ip": event.get('src_ip', event.get('ip_src', 'unknown')),
                            "dst_ip": event.get('dst_ip', event.get('ip_dst', 'unknown')),
                            "src_port": event.get('src_port', event.get('sport', 'unknown')),
                            "dst_port": event.get('dst_port', event.get('dport', 'unknown')),
                            "protocol": event.get('proto', 'unknown'),
                            "evidence": event.get('alert', {})
                        }
                        
                        dashboard.add_alert(alert)
                        print(f"Found XRING alert: {alert['signature']}")
                except json.JSONDecodeError:
                    continue
    
    except Exception as e:
        print(f"Error parsing Suricata alerts: {e}")
        dashboard.update_suricata_status(f"Error: {str(e)}")

def suricata_monitor_loop():
    """Background thread to monitor Suricata alerts"""
    print("Starting Suricata monitoring thread...")
    
    while dashboard.running:
        try:
            parse_suricata_alerts()
            time.sleep(5)  # Check every 5 seconds
        except Exception as e:
            print(f"Error in monitoring loop: {e}")
            time.sleep(10)

def dashboard_monitor_loop():
    """Main monitoring loop"""
    print("Starting dashboard monitoring...")
    
    while dashboard.running:
        try:
            # Update metrics
            dashboard.metrics["last_update"] = datetime.now().isoformat()
            
            time.sleep(2)
        except Exception as e:
            print(f"Error in dashboard monitoring: {e}")
            time.sleep(5)

# API test endpoint for testing
@app.route('/test_alert', methods=['POST'])
def test_alert():
    """Test endpoint for adding alerts"""
    alert = {
        "alert_type": "test_alert",
        "severity": request.json.get('severity', 'low'),
        "description": f"Test alert from dashboard API - {request.json.get('description', 'No description')}",
        "evidence": request.json,
        "action": "monitor"
    }
    
    dashboard.add_alert(alert)
    
    return jsonify({
        "success": True,
        "message": "Test alert added successfully"
    })

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='XRING Suricata Dashboard')
    parser.add_argument('--port', default=5001, type=int, help='Port to run on')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--test', action='store_true', help='Run in test mode')
    
    args = parser.parse_args()
    
    # Start monitoring threads
    monitor_thread = threading.Thread(target=suricata_monitor_loop)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    dashboard_thread = threading.Thread(target=dashboard_monitor_loop)
    dashboard_thread.daemon = True
    dashboard_thread.start()
    
    print(f"Starting XRING Suricata Dashboard on http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop")
    
    # Start test mode if requested
    if args.test:
        print("Test mode enabled - adding test alerts")
        test_alert = {
            "alert_type": "xring_network_pattern",
            "severity": "high",
            "description": "Test XRING network pattern detection",
            "evidence": {"test": True},
            "action": "test"
        }
        dashboard.add_alert(test_alert)
    
    app.run(host=args.host, port=args.port, debug=args.debug)
