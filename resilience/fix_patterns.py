#!/usr/bin/env python3
"""Script to fix the resilience_patterns.py class ordering issue"""

import re
import sys

# Read the original file
with open('/Users/mitchparker/.openclaw/workspace/research/resilience/resilience_patterns_old.py', 'r') as f:
    content = f.read()

# Find all class definitions with their code blocks
class_pattern = r'^class\s+(\w+)(?:\([^)]*\))?:.*?(?=\n^class\s|\n^[^@\s]|\Z)'
classes = re.findall(class_pattern, content, re.MULTILINE | re.DOTALL)

print(f"Found {len(classes)} class definitions")

# Map of class name to its position in the correct order
# We need to order based on dependencies
correct_order = [
    'CircuitBreakerState',
    'Checkpoint',
    'CheckpointManager',
    'SecureCheckpointManager',
    'Checkpointing',
    'CircuitBreakerStateData',
    'CircuitBreaker',
    'RetryWithExponentialBackoff',
    'Bulkhead',
    'TimeoutGuard',
    'FallbackHandler',
    'MultiLayerFallback',
    'SecurityFallbackLayer',
    'SecurityAwareRequestPrioritizer',
    'ResilientService',
]

# Create a dictionary to store class code by name
class_code = {}

for class_name in correct_order:
    # Find all occurrences of this class
    pattern = r'^class\s+' + re.escape(class_name) + r'(?:\([^)]*\))?:.*?(?=\n^class\s|\n^[^@\s]|\Z)'
    matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
    if matches:
        # If duplicates, keep the first one (or last one)
        class_code[class_name] = matches[-1]  # Keep last occurrence (may have fixes)
        print(f"  {class_name}: {len(matches)} occurrence(s)")
    else:
        print(f"  {class_name}: NOT FOUND")

print("\nWriting new file...")

# Build the new file content
new_content = '''#!/usr/bin/env python3
"""
Advanced Resilience Patterns Implementation
Circuit Breaker, Retry with Backoff, Bulkhead, Timeout, Fallback
"""

import asyncio
import time
import random
import logging
import json
import os
import base64
from pathlib import Path
from typing import Callable, Optional, Any, Dict, List
from dataclasses import dataclass, field, asdict
from enum import Enum
from functools import wraps
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

'''

# Add classes in correct order
for class_name in correct_order:
    if class_name in class_code:
        new_content += class_code[class_name] + '\n\n'

# Write the new file
with open('/Users/mitchparker/.openclaw/workspace/research/resilience/resilience_patterns_fixed.py', 'w') as f:
    f.write(new_content)

print(f"New file created: resilience_patterns_fixed.py")
print(f"Total characters: {len(new_content)}")
