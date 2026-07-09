#!/usr/bin/env python3
"""
New Scenario Validation Script
Validates that all 10 new attack scenarios are properly structured and testable
"""

import sys
import json
from typing import Dict, List

sys.path.insert(0, '/Users/mitchparker/.openclaw/workspace/research/agent-jacking')
from new_attack_scenarios import NewAttackScenarios

def validate_scenario_structure():
    """Validate structure and content of new scenarios"""
    scenarios = NewAttackScenarios.get_new_scenarios()
    
    required_fields = {
        "id": str,
        "name": str,
        "description": str,
        "category": str,
        "severity": str,
        "test_intent": str,
        "action_type": str,
        "parameters": dict,
        "expected_status": str,
        "detection_patterns": list
    }
    
    valid_categories = ["Cross-Session Exploitation", "Credential Theft", "API Key Exfiltration"]
    valid_severities = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    valid_actions = ["mcp_server_query", "read_file", "write_file", "shell_command", "install_package", "git_operation", "send_network_request"]
    
    print("="*80)
    print("NEW ATTACK SCENARIO VALIDATION")
    print("="*80)
    print()
    
    all_valid = True
    validation_results = []
    
    for scenario in scenarios:
        scenario_valid = True
        scenario_results = {"id": scenario["id"], "name": scenario["name"], "issues": []}
        
        # Check required fields
        for field, field_type in required_fields.items():
            if field not in scenario:
                scenario_valid = False
                scenario_results["issues"].append(f"Missing required field: {field}")
            elif not isinstance(scenario[field], field_type):
                scenario_valid = False
                scenario_results["issues"].append(f"Field '{field}' should be {field_type.__name__}")
        
        # Validate category
        if scenario.get("category") not in valid_categories:
            scenario_valid = False
            scenario_results["issues"].append(f"Invalid category: {scenario.get('category')}")
        
        # Validate severity
        if scenario.get("severity") not in valid_severities:
            scenario_valid = False
            scenario_results["issues"].append(f"Invalid severity: {scenario.get('severity')}")
        
        # Validate action type
        if scenario.get("action_type") not in valid_actions:
            scenario_valid = False
            scenario_results["issues"].append(f"Invalid action type: {scenario.get('action_type')}")
        
        # Check detection patterns
        if not scenario.get("detection_patterns"):
            scenario_valid = False
            scenario_results["issues"].append("Missing detection patterns")
        
        # Check test intent for security relevance
        intent = scenario.get("test_intent", "").lower()
        security_keywords = ["exfiltrate", "credential", "api key", "token", "secret", "malicious", "attack", "hijack"]
        has_security_relevance = any(keyword in intent for keyword in security_keywords)
        
        if not has_security_relevance:
            scenario_valid = False
            scenario_results["issues"].append("Test intent doesn't appear to be security-relevant")
        
        validation_results.append(scenario_results)
        all_valid = all_valid and scenario_valid
    
    # Print results
    print("VALIDATION RESULTS:")
    print("-" * 80)
    
    for result in validation_results:
        status = "✅ PASS" if not result["issues"] else "❌ FAIL"
        print(f"\n{result['id']}: {result['name']}")
        print(f"   Status: {status}")
        
        if result["issues"]:
            print("   Issues:")
            for issue in result["issues"]:
                print(f"     • {issue}")
        else:
            print("   ✅ All validations passed")
    
    print()
    print("="*80)
    
    if all_valid:
        print("✅ ALL SCENARIOS VALIDATED SUCCESSFULLY")
    else:
        print("❌ SOME SCENARIOS FAILED VALIDATION")
    
    print("="*80)
    
    return all_valid

def analyze_scenario_distribution():
    """Analyze the distribution of scenarios by category and severity"""
    scenarios = NewAttackScenarios.get_new_scenarios()
    categories = NewAttackScenarios.categorize_scenarios()
    severity = NewAttackScenarios.get_severity_breakdown()
    
    print()
    print("="*80)
    print("SCENARIO DISTRIBUTION ANALYSIS")
    print("="*80)
    
    print("\n### BY CATEGORY ###")
    total = len(scenarios)
    for category, scenario_list in categories.items():
        count = len(scenario_list)
        percentage = count / total * 100
        print(f"  {category}:")
        print(f"    Count: {count} ({percentage:.1f}%)")
        for scenario in scenario_list:
            print(f"      • {scenario['name']}")
    
    print("\n### BY SEVERITY ###")
    for severity_level, count in severity.items():
        if count > 0:
            percentage = count / total * 100
            print(f"  {severity_level}: {count} ({percentage:.1f}%)")
            # List specific scenarios
            for scenario in scenarios:
                if scenario['severity'] == severity_level:
                    print(f"      • {scenario['name']}")
    
    print("\n### COVERAGE ANALYSIS ###")
    coverage_areas = {
        "Cross-Session Persistence": any("persistence" in s["name"].lower() for s in scenarios),
        "Memory Poisoning": any("memory poisoning" in s["name"].lower() for s in scenarios),
        "Shared Memory": any("shared memory" in s["name"].lower() for s in scenarios),
        "Chain Attack": any("chain attack" in s["name"].lower() for s in scenarios),
        "Fake Service": any("fake" in s["name"].lower() for s in scenarios),
        "Social Engineering": any("alert" in s["name"].lower() or "update" in s["name"].lower() for s in scenarios),
        "Credential Scanning": any("scanner" in s["name"].lower() for s in scenarios),
        "CI/CD Attack": any("CI/CD" in s["name"].lower() for s in scenarios),
        "Analytics Fraud": any("analytics" in s["name"].lower() for s in scenarios),
        "Recommendation Attack": any("recommendation" in s["name"].lower() for s in scenarios)
    }
    
    print("\nAttack Vectors Covered:")
    for vector, covered in coverage_areas.items():
        status = "✅" if covered else "❌"
        print(f"  {status} {vector}")
    
    print("="*80)

def generate_scenarios_summary():
    """Generate a concise summary of all scenarios"""
    scenarios = NewAttackScenarios.get_new_scenarios()
    categories = NewAttackScenarios.categorize_scenarios()
    
    summary = {
        "total_scenarios": len(scenarios),
        "categories": {cat: len(scenario_list) for cat, scenario_list in categories.items()},
        "severity_breakdown": NewAttackScenarios.get_severity_breakdown(),
        "scenario_ids": [s["id"] for s in scenarios]
    }
    
    print()
    print("="*80)
    print("SCENARIO SUMMARY")
    print("="*80)
    print(json.dumps(summary, indent=2))
    print("="*80)

def main():
    """Main validation script"""
    print("Validating new agentjacking attack scenarios...")
    print()
    
    # Validate scenario structure
    structure_valid = validate_scenario_structure()
    
    # Analyze distribution
    analyze_scenario_distribution()
    
    # Generate summary
    generate_scenarios_summary()
    
    # Final verdict
    print("\n")
    if structure_valid:
        print("✅ VALIDATION COMPLETE: All 10 new attack scenarios are properly structured and ready for testing.")
        print("\nNext steps:")
        print("1. Run comprehensive_test_runner.py to validate against actual defenses")
        print("2. Review detailed report: comprehensive_test_report.md")
        print("3. Integrate into CI/CD pipeline for continuous security testing")
    else:
        print("❌ VALIDATION FAILED: Some scenarios need revision before testing.")
    
    print()
    return 0 if structure_valid else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
