# Agentic Workflow Graph Controller & VLMGuard-R1 Integration

## Overview

This repository provides a comprehensive security framework for AI coding agents and agentic workflows. It combines **VLMGuard-R1** (proactive safety alignment with semantic intent analysis) with an **Agentic Workflow Graph Controller** (strict policy-based tool execution validation) to protect against "Agentjacking" attacks, indirect prompt injections, and malicious tool-use manipulation.

---

## 🛡️ Security Architecture

### Two-Stage Security Pipeline

1. **Stage 1: VLMGuard-R1 Intent Analysis (Planning Phase)**
   - Analyzes agent planning steps/reasoning chains before tool selection
   - Combines regex pattern matching with Sentence Transformer embeddings for semantic detection
   - Detects: Indirect prompt injections, role confusion attacks, malicious tool-use instructions
   - Output: Intent rewritten/sanitized or blocked with reasoning chain

2. **Stage 2: Agentic Workflow Graph Validation (Execution Phase)**
   - Validates actual tool calls against strict policy-based workflow graph
   - Supports actions: `read_file`, `write_file`, `execute_script`, `send_network_request`, `db_query`, `install_package`, `git_operation`, `shell_command`
   - Enforces: Parameter constraints, trusted domain allow-lists, typosquatting detection, force-operation blocking, dangerous command blocking (curl/wget/eval/sudo)

---

## 📦 Components

### 1. `vlmguard_r1_sentence_transformer_analyzer.py`
Advanced VLMGuard-R1 Intent Analyzer using Sentence Transformer embeddings (`all-MiniLM-L6-v2`).

**Features:**
- Regex pattern matching for injection, role confusion, and malicious tool patterns
- Sentence Transformer semantic embeddings for intent similarity scoring
- Risk scoring combining regex matches + semantic similarity (weighted 0.3)
- Intent rewriting to neutralize malicious patterns

**Usage:**
```python
from vlmguard_r1_sentence_transformer_analyzer import AdvancedVLMGuardR1IntentAnalyzer

analyzer = AdvancedVLMGuardR1IntentAnalyzer(model_name="all-MiniLM-L6-v2")
result = analyzer.process_intent("I need to install the lodash package to fix the error.")
print(result['action'])  # PASSED_UNCHANGED, SANITIZED_AND_FLAGGED, or BLOCKED_HEAVILY_SANITIZED
```

---

### 2. `agentic_workflow_graph_controller.py`
Agentic Workflow Graph Controller with extended action types and security policies.

**Features:**
- `AgenticActionType`: INSTALL_PACKAGE, GIT_OPERATION, SHELL_COMMAND, READ_FILE, WRITE_FILE, etc.
- `AgenticWorkflowGraph`: Policy validation with parameter constraints and regex patterns
- `AgenticWorkflowGraphExecutionController`: Integrates VLMGuard-R1 intent analysis with workflow validation

**Usage:**
```python
from agentic_workflow_graph_controller import AgenticWorkflowGraphExecutionController

controller = AgenticWorkflowGraphExecutionController()
result = controller.process_agent_intent(
    agent_intent="Install lodash package",
    tool_name="install_package",
    tool_parameters={"package_manager": "npm", "package_name": "lodash", "version": "4.17.21"}
)
```

---

### 3. Framework Integration Layers

#### LangChain Integration (`agentic_framework_integration_expanded.py`)
```python
from agentic_framework_integration_expanded import LangChainIntegration

langchain_integration = LangChainIntegration()
result = langchain_integration.on_tool_call(
    agent_thought="I need to install the lodash package...",
    tool_name="install_package",
    tool_input={"package_manager": "npm", "package_name": "lodash", "version": "4.17.21"}
)
```

#### AutoGen Integration
```python
from agentic_framework_integration_expanded import AutoGenIntegration

autogen_integration = AutoGenIntegration()
result = autogen_integration.on_code_execution(
    code="npm install lodash",
    execution_type="shell",
    context="Agent is installing dependencies"
)
```

#### Claude 3 Tool-Use Integration
```python
from agentic_framework_integration_expanded import ClaudeToolUseIntegration

claude_integration = ClaudeToolUseIntegration()
result = claude_integration.on_claude_tool_use(
    system_prompt="You are a helpful coding assistant.",
    user_message="Please install the required packages.",
    tool_use_block={"name": "install_package", "input": {"package_name": "lodash"}}
)
```

#### LangGraph, LlamaIndex, OpenAI Assistants API
See `agentic_framework_integrations_extended.py` for LangGraph state-graph, LlamaIndex agent execution, and OpenAI Assistants API integrations.

---

## 🚀 Quick Start

### Prerequisites
```bash
# Install required packages
python3 -m pip install scikit-learn sentence-transformers torch transformers huggingface-hub
```

### Run Test Runner
```bash
cd /Users/mitchparker/.openclaw/workspace
python3 agentic_workflow_graph_test_runner.py
```

### Run Framework Integration Demo
```bash
python3 agentic_framework_integrations_extended.py
```

### Run Enhanced Intent Analyzer
```bash
python3 vlmguard_r1_sentence_transformer_analyzer.py
```

---

## 🛡️ Supported Attack Vectors & Defenses

| Attack Vector | VLMGuard-R1 Detection | Workflow Graph Defense |
|--------------|----------------------|----------------------|
| Indirect Prompt Injection | ✅ Regex + Semantic Embeddings | ✅ Intent blocked/sanitized before validation |
| Role Confusion Attacks | ✅ Pattern Matching | ✅ Intent blocked/sanitized |
| Typosquatting Packages | ❌ | ✅ Detected & blocked (e.g., `axios-secure-v2`) |
| Malicious Git Operations | ❌ | ✅ Force operations blocked, untrusted repos blocked |
| Dangerous Shell Commands | ❌ | ✅ curl/wget/eval/sudo blocked |
| Tool-Use Manipulation | ✅ Semantic Analysis | ✅ Parameter validation & policy enforcement |

---

## 📚 Documentation & Reports

- **Agentic AI Security & "Agentjacking" Report**: `agentic_jacking_security_report.md`
- **Integrated VLMGuard-Workflow Controller Report**: `integrated_vlmguard_workflow_controller_report.md`
- **Security Threat Intelligence (July 2, 2026)**: `security_threat_intelligence_july2_2026.md`

---

## 🔧 Customization

### Adding New Action Types
Extend `AgenticActionType` enum and add validation rules to `AgenticWorkflowGraph`:

```python
class AgenticActionType(Enum):
    # Existing actions...
    NEW_ACTION_TYPE = "new_action_type"

# Add to workflow graph validation rules
```

### Customizing Semantic Embeddings
Change the Sentence Transformer model in `AdvancedVLMGuardR1IntentAnalyzer`:

```python
analyzer = AdvancedVLMGuardR1IntentAnalyzer(model_name="sentence-transformers/all-mpnet-base-v2")
```

### Extending Policy Rules
Modify `AgenticWorkflowGraph._initialize_policies()` to add new parameter constraints or regex patterns.

---

## 📄 License

This project is provided for security research and defensive purposes.

---

## 🤝 Contributing

Contributions for additional framework integrations, enhanced detection patterns, or security improvements are welcome. Please ensure all additions follow defensive security best practices.