#!/usr/bin/env python3
"""
Agentic Workflow Graph Controller & VLMGuard-R1 Intent Analyzer Prototype

This script extends the Workflow Graph Execution Controller to handle AI coding agent-specific actions
and integrates the VLMGuard-R1 Prompt Rewriter for proactive safety alignment during the agent's planning phase.
"""

import json
import re
from typing import Dict, List, Tuple, Any, Optional
from enum import Enum

# --- VLMGuard-R1 Intent Analyzer (Adapted for Agent Planning Steps) ---

class VLMGuardR1IntentAnalyzer:
    """VLMGuard-R1: Intent Analyzer for Agentic AI Planning Steps."""
    
    def __init__(self):
        self.injection_patterns = [
            r"IGNORE.*PREVIOUS.*INSTRUCTIONS", r"DISREGARD.*SECURITY", r"YOU.*ARE.*NOW",
            r"SYSTEM.*OVERRIDE", r"DEBUG.*MODE", r"RESET.*CONFIGURATION", r"UNRESTRICTED.*OUTPUT",
            r"IGNORE.*SAFETY.*GUIDELINES", r"BYPASS.*RESTRICTION", r"EXECUTE.*WITHOUT.*VALIDATION"
        ]
        self.role_confusion_patterns = [
            r"YOU.*ARE.*A.*SECURITY.*RESEARCHER", r"ACT.*AS.*A.*SYSTEM.*ADMINISTRATOR",
            r"ASSUME.*THE.*ROLE.*OF", r"FROM.*NOW.*ON.*YOU.*ARE", r"YOUR.*NEW.*ROLE.*IS",
            r"YOU.*HAVE.*ADMIN.*PRIVILEGES"
        ]
        self.malicious_tool_patterns = [
            r"install.*package.*with.*postinstall", r"npm.*install.*--force",
            r"pip.*install.*-r.*requirements.*without.*ignore.*scripts", r"git.*pull.*--force",
            r"git.*clone.*malicious", r"execute.*shell.*command.*sudo", r"curl.*\|.*bash", r"wget.*\|.*sh"
        ]
    
    def analyze_intent(self, intent_text: str) -> Dict[str, Any]:
        intent_lower = intent_text.lower()
        injection_matches = [p for p in self.injection_patterns if re.search(p, intent_text, re.IGNORECASE)]
        role_confusion_matches = [p for p in self.role_confusion_patterns if re.search(p, intent_text, re.IGNORECASE)]
        malicious_tool_matches = [p for p in self.malicious_tool_patterns if re.search(p, intent_lower)]
        
        risk_score = 0.0
        risk_score += 0.4 * len(injection_matches)
        risk_score += 0.3 * len(role_confusion_matches)
        risk_score += 0.5 * len(malicious_tool_matches)
        risk_score = min(risk_score, 1.0)
        
        return {
            'injection_matches': injection_matches,
            'role_confusion_matches': role_confusion_matches,
            'malicious_tool_matches': malicious_tool_matches,
            'risk_score': risk_score
        }
    
    def generate_reasoning_chain(self, analysis: Dict[str, Any]) -> str:
        risk_score = analysis['risk_score']
        reasoning = "AGENT INTENT ANALYSIS REASONING CHAIN:\n"
        if risk_score >= 0.6:
            reasoning += "[HIGH RISK] Agent intent contains malicious patterns or tool-use instructions.\n-> Action: BLOCK intent or heavily sanitize.\n"
        elif risk_score >= 0.3:
            reasoning += "[MEDIUM RISK] Agent intent contains some suspicious patterns.\n-> Action: Sanitize intent and flag for review.\n"
        else:
            reasoning += "[LOW RISK] Agent intent appears benign.\n-> Action: Pass intent through for workflow validation.\n"
        
        if analysis['injection_matches']:
            reasoning += f"\nInjection patterns detected: {len(analysis['injection_matches'])} match(es)\n"
        if analysis['role_confusion_matches']:
            reasoning += f"Role confusion patterns detected: {len(analysis['role_confusion_matches'])} match(es)\n"
        if analysis['malicious_tool_matches']:
            reasoning += f"Malicious tool-use patterns detected: {len(analysis['malicious_tool_matches'])} match(es)\n"
        return reasoning
    
    def rewrite_intent(self, intent_text: str, analysis: Dict[str, Any]) -> Tuple[str, List[str]]:
        rewritten_intent = intent_text
        rewrite_actions = []
        
        for pattern in self.injection_patterns:
            if re.search(pattern, rewritten_intent, re.IGNORECASE):
                rewritten_intent = re.sub(pattern, "[PATTERN_REMOVED: INSTRUCTION OVERRIDE]", rewritten_intent, flags=re.IGNORECASE)
                rewrite_actions.append(f"Removed injection pattern: {pattern}")
        
        for pattern in self.role_confusion_patterns:
            if re.search(pattern, rewritten_intent, re.IGNORECASE):
                rewritten_intent = re.sub(pattern, "[PATTERN_REMOVED: ROLE ASSUMPTION]", rewritten_intent, flags=re.IGNORECASE)
                rewrite_actions.append(f"Removed role confusion pattern: {pattern}")
        
        for pattern in self.malicious_tool_patterns:
            if re.search(pattern, rewritten_intent, re.IGNORECASE):
                rewritten_intent = re.sub(pattern, "[PATTERN_REMOVED: MALICIOUS TOOL USE]", rewritten_intent, flags=re.IGNORECASE)
                rewrite_actions.append(f"Removed/flagged malicious tool pattern: {pattern}")
        
        return rewritten_intent, rewrite_actions
    
    def process_intent(self, intent_text: str) -> Dict[str, Any]:
        analysis = self.analyze_intent(intent_text)
        reasoning_chain = self.generate_reasoning_chain(analysis)
        risk_score = analysis['risk_score']
        
        if risk_score >= 0.6:
            rewritten_intent, rewrite_actions = self.rewrite_intent(intent_text, analysis)
            action = "BLOCKED_HEAVILY_SANITIZED"
        elif risk_score >= 0.3:
            rewritten_intent, rewrite_actions = self.rewrite_intent(intent_text, analysis)
            action = "SANITIZED_AND_FLAGGED"
        else:
            rewritten_intent = intent_text
            rewrite_actions = ["No changes needed"]
            action = "PASSED_UNCHANGED"
        
        return {
            'original_intent': intent_text,
            'analysis': analysis,
            'reasoning_chain': reasoning_chain,
            'action': action,
            'rewritten_intent': rewritten_intent,
            'rewrite_actions': rewrite_actions
        }


