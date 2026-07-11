#!/usr/bin/env python3
"""
Test the XRING dashboard API
"""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:5001"

def test_api():
    print("Testing XRING Dashboard API...")
    print("=" * 60)
    
    # Test 1: Get status
    print("\n1. Testing /api/status...")
    try:
        response = requests.get(f"{BASE_URL}/api/status")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Get metrics
    print("\n2. Testing /api/metrics...")
    try:
        response = requests.get(f"{BASE_URL}/api/metrics")
        print(f"Metrics: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 3: Get alerts
    print("\n3. Testing /api/alerts...")
    try:
        response = requests.get(f"{BASE_URL}/api/alerts")
        data = response.json()
        print(f"Alerts count: {data['count']}")
        print(f"Alerts: {json.dumps(data['alerts'], indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 4: Add test alert
    print("\n4. Adding test alert...")
    try:
        alert = {
            "alert_type": "xring_network_pattern",
            "severity": "high",
            "description": "Test alert from dashboard API test",
            "evidence": {"test": True, "timestamp": "2026-07-10T16:30:00Z"},
            "action": "test_action"
        }
        response = requests.post(f"{BASE_URL}/api/alerts", json=alert)
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 5: Verify alert was added
    print("\n5. Checking alerts again...")
    time.sleep(1)
    try:
        response = requests.get(f"{BASE_URL}/api/alerts?limit=10")
        data = response.json()
        print(f"Total alerts now: {data['count']}")
        for alert in data['alerts'][:5]:
            print(f" - {alert['alert_type']}: {alert['description']}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 6: Add multiple alerts
    print("\n6. Adding 3 test alerts...")
    try:
        for i in range(1, 4):
            alert = {
                "alert_type": f"xring_test_{i}",
                "severity": "medium",
                "description": f"Test alert number {i}",
                "evidence": {"test": True, "index": i},
                "action": f"test_action_{i}"
            }
            requests.post(f"{BASE_URL}/api/alerts", json=alert)
        
        print("Added 3 alerts")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 60)
    print("Dashboard API test completed!")

if __name__ == "__main__":
    test_api()
