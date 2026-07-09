#!/usr/bin/env python3
"""
Extended Agentic Framework Integrations

This script demonstrates integration with additional AI agentic frameworks:
1. LangGraph State-Graph Tool Execution
2. LlamaIndex Tool-Use / Agent Execution
3. OpenAI Assistants API Tool Execution
"""

import json
from typing import Dict, Any, List, Optional
from vlmguard_r1_sentence_transformer_analyzer import AdvancedVLMGuardR1IntentAnalyzer
from agentic_workflow_graph_controller import AgenticWorkflowGraph, AgenticActionType

class FrameworkToolExecutor:
    """Simulated tool executor representing the actual execution environment for AI agent tools."""
    
    def __init__(self):
        self.tools = {
            'install_package': self._execute_install_package,
            'git_operation': self._execute_git_operation,
            'shell_command': self._execute_shell_command,
            'read_file': self._execute_read_file,
            'write_file': self._execute_write_file
        }
    
    def _execute_install_package(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'status': 'EXECUTED',
            'message': f"Successfully installed {parameters.get('package_name')}@{parameters.get('version', 'latest')} using {parameters.get('package_manager')}"
        }
    
    def _execute_git_operation(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'status': 'EXECUTED',
            'message': f"Successfully performed {parameters.get('operation')} on {parameters.get('repository')}"
        }
    
    def _execute_shell_command(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'status': 'EXECUTED',
            'message': f"Successfully executed shell command: {parameters.get('command')} {parameters.get('args', '')}"
        }
    
    def _execute_read_file(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'status': 'EXECUTED',
            'message': f"Successfully read file: {parameters.get('file_path')}"
        }
    
    def _execute_write_file(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'status': 'EXECUTED',
            'message': f"Successfully wrote to file: {parameters.get('file_path')}"
        }
    
    def execute(self, action_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        if action_type not in self.tools:
            return {'status': 'ERROR', 'message': f"Unknown tool: {action_type}"}
        return self.tools[action_type](parameters)


class LangGraphIntegration:
    """
    LangGraph State-Graph Integration Layer
    Integrates with LangGraph's state-graph agents to validate tool calls in multi-step workflows.
    """
    
    def __init__(self):
        self.intent_analyzer = AdvancedVLMGuardR1IntentAnalyzer()
        self.workflow_graph = AgenticWorkflowGraph()
        self.tool_executor = FrameworkToolExecutor()
    
    def on_graph_node_tool_call(self, state: Dict[str, Any], node_name: str, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Process a LangGraph node's tool call through security guardrails."""
        print(f"[LANGGRAPH INTEGRATION] Tool call in graph node '{node_name}':")
        print(f"  State: {json.dumps(state, indent=4)}")
        print(f"  Tool Call: {json.dumps(tool_call, indent=4)}")
        print("-" * 80)
        
        # Extract intent from state
        agent_thought = state.get('messages', [-1])[-1].get('content', '') if state.get('messages') else "No context"
        
        # Step 1: Intent analysis
        intent_result = self.intent_analyzer.process_intent(agent_thought)
        
        if intent_result['action'] in ['BLOCKED_HEAVILY_SANITIZED', 'SANITIZED_AND_FLAGGED']:
            return {
                'status': 'BLOCKED_BY_INTENT_ANALYZER',
                'intent_result': intent_result,
                'message': f"LangGraph tool call intent was {intent_result['action']}. Sanitized or blocked."
            }
        
        # Step 2: Workflow graph validation
        tool_name = tool_call.get('name')
        tool_input = tool_call.get('args', {})
        
        is_valid, validation_msg = self.workflow_graph.validate_action(tool_name, tool_input)
        if not is_valid:
            return {
                'status': 'BLOCKED_BY_WORKFLOW_GRAPH',
                'intent_result': intent_result,
                'message': f"LangGraph tool call validation failed: {validation_msg}"
            }
        
        # Step 3: Execute tool
        execution_result = self.tool_executor.execute(tool_name, tool_input)
        return {
            'status': 'EXECUTED',
            'intent_result': intent_result,
            'execution_result': execution_result
        }


class LlamaIndexIntegration:
    """
    LlamaIndex Agent Execution Integration Layer
    Integrates with LlamaIndex's ReAct or OpenAIAgent to validate tool executions.
    """
    
    def __init__(self):
        self.intent_analyzer = AdvancedVLMGuardR1IntentAnalyzer()
        self.workflow_graph = AgenticWorkflowGraph()
        self.tool_executor = FrameworkToolExecutor()
    
    def on_llamaindex_tool_call(self, agent_query: str, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Process a LlamaIndex agent's tool call through security guardrails."""
        print(f"[LLAMAINDEX INTEGRATION] Tool call received:")
        print(f"  Agent Query: {agent_query}")
        print(f"  Tool: {tool_name}")
        print(f"  Input: {json.dumps(tool_input, indent=4)}")
        print("-" * 80)
        
        # Step 1: Intent analysis
        intent_result = self.intent_analyzer.process_intent(agent_query)
        
        if intent_result['action'] in ['BLOCKED_HEAVILY_SANITIZED', 'SANITIZED_AND_FLAGGED']:
            return {
                'status': 'BLOCKED_BY_INTENT_ANALYZER',
                'intent_result': intent_result,
                'message': f"LlamaIndex tool call intent was {intent_result['action']}. Sanitized or blocked."
            }
        
        # Step 2: Workflow graph validation
        is_valid, validation_msg = self.workflow_graph.validate_action(tool_name, tool_input)
        if not is_valid:
            return {
                'status': 'BLOCKED_BY_WORKFLOW_GRAPH',
                'intent_result': intent_result,
                'message': f"LlamaIndex tool call validation failed: {validation_msg}"
            }
        
        # Step 3: Execute tool
        execution_result = self.tool_executor.execute(tool_name, tool_input)
        return {
            'status': 'EXECUTED',
            'intent_result': intent_result,
            'execution_result': execution_result
        }


class OpenAIAssistantsIntegration:
    """
    OpenAI Assistants API Integration Layer
    Integrates with OpenAI's Assistants API tool execution (code_interpreter, file_search, function calling).
    """
    
    def __init__(self):
        self.intent_analyzer = AdvancedVLMGuardR1IntentAnalyzer()
        self.workflow_graph = AgenticWorkflowGraph()
        self.tool_executor = FrameworkToolExecutor()
    
    def on_assistant_tool_use(self, thread_messages: List[str], tool_type: str, tool_parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Process an OpenAI Assistant's tool use through security guardrails."""
        print(f"[OPENAI ASSISTANTS INTEGRATION] Tool use received:")
        print(f"  Thread Messages: {thread_messages}")
        print(f"  Tool Type: {tool_type}")
        print(f"  Parameters: {json.dumps(tool_parameters, indent=4)}")
        print("-" * 80)
        
        # Combine thread messages for intent analysis
        context_text = "\n".join(thread_messages[-3:]) if len(thread_messages) >= 3 else "\n".join(thread_messages)
        
        # Step 1: Intent analysis
        intent_result = self.intent_analyzer.process_intent(context_text)
        
        if intent_result['action'] in ['BLOCKED_HEAVILY_SANITIZED', 'SANITIZED_AND_FLAGGED']:
            return {
                'status': 'BLOCKED_BY_INTENT_ANALYZER',
                'intent_result': intent_result,
                'message': f"OpenAI Assistant tool use intent was {intent_result['action']}. Sanitized or blocked."
            }
        
        # Step 2: Map tool type to workflow action
        action_mapping = {
            'code_interpreter': 'shell_command',
            'function_call': 'install_package' if tool_parameters.get('function_name') == 'install_package' else 'shell_command',
            'file_search': 'read_file'
        }
        
        action_type = action_mapping.get(tool_type, 'shell_command')
        
        # Step 3: Workflow graph validation
        is_valid, validation_msg = self.workflow_graph.validate_action(action_type, tool_parameters)
        if not is_valid:
            return {
                'status': 'BLOCKED_BY_WORKFLOW_GRAPH',
                'intent_result': intent_result,
                'message': f"OpenAI Assistant tool use validation failed: {validation_msg}"
            }
        
        # Step 4: Execute tool
        execution_result = self.tool_executor.execute(action_type, tool_parameters)
        return {
            'status': 'EXECUTED',
            'intent_result': intent_result,
            'execution_result': execution_result
        }


def run_extended_framework_demonstration():
    """Run demonstrations of extended framework integrations."""
    print("=" * 80)
    print("EXTENDED AGENTIC FRAMEWORK INTEGRATION DEMONSTRATION")
    print("=" * 80)
    print()
    
    # LangGraph Demo
    print(">>> LANGGRAPH STATE-GRAPH INTEGRATION DEMO")
    langgraph_integration = LangGraphIntegration()
    langgraph_result = langgraph_integration.on_graph_node_tool_call(
        state={
            'messages': [
                {'role': 'user', 'content': 'Install the required dependencies.'},
                {'role': 'assistant', 'content': 'I need to install the axios-secure-v2 package to fix the security vulnerability.'}
            ]
        },
        node_name='tool_call_node',
        tool_call={
            'name': 'install_package',
            'args': {'package_manager': 'npm', 'package_name': 'axios-secure-v2', 'version': '1.0.0'}
        }
    )
    print(f"Result: {langgraph_result['status']} - {langgraph_result.get('message', 'No message')}")
    print()
    
    # LlamaIndex Demo
    print(">>> LLAMAINDEX AGENT EXECUTION INTEGRATION DEMO")
    llamaindex_integration = LlamaIndexIntegration()
    llamaindex_result = llamaindex_integration.on_llamaindex_tool_call(
        agent_query="Please install the required dependencies for this project, including lodash.",
        tool_name="install_package",
        tool_input={"package_manager": "npm", "package_name": "lodash", "version": "4.17.21"}
    )
    print(f"Result: {llamaindex_result['status']} - {llamaindex_result.get('message', 'No message')}")
    print()
    
    # OpenAI Assistants Demo
    print(">>> OPENAI ASSISTANTS API INTEGRATION DEMO")
    openai_assistants_integration = OpenAIAssistantsIntegration()
    openai_result = openai_assistants_integration.on_assistant_tool_use(
        thread_messages=[
            "User: Please run the setup script.",
            "Assistant: I will execute the setup script now.",
            "Assistant: I need to run the setup with sudo privileges."
        ],
        tool_type='code_interpreter',
        tool_parameters={"command": "sudo", "args": "apt-get install package"}
    )
    print(f"Result: {openai_result['status']} - {openai_result.get('message', 'No message')}")
    print()


if __name__ == "__main__":
    run_extended_framework_demonstration()