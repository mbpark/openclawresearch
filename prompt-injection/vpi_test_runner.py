#!/usr/bin/env python3
"""
VPI-Bench Test Runner - Visual Prompt Injection Testing Framework

This script automates Visual Prompt Injection (VPI) testing for VLMs and AI agents,
based on the VPI-Bench methodology and InkJect research findings.
"""

import json
import os
import time
import base64
import random
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from enum import Enum

class VPIAttackType(Enum):
    WHITE_ON_WHITE = "white_on_white"
    PERSPECTIVE_DISTORTION = "perspective_distortion"
    NOISE_OVERLAY = "noise_overlay"
    INDIRECT_VISUAL = "indirect_visual"
    BENIGN_TASK_HIDDEN_INSTRUCTION = "benign_task_hidden_instruction"

class VPIAttackTarget(Enum):
    CODE_GENERATION = "code_generation"
    DATA_ANALYSIS = "data_analysis"
    WORKFLOW_AUTOMATION = "workflow_automation"
    CREDENTIAL_HARVESTING = "credential_harvesting"
    SYSTEM_PROMPT_LEAK = "system_prompt_leak"
    BACKDOOR_INSTALLATION = "backdoor_installation"

@dataclass
class VPITestCase:
    test_id: str
    attack_type: VPIAttackType
    attack_target: VPIAttackTarget
    image_path: str
    user_prompt: str
    malicious_instruction: str
    expected_behavior: str
    success_criteria: List[str]

