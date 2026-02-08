# Cognitive Graph Specification

## MODIFIED Requirements

### Requirement: Tool Execution Node

The ToolNode SHALL execute MCP tool calls via ExecutionContract state transitions, providing structured success/failure reporting instead of unstructured string observations.

#### Scenario: Successful tool execution

- **GIVEN** `pending_executions` contains a contract with `action_type="tool_call"`
- **WHEN** ToolNode executes the MCP tool
- **THEN** the contract SHALL transition from `PENDING` → `RUNNING` → `COMPLETED`
- **AND** `contract.result` SHALL contain the tool output
- **AND** the observation field SHALL also be populated for backward compatibility
- **AND** a `tool_result` SSE event SHALL be emitted

#### Scenario: Tool execution failure

- **GIVEN** `pending_executions` contains a contract with `action_type="tool_call"`
- **WHEN** the MCP tool execution fails
- **THEN** the contract SHALL transition from `PENDING` → `RUNNING` → `FAILED`
- **AND** `contract.error_message` SHALL contain the error description
- **AND** the observation field SHALL also be populated for backward compatibility
- **AND** ReasoningNode SHALL receive the structured error via the contract

### Requirement: Reasoning Node with Real LLM

The ReasoningNode SHALL call the configured LLM API to generate responses, using context from emotion detection and memory retrieval. When creating executable actions, it SHALL produce ExecutionContracts instead of raw tool call dictionaries.

#### Scenario: Building prompt with full context

- **GIVEN** EmotionNode and MemoryNode have updated the state
- **WHEN** ReasoningNode constructs the LLM prompt
- **THEN** the prompt SHALL include working_memory_summary
- **AND** the prompt SHALL include relevant_long_term_memory
- **AND** the prompt SHALL include emotion_modulation instruction
- **AND** the prompt SHALL include ECS/MCP instructions based on intent

#### Scenario: Parsing LLM JSON response

- **GIVEN** the LLM returns a JSON-formatted response
- **WHEN** ReasoningNode parses the response
- **THEN** the response text SHALL be extracted to dialogue_history
- **AND** tool_call (if present) SHALL create an ExecutionContract with `action_type="tool_call"` added to `pending_executions`
- **AND** ecs_request (if present) SHALL create an ExecutionContract with `action_type="ecs_request"` added to `pending_executions`
- **AND** memory_update entries SHALL trigger memory storage

#### Scenario: Reading completed execution results

- **GIVEN** ReasoningNode is re-entered after tool or ECS execution
- **WHEN** `completed_executions` contains contracts
- **THEN** ReasoningNode SHALL read `contract.status` to determine outcome
- **AND** ReasoningNode SHALL NOT parse natural language observation strings for execution status determination

### Requirement: State Persistence for ECS

The system SHALL persist GraphState including ExecutionContract data when execution is suspended for human intervention, enabling validated resumption after user response.

#### Scenario: Saving checkpoint on ECS suspension

- **GIVEN** ECSNode transitions a contract to `WAITING` status
- **WHEN** GraphRunner detects the suspended status
- **THEN** the current GraphState SHALL be serialized to JSON including all ExecutionContracts
- **AND** the JSON SHALL be stored in `graph_checkpoints` table with session_id as key

#### Scenario: Resuming from checkpoint with validation

- **GIVEN** a user submits ECS form response via `/ecs/respond`
- **WHEN** `/ecs/continue` endpoint is called
- **THEN** the GraphState SHALL be loaded from `graph_checkpoints`
- **AND** the system SHALL validate the waiting contract is in `WAITING` status
- **AND** the contract SHALL be transitioned through `WAITING` → `RUNNING` → `COMPLETED`
- **AND** the graph SHALL resume execution from ReasoningNode
- **AND** the checkpoint SHALL be deleted after successful resume
