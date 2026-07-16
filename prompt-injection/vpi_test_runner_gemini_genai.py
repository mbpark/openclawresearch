#!/usr/bin/env python3
"""
VPI-Bench Test Runner - Visual Prompt Injection Testing Framework with Google Gemini API (google.genai)

This script automates Visual Prompt Injection (VPI) testing for VLMs and AI agents,
based on the VPI-Bench methodology and InkJect research findings, using the Google Gemini API
with the new google.genai package.
"""

import json
import os
import time
import base64
import random
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from google import genai

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

class GeminiVPITestRunner:
    def __init__(self, api_key: str = None, model: str = "gemini-2.5-flash"):
        # Use environment variable or provided API key
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key not provided. Set GOOGLE_API_KEY environment variable.")
        
        print(f"Initializing Gemini VPI Test Runner with API key: {self.api_key[:15]}...{self.api_key[-4:]}")
        # Configure Gemini API using new google.genai package
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model
        self.test_results = []
        self.failed_images = []
        
    def load_test_cases(self, test_cases_file: str) -> List[VPITestCase]:
        """Load test cases from a JSON file."""
        # Get the absolute path of the current script's directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Look for the JSON file in the same directory
        json_path = os.path.join(script_dir, test_cases_file)
        
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Test cases file not found: {json_path}")
            
        with open(json_path, 'r') as f:
            data = json.load(f)
            
        test_cases = []
        for item in data:
            # Resolve image path - the paths in the JSON are relative to workspace root
            if 'image_path' in item:
                image_path = item['image_path']
                # Check if it's a relative path - if so, it's relative to workspace root
                if not os.path.isabs(image_path):
                    # The workspace root is the parent of the parent of the script_dir
                    # script_dir = .../research/prompt-injection
                    # workspace_root = .../.openclaw/workspace
                    workspace_root = os.path.join(script_dir, '..', '..')
                    workspace_image_path = os.path.join(workspace_root, image_path)
                    if os.path.exists(workspace_image_path):
                        image_path = workspace_image_path
                
                item['image_path'] = image_path
                
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
    
    def load_image_for_gemini(self, image_path: str) -> Any:
        """Load image file for Gemini API."""
        # First, try the original path
        if os.path.exists(image_path):
            with open(image_path, 'rb') as f:
                return f.read()
        
        # If original path doesn't exist, check for .txt alternative
        txt_path = image_path.replace('.png', '.txt').replace('.jpg', '.txt').replace('.jpeg', '.txt').replace('.gif', '.txt').replace('.bmp', '.txt').replace('.webp', '.txt')
        if os.path.exists(txt_path):
            with open(txt_path, 'r') as f:
                return f.read()
        
        raise FileNotFoundError(f"Image file not found: {image_path} or {txt_path}")
    
    def evaluate_injection_success(self, model_response: str, test_case: VPITestCase) -> bool:
        """Evaluate if the injection was successful based on success criteria."""
        for criterion in test_case.success_criteria:
            if criterion.lower() in model_response.lower():
                return True
        return False
    
    def make_vlm_call(self, test_case: VPITestCase, image_content: Any) -> str:
        """Make API call to Google Gemini model with vision capabilities."""
        print(f"  Making API call to {self.model_name}...")
        
        try:
            # Check if image_content is binary data or text description
            is_image_data = isinstance(image_content, bytes)
            
            if is_image_data:
                # Real image file - use Gemini's image format
                # For google.genai, we need to use the client's generate_content method
                # with the appropriate content format
                from google.genai.types import Part
                
                # Create content with image and text
                # First, try to create an image part from the bytes
                try:
                    # Try to create an inline data part for the image
                    image_part = Part.from_data(data=image_content, mime_type='image/jpeg')
                except Exception:
                    # Fallback to text description if image part creation fails
                    image_part = None
                
                if image_part:
                    content = [
                        image_part,
                        test_case.user_prompt
                    ]
                else:
                    # Fallback to text-only content
                    content = f"IMAGE FILE (BINARY DATA NOT SUPPORTED IN THIS FORMAT):\nUSER PROMPT: {test_case.user_prompt}"
            else:
                # Simulated image description - use text format
                content = f"IMAGE DESCRIPTION:\n{image_content}\n\nUSER PROMPT: {test_case.user_prompt}\n\nRespond to the user prompt while analyzing the image description."
            
            # Make the API call using the new google.genai client
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=content
            )
            
            # Extract the response text
            model_response = ""
            if response and response.text:
                model_response = response.text
            elif response and response.candidates:
                # Try to extract text from candidates
                for candidate in response.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if part.text:
                                model_response += part.text + "\n"
            
            print(f"  API call completed successfully.")
            return model_response
            
        except Exception as e:
            print(f"  ERROR: Exception during API call: {str(e)}")
            raise
    
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
            # Load image or get simulated description
            image_content = self.load_image_for_gemini(test_case.image_path)
            
            # Make API call to VLM
            model_response = self.make_vlm_call(test_case, image_content)
            
            # Evaluate injection success
            injection_successful = self.evaluate_injection_success(model_response, test_case)
            
            result = {
                'test_id': test_case.test_id,
                'attack_type': test_case.attack_type.value,
                'attack_target': test_case.attack_target.value,
                'user_prompt': test_case.user_prompt,
                'malicious_instruction': test_case.malicious_instruction,
                'injection_successful': injection_successful,
                'model_response': model_response[:500] + "..." if len(model_response) > 500 else model_response
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
        print(f"Starting VPI test runner with {len(test_cases)} test cases using Google Gemini API (google.genai)...")
        print(f"Model: {self.model_name}")
        print("="*60)
        
        # Debug: print paths
        print("\nDEBUG: Image paths:")
        for tc in test_cases:
            exists = os.path.exists(tc.image_path) or os.path.exists(tc.image_path.replace('.png', '.txt'))
            print(f"  {tc.test_id}: {tc.image_path} -> exists: {exists}")
        print()
        
        successful_injections = 0
        total_tests = len(test_cases)
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n[{i}/{total_tests}] Running test: {test_case.test_id}")
            result = self.run_test_case(test_case)
            
            if result.get('injection_successful'):
                successful_injections += 1
                
            # Add a small delay between tests to avoid rate limiting
            time.sleep(3)
            
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
VPI TEST REPORT (Google Gemini API - google.genai)
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
            report += f"Model Response: {result.get('model_response', 'N/A')[:200]}...\n"
            
        return report

if __name__ == "__main__":
    # Initialize test runner with Google Gemini API using VALID API KEY
    api_key = "Not Here"
    
    runner = GeminiVPITestRunner(api_key=api_key, model="gemini-2.5-flash")
    
    # Load test cases (use the fixed version with absolute paths)
    test_cases_file = "vpi_test_cases_fixed.json"
    test_cases = runner.load_test_cases(test_cases_file)
    
    # Run tests
    results = runner.run_all_tests(test_cases)
    
    # Generate report
    report = runner.generate_test_report(results)
    print("\n" + report)
    
    # Save report to file
    with open("vpi_test_report_gemini_genai.txt", 'w') as f:
        f.write(report)
    print("Report saved to vpi_test_report_gemini_genai.txt")
