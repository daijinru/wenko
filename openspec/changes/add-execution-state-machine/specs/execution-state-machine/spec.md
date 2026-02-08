# Execution State Machine

独立于意图和任务建模的执行状态管理能力，用于描述和约束现实世界中的执行过程。

## ADDED Requirements

### Requirement: Execution Contract Lifecycle

The system SHALL create an ExecutionContract for each executable action (tool call or ECS request), tracking its lifecycle through a finite state machine with structured status transitions.

#### Scenario: Creating a contract for tool call

- **GIVEN** ReasoningNode detects a tool_call in the LLM response
- **WHEN** the tool call is parsed
- **THEN** an ExecutionContract SHALL be created with `action_type="tool_call"`
- **AND** the contract SHALL have a unique `execution_id`
- **AND** the initial status SHALL be `PENDING`
- **AND** the contract SHALL be added to `pending_executions` in GraphState

#### Scenario: Creating a contract for ECS request

- **GIVEN** ReasoningNode detects an ecs_request in the LLM response
- **WHEN** the ECS request is parsed
- **THEN** an ExecutionContract SHALL be created with `action_type="ecs_request"`
- **AND** the initial status SHALL be `PENDING`
- **AND** the contract SHALL be added to `pending_executions` in GraphState

### Requirement: Execution Status Enumeration

The system SHALL define a minimal and complete set of execution statuses with strict transition rules, ensuring execution state is fact-based and not inferred by reasoning.

#### Scenario: Valid status values

- **GIVEN** the ExecutionStatus enumeration
- **THEN** it SHALL contain exactly these values: `PENDING`, `RUNNING`, `WAITING`, `COMPLETED`, `FAILED`, `REJECTED`, `CANCELLED`
- **AND** `COMPLETED`, `FAILED`, `REJECTED`, `CANCELLED` SHALL be terminal states (no transitions out)
- **AND** `WAITING` SHALL be a stable state (can remain indefinitely)

#### Scenario: Valid state transitions

- **GIVEN** a contract in `PENDING` status
- **THEN** the only valid transition SHALL be to `RUNNING` (via "start" trigger)

- **GIVEN** a contract in `RUNNING` status
- **THEN** valid transitions SHALL be: `COMPLETED` (succeed), `FAILED` (fail), `REJECTED` (reject), `WAITING` (suspend), `CANCELLED` (cancel)

- **GIVEN** a contract in `WAITING` status
- **THEN** valid transitions SHALL be: `RUNNING` (resume), `CANCELLED` (cancel/timeout)

#### Scenario: Invalid state transition rejected

- **GIVEN** a contract in any terminal status (`COMPLETED`, `FAILED`, `REJECTED`, `CANCELLED`)
- **WHEN** a state transition is attempted
- **THEN** the system SHALL raise an error
- **AND** the contract status SHALL remain unchanged

### Requirement: Structured Execution Results

The system SHALL provide structured execution results via ExecutionContract fields, replacing unstructured string-based observation parsing.

#### Scenario: ToolNode reports success via contract

- **GIVEN** ToolNode executes an MCP tool call successfully
- **WHEN** the tool returns a result
- **THEN** the contract status SHALL be transitioned to `COMPLETED`
- **AND** `contract.result` SHALL contain the tool output
- **AND** the transition SHALL be recorded with timestamp and actor="tool_node"

#### Scenario: ToolNode reports failure via contract

- **GIVEN** ToolNode executes an MCP tool call that fails
- **WHEN** the tool returns an error or throws an exception
- **THEN** the contract status SHALL be transitioned to `FAILED`
- **AND** `contract.error_message` SHALL contain the error description
- **AND** the transition SHALL be recorded with timestamp and actor="tool_node"

#### Scenario: ReasoningNode reads structured contract status

- **GIVEN** ReasoningNode receives control after tool or ECS execution
- **WHEN** it processes completed contracts
- **THEN** it SHALL read `contract.status` to determine outcome (not parse observation strings)
- **AND** it SHALL read `contract.result` for success data or `contract.error_message` for failure data

### Requirement: Execution Trace Recording

The system SHALL record all contract state transitions into the existing `execution_trace` field of GraphState, enabling audit and system-level review.

#### Scenario: Recording a state transition

- **GIVEN** a contract undergoes a state transition
- **WHEN** the `transition()` method is called
- **THEN** an ExecutionStep SHALL be appended to `state.execution_trace`
- **AND** the step SHALL contain `node_id`, `action` (including contract_id and from/to states), `timestamp`, and `metadata`

#### Scenario: Trace available for diagnostic review

- **GIVEN** a completed conversation with tool or ECS executions
- **WHEN** a system review is requested
- **THEN** the full execution_trace SHALL be available with all contract transitions
- **AND** each transition SHALL include the actor that triggered it

### Requirement: Irreversible Operation Protection

The system SHALL prevent duplicate execution of irreversible operations through idempotency key checking on completed contracts.

#### Scenario: Blocking duplicate irreversible execution

- **GIVEN** an ExecutionContract with `irreversible=true` has reached `COMPLETED` status
- **WHEN** ReasoningNode attempts to create a new contract with the same `idempotency_key`
- **THEN** the system SHALL reject the creation
- **AND** ReasoningNode SHALL be informed that the operation was already completed

#### Scenario: Allowing retry after failure

- **GIVEN** an ExecutionContract with `irreversible=true` has reached `FAILED` status
- **WHEN** ReasoningNode attempts to create a new contract with the same `idempotency_key`
- **THEN** the system SHALL allow the creation
- **AND** a new contract with a new `execution_id` SHALL be created

### Requirement: Suspend and Resume via Contract

The system SHALL support execution suspension (entering WAITING state) and resumption (returning to RUNNING) through contract state transitions, with validation to prevent invalid resume operations.

#### Scenario: ECS request suspends execution

- **GIVEN** an ECS contract is created and ECSNode processes it
- **WHEN** ECSNode executes
- **THEN** the contract SHALL transition from `PENDING` → `RUNNING` → `WAITING`
- **AND** GraphState.status SHALL be set to "suspended"
- **AND** GraphRunner SHALL persist the checkpoint including the contract

#### Scenario: Valid resume after human response

- **GIVEN** a contract in `WAITING` status and a user response submitted
- **WHEN** `GraphRunner.resume()` is called
- **THEN** the system SHALL validate the contract is in `WAITING` status
- **AND** the contract SHALL transition from `WAITING` → `RUNNING` → `COMPLETED`
- **AND** graph execution SHALL resume from ReasoningNode

#### Scenario: Invalid resume on terminated contract

- **GIVEN** a contract in `COMPLETED` or `CANCELLED` status
- **WHEN** `GraphRunner.resume()` is called for that contract
- **THEN** the system SHALL reject the resume with an error
- **AND** no graph execution SHALL occur
