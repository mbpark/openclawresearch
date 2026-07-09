#!/usr/bin/env python3
"""
AI Monitoring Continuous Runner - Phase 2
Runs the AI-enhanced monitoring system in continuous operation.
"""

import time
import json
import logging
import signal
import sys
from pathlib import Path
from typing import Dict, List, Optional
import threading
from datetime import datetime

# Import our AI monitoring system
from ai_monitoring import ResilienceMonitor, ResilienceMetrics

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("monitoring.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ContinuousMonitoringSystem:
    """Manages continuous AI monitoring with alerts and reporting"""
    
    def __init__(self, monitoring_interval: float = 30.0):
        self.monitor = ResilienceMonitor()
        self.monitoring_interval = monitoring_interval
        self.running = False
        self.last_report_time = time.time()
        self.critical_alerts = []
        self.monitoring_thread = None
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.stop()
        sys.exit(0)
    
    def _fetch_application_metrics(self) -> Optional[ResilienceMetrics]:
        """Fetch current metrics from the resilience test application"""
        try:
            import requests
            response = requests.get("http://localhost:8080/api/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                state = data.get("app_state", {})
                
                # Calculate response time from metrics endpoint
                try:
                    metrics_response = requests.get("http://localhost:8080/metrics", timeout=5)
                    if metrics_response.status_code == 200:
                        metrics_text = metrics_response.text
                        # Parse Prometheus metrics for response time histogram
                        # Look for app_request_duration_seconds values
                        response_time_avg = 0.002  # Default
                        for line in metrics_text.split('\n'):
                            if 'app_request_duration_seconds' in line and 'summary' not in line:
                                try:
                                    value = float(line.split()[-1])
                                    response_time_avg = value
                                    break
                                except:
                                    pass
                except Exception as e:
                    logger.error(f"Failed to parse metrics: {e}")
                    response_time_avg = 0.002

                return ResilienceMetrics(
                    timestamp=time.time(),
                    request_count=state.get("request_count", 0),
                    error_count=state.get("failures_simulated", 0),
                    response_time_avg=response_time_avg,
                    response_time_std=0.001,
                    checkpoint_count=state.get("checkpoint_count", 0),
                    recovery_count=state.get("recovery_count", 0),
                    failure_count=state.get("failures_simulated", 0)
                )
        except Exception as e:
            logger.error(f"Failed to fetch metrics: {e}")
            return None
    
    def _run_monitoring_loop(self):
        """Main monitoring loop"""
        logger.info("Starting AI monitoring loop...")
        self.running = True
        
        while self.running:
            try:
                # Fetch current metrics
                metrics = self._fetch_application_metrics()
                if metrics:
                    self.monitor.record_metrics(metrics)
                    report = self.monitor.generate_report()
                    
                    # Log monitoring data
                    self._log_monitoring_data(report)
                    
                    # Check for critical conditions
                    if report.get("health_score", 100) < 50:
                        self._handle_critical_alert(report)
                    
                    # Generate periodic reports
                    if time.time() - self.last_report_time > 300:  # Every 5 minutes
                        self._generate_periodic_report(report)
                        self.last_report_time = time.time()
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(10)
    
    def _log_monitoring_data(self, report: Dict):
        """Log monitoring data"""
        logger.info(f"Monitoring Report - Health Score: {report.get('health_score', 0)}/100")
        logger.info(f"  Current Metrics:")
        logger.info(f"    - Request Count: {report.get('current_metrics', {}).get('request_count', 0)}")
        logger.info(f"    - Error Count: {report.get('current_metrics', {}).get('error_count', 0)}")
        logger.info(f"    - Response Time: {report.get('current_metrics', {}).get('response_time_avg', 0):.4f}s")
        
        if report.get('insights'):
            logger.warning(f"  Insights Detected: {len(report['insights'])}")
            for insight in report['insights']:
                severity = insight.get('severity', 'unknown')
                insight_type = insight.get('type', 'unknown')
                logger.warning(f"    - {insight_type} ({severity})")
    
    def _handle_critical_alert(self, report: Dict):
        """Handle critical alert conditions"""
        alert = {
            "timestamp": time.time(),
            "type": "critical_health_score",
            "health_score": report.get("health_score", 0),
            "message": f"CRITICAL: System health score {report.get('health_score', 0)}/100"
        }
        
        self.critical_alerts.append(alert)
        logger.error(f"CRITICAL ALERT: {alert['message']}")
        
        # Send alert via multiple channels (can be extended)
        self._send_alert(alert)
    
    def _send_alert(self, alert: Dict):
        """Send alert through configured channels"""
        # In production, this would send to:
        # - Slack webhook
        # - Email
        # - PagerDuty
        # - SMS
        # - etc.
        
        logger.critical(f"ALERT: {alert['message']}")
        
        # Log to file
        with open("alerts.log", "a") as f:
            json.dump(alert, f)
            f.write("\n")
    
    def _generate_periodic_report(self, current_report: Dict):
        """Generate periodic monitoring report"""
        report = {
            "timestamp": time.time(),
            "period": "5_minutes",
            "health_score": current_report.get("health_score", 0),
            "insights_count": len(current_report.get('insights', [])),
            "alert_count": len(self.critical_alerts),
            "metrics_summary": current_report.get('current_metrics', {})
        }
        
        # Save report to file
        report_path = f"reports/monitoring_report_{int(time.time())}.json"
        Path(report_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Periodic report saved to {report_path}")
    
    def start(self):
        """Start continuous monitoring"""
        if self.running:
            logger.warning("Monitoring already running")
            return
        
        logger.info("Starting continuous AI monitoring system...")
        self.running = True
        self.monitoring_thread = threading.Thread(target=self._run_monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
        logger.info("AI monitoring system started successfully")
    
    def stop(self):
        """Stop continuous monitoring"""
        logger.info("Stopping AI monitoring system...")
        self.running = False
        self.monitor.stop()
        
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=10)
        
        logger.info("AI monitoring system stopped")
    
    def get_status(self) -> Dict:
        """Get current monitoring status"""
        return {
            "running": self.running,
            "health_score": self.monitor.generate_report().get("health_score", 0),
            "critical_alerts": len(self.critical_alerts),
            "last_report_time": self.last_report_time,
            "monitoring_interval": self.monitoring_interval
        }

def run_demo():
    """Run a demonstration of the continuous monitoring system"""
    print("=" * 60)
    print("AI Monitoring Continuous Runner - Demo Mode")
    print("=" * 60)
    
    system = ContinuousMonitoringSystem(monitoring_interval=10.0)
    
    # Simulate some metrics data
    import random
    for i in range(20):
        metrics = ResilienceMetrics(
            timestamp=time.time() + i,
            request_count=random.randint(100, 200),
            error_count=random.randint(0, 5),
            response_time_avg=0.001 + random.random() * 0.002,
            response_time_std=0.0001,
            checkpoint_count=random.randint(0, 3),
            recovery_count=random.randint(0, 1),
            failure_count=random.randint(0, 2)
        )
        system.monitor.record_metrics(metrics)
        
        # Generate and print report
        report = system.monitor.generate_report()
        print(f"\nIteration {i+1}:")
        print(f"  Health Score: {report['health_score']}/100")
        print(f"  Insights: {len(report['insights'])}")
        print(f"  Failure Probability: {report['failure_probability']}")
        
        time.sleep(2)
    
    print("\n" + "=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        run_demo()
    else:
        system = ContinuousMonitoringSystem()
        
        try:
            system.start()
            
            # Keep running
            while system.running:
                time.sleep(5)
                status = system.get_status()
                print(f"\nMonitoring Status (Ctrl+C to stop):")
                print(f"  Running: {status['running']}")
                print(f"  Health Score: {status['health_score']}/100")
                print(f"  Critical Alerts: {status['critical_alerts']}")
                
        except KeyboardInterrupt:
            print("\nShutting down monitoring system...")
            system.stop()