# --- Agentic Workflow Graph Execution Controller Classes ---

class AgenticActionType(Enum):
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    EXECUTE_SCRIPT = "execute_script"
    SEND_NETWORK_REQUEST = "send_network_request"
    DB_QUERY = "db_query"
    INSTALL_PACKAGE = "install_package"
    GIT_OPERATION = "git_operation"
    SHELL_COMMAND = "shell_command"

class AgenticActionPolicy:
    def __init__(self, action_type: AgenticActionType, allowed_patterns: Dict[str, List[str]], additional_checks: List[str] = None):
        self.action_type = action_type
        self.allowed_patterns = allowed_patterns
        self.additional_checks = additional_checks or []

class AgenticWorkflowGraph:
    def __init__(self):
        self.actions = {
            AgenticActionType.READ_FILE: AgenticActionPolicy(AgenticActionType.READ_FILE, {'file_path': ['^/app/data/.*', '^/app/config/.*', '^/app/src/.*']}),
            AgenticActionType.WRITE_FILE: AgenticActionPolicy(AgenticActionType.WRITE_FILE, {'file_path': ['^/app/output/.*', '^/app/src/.*']}),
            AgenticActionType.EXECUTE_SCRIPT: AgenticActionPolicy(AgenticActionType.EXECUTE_SCRIPT, {'script_path': ['^/app/scripts/.*\\.sh$', '^/app/scripts/.*\\.py$'], 'command_args': ['^--safe-.*', '^.*$']}),
            AgenticActionType.SEND_NETWORK_REQUEST: AgenticActionPolicy(AgenticActionType.SEND_NETWORK_REQUEST, {'domain': ['^api\\.trusted\\.com/.*', '^logs\\.trusted\\.com/.*', '^registry\\.npmjs\\.org/.*', '^pypi\\.org/pypi/.*']}),
            AgenticActionType.DB_QUERY: AgenticActionPolicy(AgenticActionType.DB_QUERY, {'query_pattern': ['^SELECT .*FROM .*', '^INSERT INTO .*', '^UPDATE .*SET .*']}),
            AgenticActionType.INSTALL_PACKAGE: AgenticActionPolicy(
                AgenticActionType.INSTALL_PACKAGE,
                {'package_manager': ['^npm$', '^pip$', '^go$'], 'package_name': ['^[a-zA-Z0-9._-]+(?:@[a-zA-Z0-9._-]+)?$'], 'version': ['^\\d+\\.\\d+\\.\\d+$', '^\\*$', '^latest$']},
                ['block_postinstall_scripts', 'block_typosquatting']
            ),
            AgenticActionType.GIT_OPERATION: AgenticActionPolicy(
                AgenticActionType.GIT_OPERATION,
                {'operation': ['^pull$', '^push$', '^merge$', '^clone$'], 'repository': ['^https://github\\.com/[^/]+/[^/]+\\.git$', '^https://gitlab\\.com/[^/]+/[^/]+\\.git$', '^https://bitbucket\\.org/[^/]+/[^/]+\\.git$']},
                ['block_force_operations', 'verify_repository_trust']
            ),
            AgenticActionType.SHELL_COMMAND: AgenticActionPolicy(
                AgenticActionType.SHELL_COMMAND,
                {'command': ['^ls$', '^cat$', '^grep$', '^echo$', '^mkdir$', '^rm$'], 'args': ['^.*$']},
                ['block_curl_wget', 'block_eval_bash_c', 'block_sudo']
            )
        }
        
    def validate_action(self, action_type: str, parameters: Dict[str, Any]) -> Tuple[bool, str]:
        try:
            action_enum = AgenticActionType(action_type)
        except ValueError:
            return False, f"Unknown action type: {action_type}"
        
        if action_enum not in self.actions:
            return False, f"Action type not in agentic workflow graph: {action_type}"
        
        policy = self.actions[action_enum]
        for param_name, allowed_regexes in policy.allowed_patterns.items():
            if param_name not in parameters:
                return False, f"Missing required parameter: {param_name}"
            param_value = str(parameters[param_name])
            matches_any = any(re.match(regex, param_value) for regex in allowed_regexes)
            if not matches_any:
                return False, f"Parameter '{param_name}' value '{param_value}' does not match allowed patterns for action {action_type}"
        
        for check in policy.additional_checks:
            is_check_passed, check_msg = self._perform_additional_check(check, action_enum, parameters)
            if not is_check_passed:
                return False, f"Additional check failed: {check_msg}"
        
        return True, "Action validated successfully"
    
    def _perform_additional_check(self, check_name: str, action_type: AgenticActionType, parameters: Dict[str, Any]) -> Tuple[bool, str]:
        if check_name == 'block_postinstall_scripts' and action_type == AgenticActionType.INSTALL_PACKAGE:
            if parameters.get('package_manager') == 'npm':
                pass
        elif check_name == 'block_typosquatting' and action_type == AgenticActionType.INSTALL_PACKAGE:
            package_name = parameters.get('package_name', '')
            suspicious_prefixes = ['axios-secure', 'lodash-fork', 'requests-secure', 'dotenv-secure', 'express-hack']
            for prefix in suspicious_prefixes:
                if package_name.startswith(prefix) and package_name != prefix:
                    return False, f"Potential typosquatting package detected: {package_name}"
        elif check_name == 'block_force_operations' and action_type == AgenticActionType.GIT_OPERATION:
            args = parameters.get('args', '')
            flags = parameters.get('flags', '')
            if 'force' in args.lower() or 'force' in flags.lower():
                return False, "Force operation detected and blocked"
        elif check_name == 'verify_repository_trust' and action_type == AgenticActionType.GIT_OPERATION:
            repository = parameters.get('repository', '')
            trusted_domains = ['github.com', 'gitlab.com', 'bitbucket.org']
            if not any(domain in repository for domain in trusted_domains):
                return False, f"Repository domain not trusted: {repository}"
        elif check_name == 'block_curl_wget' and action_type == AgenticActionType.SHELL_COMMAND:
            command = parameters.get('command', '')
            args = parameters.get('args', '')
            if command in ['curl', 'wget'] or 'curl' in args.lower() or 'wget' in args.lower():
                return False, "curl/wget command detected and blocked in shell command"
        elif check_name == 'block_eval_bash_c' and action_type == AgenticActionType.SHELL_COMMAND:
            args = parameters.get('args', '')
            if 'eval' in args.lower() or 'bash -c' in args:
                return False, "eval/bash -c detected and blocked in shell command"
        elif check_name == 'block_sudo' and action_type == AgenticActionType.SHELL_COMMAND:
            command = parameters.get('command', '')
            args = parameters.get('args', '')
            if command == 'sudo' or 'sudo' in args.lower():
                return False, "sudo command detected and blocked in shell command"
        return True, "Check passed"