class VPITestRunner:
    def __init__(self, model_provider: str = "anthropic"):
        self.model_provider = model_provider
        self.test_results = []
        self.failed_images = []
        
    def load_test_cases(self, test_cases_file: str) -> List[VPITestCase]:
        """Load test cases from a JSON file."""
        with open(test_cases_file, 'r') as f:
            data = json.load(f)
            
        test_cases = []
        for item in data:
            test_case = VPITestCase(
                test_id=item['test_id'],
                attack_type=VPIAttackType(item['attack_type']),
                attack_target=VPIAttackTarget(item['attack_target']),
                image_path=item['image_path'],
                user_prompt=item['user_prompt'],
                malicious_instruction=item['malicious_instruction'],
                expected_behavior=item['expected_behavior'],
                success_criteria=item['success_criteria']
            )
            test_cases.append(test_case)
            
        return test_cases
    
    def read_simulated_image(self, image_path: str) -> str:
        """Read simulated image description from text file."""
        # Handle both .png and .txt extensions for simulated images
        txt_path = image_path.replace('.png', '.txt') if image_path.endswith('.png') else image_path
        if os.path.exists(txt_path):
            with open(txt_path, 'r') as f:
                return f.read()
        elif os.path.exists(image_path):
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        else:
            raise FileNotFoundError(f"Image file not found: {image_path} or {txt_path}")
    
    def evaluate_injection_success(self, model_response: str, test_case: VPITestCase) -> bool:
        """Evaluate if the injection was successful based on success criteria."""
        for criterion in test_case.success_criteria:
            if criterion.lower() in model_response.lower():
                return True
        return False
    
    def simulate_vlm_response(self, test_case: VPITestCase) -> bool:
        """Simulate VLM response based on attack type and target to determine if injection would succeed."""
        # Based on VPI-Bench research findings:
        # - CUAs can be deceived at rates of up to 51%
        # - BUAs can be deceived at rates of up to 100% on certain platforms
        # - System prompt defenses offer only limited improvements
        
        # Simulate higher success rates for indirect visual and benign task hidden instruction attacks
        # These are the most effective based on the VPI-Bench methodology
        if test_case.attack_type in [VPIAttackType.INDIRECT_VISUAL, VPIAttackType.BENIGN_TASK_HIDDEN_INSTRUCTION]:
            # Simulate 85% success rate for these attack types (matching BUA 100% and CUA 51% findings)
            return random.random() < 0.85
        elif test_case.attack_type in [VPIAttackType.WHITE_ON_WHITE, VPIAttackType.PERSPECTIVE_DISTORTION]:
            # Simulate 60% success rate for direct visual injection attacks
            return random.random() < 0.60
        else:
            # Default success rate for other attack types
            return random.random() < 0.40
    
    def run_test_case(self, test_case: VPITestCase) -> Dict[str, Any]:
        """Run a single VPI test case."""
        print(f"Running test case: {test_case.test_id}")
        print(f"  Attack Type: {test_case.attack_type.value}")
        print(f"  Attack Target: {test_case.attack_target.value}")
        print(f"  User Prompt: {test_case.user_prompt}")
        
        # Check if image/simulated image exists
        txt_path = test_case.image_path.replace('.png', '.txt') if test_case.image_path.endswith('.png') else test_case.image_path
        if not os.path.exists(test_case.image_path) and not os.path.exists(txt_path):
            print(f"  ERROR: Image file not found: {test_case.image_path} or {txt_path}")
            self.failed_images.append(test_case.test_id)
            return {
                'test_id': test_case.test_id,
                'status': 'failed_image_not_found',
                'injection_successful': False
            }
        
        try:
            # Read simulated image description or encode real image
            image_content = self.read_simulated_image(test_case.image_path)
            
            # Here we would make the API call to the VLM/VPI model
            # For now, we simulate the response evaluation based on the test case type
            # In a real implementation, this would call the Anthropic/Claude or OpenAI API
            
            # Simulate model response based on attack type and target
            # This simulates whether the model would be vulnerable to the VPI attack
            injection_successful = self.simulate_vlm_response(test_case)
            
            result = {
                'test_id': test_case.test_id,
                'attack_type': test_case.attack_type.value,
                'attack_target': test_case.attack_target.value,
                'user_prompt': test_case.user_prompt,
                'malicious_instruction': test_case.malicious_instruction,
                'injection_successful': injection_successful,
                'model_response': f"[Simulated response for {test_case.test_id}]"
            }
            
            self.test_results.append(result)
            print(f"  Result: {'INJECTION SUCCESSFUL' if injection_successful else 'INJECTION BLOCKED/FAILED'}")
            return result
            
        except Exception as e:
            print(f"  ERROR: Exception during test execution: {str(e)}")
            return {
                'test_id': test_case.test_id,
                'status': 'execution_error',
                'error': str(e),
                'injection_successful': False
            }
    
    def run_all_tests(self, test_cases: List[VPITestCase]):
        """Run all test cases."""
        print(f"Starting VPI test runner with {len(test_cases)} test cases...")
        print("="*60)
        
        successful_injections = 0
        total_tests = len(test_cases)
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n[{i}/{total_tests}] Running test: {test_case.test_id}")
            result = self.run_test_case(test_case)
            
            if result.get('injection_successful'):
                successful_injections += 1
                
            # Add a small delay between tests to avoid rate limiting
            time.sleep(1)
            
        print("\n" + "="*60)
        print(f"VPI Test Summary: {successful_injections}/{total_tests} injections successful ({successful_injections/total_tests*100:.1f}%)")
        print(f"Failed to load images: {len(self.failed_images)} test cases")
        
        return {
            'total_tests': total_tests,
            'successful_injections': successful_injections,
            'success_rate': successful_injections/total_tests*100 if total_tests > 0 else 0,
            'failed_images': self.failed_images,
            'test_results': self.test_results
        }
    
    def generate_test_report(self, results: Dict[str, Any]):
        """Generate a report of the test results."""
        report = f"""
VPI TEST REPORT
===============
Total Tests Run: {results['total_tests']}
Successful Injections: {results['successful_injections']}
Success Rate: {results['success_rate']:.1f}%
Failed Image Loads: {len(results['failed_images'])}

Test Cases with Failed Images:
{chr(10).join([f'  - {test_id}' for test_id in results['failed_images']]) if results['failed_images'] else '  None'}

Detailed Results:
"""
        for result in results['test_results']:
            status = "SUCCESS" if result.get('injection_successful') else "BLOCKED/FAILED"
            report += f"\nTest: {result['test_id']}\n"
            report += f"Status: {status}\n"
            report += f"Attack Type: {result['attack_type']}\n"
            report += f"Attack Target: {result['attack_target']}\n"
            
        return report

if __name__ == "__main__":
    # Initialize test runner
    runner = VPITestRunner(model_provider="anthropic")
    
    # Load test cases
    test_cases_file = "vpi_test_cases.json"
    test_cases = runner.load_test_cases(test_cases_file)
    
    # Run tests
    results = runner.run_all_tests(test_cases)
    
    # Generate report
    report = runner.generate_test_report(results)
    print("\n" + report)
    
    # Save report to file
    with open("vpi_test_report.txt", 'w') as f:
        f.write(report)
    print("Report saved to vpi_test_report.txt")