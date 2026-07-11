#!/usr/bin/env python3
"""
XRING Security Dashboard
Web-based dashboard for monitoring XRING detection and security status
"""

from flask import Flask, render_template, jsonify, request
import json
import os
import threading
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict

app = Flask(__name__)

# Global state
class SecurityDashboard:
    def __init__(self):
        self.alerts: List[Dict] = []
        self.metrics = {
            "last_update": None,
            "total_alerts": 0,
            "critical_alerts": 0,
            "high_alerts": 0,
            "medium_alerts": 0,
            "low_alerts": 0,
            "suricata_status": "unknown",
            "monitor_status": "unknown",
            "workflow_status": "unknown"
        }
    
    def add_alert(self, alert_data: Dict):
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
    
    def update_status(self, component: str, status: str):
        """Update component status"""
        if component == "suricata":
            self.metrics["suricata_status"] = status
        elif component == "monitor":
            self.metrics["monitor_status"] = status
        elif component == "workflow":
            self.metrics["workflow_status"] = status
        
        self.metrics["last_update"] = datetime.now().isoformat()
    
    def get_alerts(self, limit: int = 50, severity: str = None) -> List[Dict]:
        """Get alerts with optional filtering"""
        alerts = self.alerts
        
        if severity:
            alerts = [a for a in alerts if a.get("severity") == severity]
        
        return alerts[:limit]
    
    def get_metrics(self) -> Dict:
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
        "monitor": dashboard.metrics["monitor_status"],
        "workflow": dashboard.metrics["workflow_status"],
        "last_update": dashboard.metrics["last_update"]
    })

# Function to simulate alerts for demo
def simulate_alerts():
    """Generate test alerts for demonstration"""
    import random
    
    alert_types = [
        {"type": "xring_network_pattern", "severity": "high"},
        {"type": "xring_memory_violation", "severity": "critical"},
        {"type": "xring_crash", "severity": "critical"},
        {"type": "xring_workflow_pattern", "severity": "high"}
    ]
    
    processes = ["xquic-server", "nghttp3-server", "quiche-server", "quic-go-server"]
    
    while True:
        if random.random() < 0.3:  # 30% chance of alert every 5 seconds
            alert_type = random.choice(alert_types)
            process = random.choice(processes)
            
            alert = {
                "alert_type": alert_type["type"],
                "severity": alert_type["severity"],
                "description": f"XRING {alert_type['type']} detected in {process}",
                "evidence": {
                    "process": process,
                    "timestamp": datetime.now().isoformat()
                },
                "action": f"block_{process}"
            }
            
            dashboard.add_alert(alert)
            print(f"Simulated alert: {alert['alert_type']} from {process}")
        
        time.sleep(5)

# Background thread for simulation
if __name__ == '__main__':
    import argparse
    import time
    
    parser = argparse.ArgumentParser(description='XRING Security Dashboard')
    parser.add_argument('--port', default=5000, type=int, help='Port to run on')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--simulate', action='store_true', help='Simulate alerts')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    
    args = parser.parse_args()
    
    # Start alert simulation if requested
    if args.simulate:
        sim_thread = threading.Thread(target=simulate_alerts)
        sim_thread.daemon = True
        sim_thread.start()
        print("Alert simulation started")
    
    # Run Flask app
    print(f"Starting XRING Security Dashboard on http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop")
    
    app.run(host=args.host, port=args.port, debug=args.debug)