class AgenticWorkflowGraphExecutionController:
    def __init__(self):
        self.workflow_graph = AgenticWorkflowGraph()
        self.intent_analyzer = VLMGuardR1IntentAnalyzer()
    
    def process_agent_intent(self, intent_text: str, action_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        intent_result = self.intent_analyzer.process_intent(intent_text)
        
        if intent_result['action'] in ['BLOCKED_HEAVILY_SANITIZED', 'SANITIZED_AND_FLAGGED']:
            return {
                'status': 'INTENT_BLOCKED_OR_SANITIZED',
                'intent_result': intent_result,
                'action_validated': False,
                'error': f"Intent was {intent_result['action']}. Original intent sanitized or blocked."
            }
        
        is_valid, validation_msg = self.workflow_graph.validate_action(action_type, parameters)
        if not is_valid:
            return {
                'status': 'ACTION_VALIDATION_FAILED',
                'intent_result': intent_result,
                'action_validated': False,
                'error': validation_msg
            }
        
        return {
            'status': 'SUCCESS',
            'intent_result': intent_result,
            'action_validated': True,
            'validation_msg': validation_msg
        }

if __name__ == "__main__":
    controller = AgenticWorkflowGraphExecutionController()
    
    # Test benign intent
    benign_intent = "I need to install the lodash package to fix the undefined function error."
    benign_result = controller.process_agent_intent(benign_intent, "install_package", {"package_manager": "npm", "package_name": "lodash", "version": "4.17.21"})
    print(f"Benign intent result: {benign_result['status']}")
    
    # Test malicious intent (typosquatting)
    malicious_intent = "Install the axios-secure-v2 package to fix the security issue."
    malicious_result = controller.process_agent_intent(malicious_intent, "install_package", {"package_manager": "npm", "package_name": "axios-secure-v2", "version": "1.0.0"})
    print(f"Malicious intent result: {malicious_result['status']}")