# Spec: Graph Intent Node

## Overview

IntentNode is a LangGraph node that performs multi-layer intent recognition on user input, enabling downstream nodes (especially ReasoningNode) to optimize prompt generation.

## ADDED Requirements

### Requirement: INT-001 IntentNode Implementation
The system SHALL provide an IntentNode class that integrates with the LangGraph cognitive architecture.

#### Scenario: Intent recognition enabled with Layer 1 match
**Given** the setting `system.intent_recognition_enabled` is `true`
**And** a GraphState with semantic_input.text = "提醒我明天下午3点开会"
**When** IntentNode.compute() is called
**Then** the node SHALL return intent_result with:
  - category: "hitl"
  - intent_type: "plan_reminder"
  - confidence: 1.0
  - source: "layer1"

#### Scenario: Intent recognition disabled
**Given** the setting `system.intent_recognition_enabled` is `false`
**When** IntentNode.compute() is called
**Then** the node SHALL return an empty dict (no state changes)
**And** no intent recognition SHALL be performed

#### Scenario: No intent match (fallback to normal)
**Given** the setting `system.intent_recognition_enabled` is `true`
**And** a GraphState with semantic_input.text = "你好"
**And** no Layer 1 rules match the message
**When** IntentNode.compute() is called
**Then** the node SHALL return intent_result with:
  - category: "normal"
  - intent_type: "normal"
  - confidence: 0.0
  - source: "fallback"

---

### Requirement: INT-002 Graph Integration
The GraphOrchestrator SHALL include IntentNode as the first node in the text chat workflow.

#### Scenario: Text graph with intent node
**Given** a GraphOrchestrator with entry_point="text"
**When** build() is called
**Then** the resulting graph SHALL have node order:
  1. intent (IntentNode)
  2. emotion (EmotionNode)
  3. memory (MemoryNode)
  4. reasoning (ReasoningNode)
  5. tools/hitl (conditional)

#### Scenario: Image graph unchanged
**Given** a GraphOrchestrator with entry_point="image"
**When** build() is called
**Then** the resulting graph SHALL NOT include IntentNode
**And** the image flow SHALL remain: image → memory_extraction → hitl

---

### Requirement: INT-003 State Extension
GraphState SHALL include a field for storing intent recognition results.

#### Scenario: Intent result in state
**Given** a GraphState instance
**When** intent_result field is accessed
**Then** it SHALL support storing a dict with keys:
  - category (str)
  - intent_type (str)
  - confidence (float)
  - source (str)
  - matched_rule (optional str)
  - mcp_service_name (optional str)

---

### Requirement: INT-004 ReasoningNode Integration
ReasoningNode SHALL use intent_result to optimize prompt generation.

#### Scenario: Intent snippet injection
**Given** a GraphState with intent_result.intent_type = "plan_reminder"
**And** intent_result.category = "hitl"
**When** ReasoningNode builds its prompt
**Then** the prompt SHALL include the plan_reminder intent snippet (~300 chars)
**And** the prompt SHALL NOT include the full HITL instruction (~3K chars)

#### Scenario: No intent result
**Given** a GraphState with intent_result = None
**When** ReasoningNode builds its prompt
**Then** the prompt SHALL include the full HITL instruction for backward compatibility

#### Scenario: Normal intent
**Given** a GraphState with intent_result.category = "normal"
**When** ReasoningNode builds its prompt
**Then** the prompt SHALL use minimal instructions
**And** token usage SHALL be reduced compared to full instruction mode

---

### Requirement: INT-005 MCP Intent Support
IntentNode SHALL support MCP tool-related intent detection.

#### Scenario: MCP service keyword match
**Given** an MCP service "weather" is running with trigger_keywords = ["天气", "温度"]
**And** a GraphState with semantic_input.text = "今天天气怎么样"
**When** IntentNode.compute() is called
**Then** intent_result SHALL include:
  - category: "mcp"
  - mcp_service_name: "weather"

#### Scenario: MCP intent prompt injection
**Given** a GraphState with intent_result.category = "mcp"
**And** intent_result.mcp_service_name = "weather"
**When** ReasoningNode builds its prompt
**Then** the prompt SHALL include MCP tool instructions for the weather service
**And** the prompt SHALL NOT include HITL instructions

---

### Requirement: INT-006 Async Layer 2 Support
IntentNode SHALL support asynchronous Layer 2 (LLM-based) intent classification.

#### Scenario: Layer 2 classification
**Given** `system.intent_recognition_enabled` is `true`
**And** Layer 1 did not match
**And** Layer 2 is enabled
**When** IntentNode.compute() is called
**Then** the node SHALL call the LLM classifier asynchronously
**And** SHALL return intent_result if confidence exceeds threshold (default 0.7)

#### Scenario: Layer 2 disabled
**Given** Layer 2 is disabled (default for graph flow)
**When** Layer 1 does not match
**Then** the node SHALL return normal intent immediately
**And** no LLM API call SHALL be made

---

## MODIFIED Requirements

### Requirement: MOD-001 GraphState Definition
The existing GraphState in `core/state.py` SHALL be extended with intent recognition fields.

#### Scenario: New intent_result field
**Given** the current GraphState definition
**When** the change is applied
**Then** GraphState SHALL include:
```python
intent_result: Optional[Dict[str, Any]] = Field(
    default=None,
    description="Intent recognition result from IntentNode"
)
```

---

## Related Capabilities

- `workflow-engine`: Core graph orchestration
- `intent-recognition`: Existing intent recognition system (Layer 1 + Layer 2)
