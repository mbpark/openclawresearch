#!/usr/bin/env python3
"""
QUIC XRING Test Dashboard
Real-time monitoring of test results and server status
"""

import json
import os
import time
import threading
import queue
from datetime import datetime
from pathlib import Path

class TestDashboard:
    def __init__(self, results_file=None):
        self.results_file = results_file or "/tmp/quic_test_dashboard.json"
        self.current_status = {
            "last_update": None,
            "test_status": "idle",
            "server_status": "stopped",
            "last_result": None,
            "total_tests": 0,
            "crashes": 0,
            "passed": 0,
            "last_test_name": "",
            "response_times": []
        }
        self.update_interval = 2  # seconds
        
    def update_status(self, status_data: dict):
        """Update dashboard status"""
        self.current_status.update(status_data)
        self.current_status["last_update"] = datetime.now().isoformat()
        
        # Save to file
        with open(self.results_file, 'w') as f:
            json.dump(self.current_status, f, indent=2)
    
    def record_test_result(self, result: dict):
        """Record a test result"""
        test_name = result.get('test_name', 'unknown')
        status = result.get('status', 'unknown')
        crash_detected = result.get('crash_detected', False)
        response_time = result.get('response_time_ms')
        
        self.current_status["last_test_name"] = test_name
        self.current_status["last_result"] = status
        self.current_status["total_tests"] += 1
        
        if crash_detected:
            self.current_status["crashes"] += 1
            status_display = "❌ CRASH"
        else:
            self.current_status["passed"] += 1
            status_display = "✅ PASSED"
        
        if response_time is not None:
            self.current_status["response_times"].append(response_time)
            # Keep last 10 response times
            self.current_status["response_times"] = self.current_status["response_times"][-10:]
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {test_name}: {status_display}")
        
        # Update status
        self.update_status({
            "test_status": status,
            "crashes": self.current_status["crashes"],
            "passed": self.current_status["passed"],
            "total_tests": self.current_status["total_tests"]
        })
    
    def start_server(self, server_pid=None):
        """Update server status"""
        if server_pid:
            import subprocess
            try:
                subprocess.run(['kill', '-0', str(server_pid)], check=True)
                server_alive = True
            except:
                server_alive = False
            
            self.update_status({
                "server_status": "running" if server_alive else "stopped",
                "server_pid": server_pid
            })
            return server_alive
        else:
            self.update_status({"server_status": "unknown"})
            return False
    
    def stop_server(self):
        """Update server status"""
        self.update_status({"server_status": "stopped"})
    
    def get_status(self) -> dict:
        """Get current dashboard status"""
        return self.current_status.copy()
    
    def display(self):
        """Display dashboard status"""
        status = self.current_status
        
        print("\n" + "=" * 60)
        print("QUIC XRING TEST DASHBOARD")
        print("=" * 60)
        
        print(f"\n📊 Status: {status['test_status'].upper()}")
        print(f"🖥️  Server: {status['server_status'].upper()}")
        print(f"📅 Last Update: {status['last_update']}")
        
        print(f"\n📈 Test Results:")
        print(f"   Total Tests: {status['total_tests']}")
        print(f"   ✅ Passed: {status['passed']}")
        print(f"   ❌ Crashes: {status['crashes']}")
        
        if status['response_times']:
            avg_response = sum(status['response_times']) / len(status['response_times'])
            print(f"\n⚡ Average Response Time: {avg_response:.2f}ms")
        
        if status['last_test_name']:
            print(f"\n🧪 Last Test: {status['last_test_name']}")
            print(f"   Result: {status['last_result']}")
        
        print("\n" + "=" * 60)
    
    def monitor_loop(self):
        """Continuous monitoring loop"""
        while True:
            self.display()
            time.sleep(self.update_interval)

# Example usage
if __name__ == "__main__":
    dashboard = TestDashboard()
    
    # Simulate test results
    test_results = [
        {"test_name": "basic_connectivity", "status": "completed", "crash_detected": False, "response_time_ms": 25.5},
        {"test_name": "xring_attack", "status": "completed", "crash_detected": False, "response_time_ms": 24.9},
        {"test_name": "rapid_attack_1", "status": "completed", "crash_detected": False, "response_time_ms": 23.1},
        {"test_name": "rapid_attack_2", "status": "completed", "crash_detected": False, "response_time_ms": 22.8},
    ]
    
    for result in test_results:
        dashboard.record_test_result(result)
        time.sleep(1)
    
    dashboard.display()
