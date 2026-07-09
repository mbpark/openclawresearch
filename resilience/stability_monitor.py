#!/usr/bin/env python3
"""
24-Hour Stability Monitor - Phase 3
Continuous monitoring with detailed logging and reporting.
"""

import time
import json
import logging
import os
import signal
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("stability_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class StabilityMonitor:
    """Monitors system stability over extended periods"""
    
    def __init__(self, check_interval: float = 60.0):
        self.check_interval = check_interval
        self.start_time = time.time()
        self.checks: List[Dict] = []
        self.issues: List[Dict] = []
        self.running = False
        self.monitoring_thread = None
        
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, generating final report...")
        self.stop()
        
        # Generate final report
        self.generate_report()
        sys.exit(0)
    
    def perform_health_check(self) -> Dict:
        """Perform comprehensive health check"""
        check_time = time.time()
        timestamp = datetime.now().isoformat()
        
        # Health endpoint
        health = {"healthy": False, "error": None}
        try:
            response = requests.get("http://localhost:8080/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                health = {
                    "healthy": health_data.get("status") == "healthy",
                    "uptime": health_data.get("uptime", 0),
                    "request_count": health_data.get("request_count", 0),
                    "failures_simulated": health_data.get("failures_simulated", 0),
                    "recovery_count": health_data.get("recovery_count", 0),
                    "checkpoint_count": health_data.get("checkpoint_count", 0),
                    "timestamp": check_time
                }
            else:
                health["error"] = f"Status {response.status_code}"
        except Exception as e:
            health["error"] = str(e)
        
        # Metrics endpoint
        metrics = {"error": None, "data": {}}
        try:
            response = requests.get("http://localhost:8080/metrics", timeout=5)
            if response.status_code == 200:
                metrics_text = response.text
                # Parse some key metrics
                for line in metrics_text.split('\n'):
                    if 'app_' in line and not line.startswith('#'):
                        try:
                            metric_name, value = line.split()
                            metrics["data"][metric_name] = float(value)
                        except:
                            pass
        except Exception as e:
            metrics["error"] = str(e)
        
        # Check response time
        response_times = []
        try:
            start = time.time()
            requests.get("http://localhost:8080/api/status", timeout=10)
            response_times.append(time.time() - start)
        except Exception as e:
            logger.warning(f"Response time check failed: {e}")
        
        # Record check
        check_result = {
            "timestamp": timestamp,
            "check_time": check_time,
            "uptime_seconds": time.time() - self.start_time,
            "health": health,
            "metrics": metrics["data"],
            "metrics_errors": metrics["error"],
            "response_time": response_times[0] if response_times else None,
            "status": "healthy" if health.get("healthy", False) and not metrics["error"] else "degraded"
        }
        
        self.checks.append(check_result)
        
        # Check for issues
        if not health.get("healthy", False):
            self.issues.append({
                "timestamp": timestamp,
                "type": "health_check_failed",
                "details": health.get("error", "Unknown error")
            })
            logger.error(f"Health check failed: {health.get('error', 'Unknown error')}")
        
        if check_result.get("response_time") and check_result["response_time"] > 1.0:
            self.issues.append({
                "timestamp": timestamp,
                "type": "slow_response",
                "details": f"Response time {check_result['response_time']:.2f}s > 1s"
            })
            logger.warning(f"Slow response time: {check_result['response_time']:.2f}s")
        
        return check_result
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        self.running = True
        check_count = 0
        
        logger.info("Starting 24-hour stability monitoring...")
        
        while self.running:
            try:
                check_result = self.perform_health_check()
                check_count += 1
                
                # Log progress
                if check_count % 10 == 0:
                    logger.info(f"Check {check_count} complete. Total checks: {check_count}")
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(30)
    
    def start(self):
        """Start monitoring"""
        if self.running:
            logger.warning("Monitoring already running")
            return
        
        self.start_time = time.time()
        self.checks = []
        self.issues = []
        self.running = True
        
        logger.info(f"Starting stability monitoring (interval: {self.check_interval}s)...")
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
    
    def stop(self):
        """Stop monitoring"""
        self.running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=10)
    
    def generate_report(self) -> Dict:
        """Generate comprehensive stability report"""
        total_duration = time.time() - self.start_time
        total_checks = len(self.checks)
        failed_checks = sum(1 for check in self.checks if check["status"] != "healthy")
        
        # Calculate statistics
        response_times = [c["response_time"] for c in self.checks if c["response_time"] is not None]
        request_counts = [c["health"].get("request_count", 0) for c in self.checks]
        
        report = {
            "monitoring_duration_seconds": total_duration,
            "monitoring_duration_human": str(timedelta(seconds=int(total_duration))),
            "total_checks": total_checks,
            "successful_checks": total_checks - failed_checks,
            "failed_checks": failed_checks,
            "success_rate": ((total_checks - failed_checks) / total_checks * 100) if total_checks > 0 else 0,
            "issues_count": len(self.issues),
            "issues": self.issues,
            "response_time_stats": {
                "avg": sum(response_times) / len(response_times) if response_times else 0,
                "min": min(response_times) if response_times else 0,
                "max": max(response_times) if response_times else 0,
                "stable": len(response_times) > 0 and max(response_times) < 0.5
            },
            "request_volume": {
                "start": request_counts[0] if request_counts else 0,
                "end": request_counts[-1] if request_counts else 0,
                "trend": "increasing" if len(request_counts) > 1 and request_counts[-1] > request_counts[0] else "stable"
            },
            "system_status": "stable" if failed_checks == 0 else "unstable",
            "timestamp": datetime.now().isoformat(),
            "checks": self.checks
        }
        
        # Save report
        report_path = f"stability_report_{int(time.time())}.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Stability report saved to {report_path}")
        return report

def main():
    """Main function"""
    monitor = StabilityMonitor(check_interval=30.0)
    
    try:
        monitor.start()
        
        # Monitor for 24 hours or until interrupted
        max_duration = 24 * 60 * 60  # 24 hours
        start_time = time.time()
        
        logger.info(f"Monitoring for up to 24 hours (Ctrl+C to stop early)...")
        
        while time.time() - start_time < max_duration:
            elapsed = time.time() - start_time
            remaining = max_duration - elapsed
            hours, remainder = divmod(int(remaining), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            print(f"\rMonitoring: {int(elapsed//3600)}h {hours}h {minutes}m {seconds}s remaining | "
                  f"Checks: {len(monitor.checks)} | Issues: {len(monitor.issues)}", end="")
            
            time.sleep(60)
        
        print("\n24-hour monitoring complete!")
        
    except KeyboardInterrupt:
        print("\nStopping monitoring...")
    finally:
        monitor.stop()
        report = monitor.generate_report()
        
        print("\n" + "=" * 60)
        print("24-HOUR STABILITY REPORT")
        print("=" * 60)
        print(f"Duration: {report['monitoring_duration_human']}")
        print(f"Total Checks: {report['total_checks']}")
        print(f"Success Rate: {report['success_rate']:.1f}%")
        print(f"Issues: {report['issues_count']}")
        print(f"Status: {report['system_status'].upper()}")
        print("=" * 60)

if __name__ == "__main__":
    main()
