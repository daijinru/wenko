# Execution Observation

执行状态观测层：提供只读的执行状态投影、执行后果感知、状态机拓扑暴露和实时状态变更事件。

分阶段交付：v1 聚焦认知层地基（ReasoningNode 现实感知 + resume 对齐 + 记忆），v2 扩展工程与产品能力（HTTP API + SSE 事件）。

## ADDED Requirements

### Requirement: Execution Snapshot Projection `[v1]`

The system SHALL provide a read-only snapshot projection of any ExecutionContract, exposing current status, derived stability properties, and constraint metadata without exposing internal implementation details.

#### Scenario: Snapshot of a PENDING contract

- **GIVEN** an ExecutionContract with status `PENDING`
- **WHEN** an observation snapshot is requested
- **THEN** the snapshot SHALL include `current_status: "pending"`, `is_terminal: false`, `is_stable: false`, `is_resumable: false`
- **AND** `transition_count` SHALL be `0`
- **AND** `action_summary` SHALL be a human-readable description derived from `action_detail`

#### Scenario: Snapshot of a WAITING contract

- **GIVEN** an ExecutionContract with status `WAITING` and `irreversible: true`
- **WHEN** an observation snapshot is requested
- **THEN** the snapshot SHALL include `is_stable: true`, `is_resumable: true`, `has_side_effects: true`
- **AND** `duration_in_state_ms` SHALL reflect the time elapsed since entering WAITING
- **AND** `last_trigger` SHALL be `"suspend"` and `last_actor` SHALL identify the node that triggered suspension

#### Scenario: Snapshot of a terminal contract

- **GIVEN** an ExecutionContract with status `COMPLETED`
- **WHEN** an observation snapshot is requested
- **THEN** the snapshot SHALL include `is_terminal: true`, `is_stable: true`, `is_resumable: false`
- **AND** `result` SHALL contain the execution result if available

### Requirement: Execution Consequence View for ReasoningNode `[v1]`

The system SHALL provide an ExecutionConsequenceView as a simplified, ReasoningNode-oriented projection of ExecutionContract, serving as the primary interface through which ReasoningNode perceives real-world execution outcomes. ReasoningNode SHALL NOT directly read ExecutionContract fields for determining execution consequences.

#### Scenario: Consequence view of a successful irreversible tool execution

- **GIVEN** an ExecutionContract with status `COMPLETED`, `irreversible: true`, and transitions showing a WAITING → RUNNING → COMPLETED path
- **WHEN** a consequence view is requested
- **THEN** the view SHALL include `consequence_label: "SUCCESS"`, `has_side_effects: true`, `was_suspended: true`, `is_still_pending: false`
- **AND** `result` SHALL contain the execution result
- **AND** `action_summary` SHALL be a human-readable description

#### Scenario: Consequence view of a failed tool execution

- **GIVEN** an ExecutionContract with status `FAILED` and no WAITING in its transition history
- **WHEN** a consequence view is requested
- **THEN** the view SHALL include `consequence_label: "FAILED"`, `was_suspended: false`, `is_still_pending: false`
- **AND** `error_message` SHALL contain the failure reason

#### Scenario: Consequence view of a WAITING contract

- **GIVEN** an ExecutionContract with status `WAITING`
- **WHEN** a consequence view is requested
- **THEN** the view SHALL include `consequence_label: "WAITING"`, `is_still_pending: true`
- **AND** `has_side_effects` SHALL be `false` (side effects have not yet occurred)

#### Scenario: ReasoningNode consumes consequence views instead of raw contracts

- **GIVEN** ReasoningNode receives control after tool execution
- **WHEN** it builds tool result text for LLM prompt injection
- **THEN** it SHALL obtain `ExecutionConsequenceView` instances via `ExecutionObserver.consequence_views()`
- **AND** it SHALL NOT directly read `ExecutionContract.status`, `ExecutionContract.result`, or `ExecutionContract.error_message`
- **AND** the injected prompt text SHALL include `has_side_effects` and `was_suspended` indicators when applicable

### Requirement: Resume Alignment Check `[v1]`

The system SHALL perform alignment checks before executing a resume operation, validating that the contract state is consistent with the expected graph position and preventing illegal execution paths.

#### Scenario: Successful alignment before resume

- **GIVEN** a checkpoint with one contract in WAITING status
- **WHEN** `GraphRunner.resume()` is called
- **THEN** the system SHALL generate an ExecutionSnapshot before proceeding
- **AND** the system SHALL verify the contract count matches expected WAITING contracts
- **AND** resume SHALL proceed normally

#### Scenario: Alignment warning on count mismatch

- **GIVEN** a checkpoint where the number of WAITING contracts differs from expected
- **WHEN** `GraphRunner.resume()` is called
- **THEN** the system SHALL log a warning with the mismatch details
- **AND** resume SHALL still proceed if individual contract validation passes

### Requirement: Memory Execution Summary `[v1]`

The system SHALL record a structured execution summary in MemoryNode when a contract reaches a terminal state, capturing the execution outcome for long-term recall without storing full transition history.

#### Scenario: Recording a successful tool execution

- **GIVEN** a tool_call contract has reached COMPLETED status with `irreversible: true`
- **WHEN** MemoryNode consolidation is triggered
- **THEN** a memory entry with `type: "execution_fact"` SHALL be created
- **AND** it SHALL include `action_summary`, `final_status: "completed"`, `irreversible: true`, `duration_ms`, and a truncated `result_summary`

#### Scenario: Recording a failed execution

- **GIVEN** a tool_call contract has reached FAILED status
- **WHEN** MemoryNode consolidation is triggered
- **THEN** a memory entry with `type: "execution_fact"` SHALL be created
- **AND** it SHALL include `final_status: "failed"` and a truncated `error_summary`
- **AND** the full transition history SHALL NOT be stored in memory (available via timeline API)

### Requirement: Execution Timeline Query `[v1-minimal / v2]`

The system SHALL provide an ordered timeline of all execution contracts and their state transitions within a single session, supporting historical review and debugging. v1 provides per-execution transition history via internal function; v2 extends to full session-level aggregated timeline with HTTP API.

#### Scenario: Per-execution transition history (v1-minimal)

- **GIVEN** an ExecutionContract with 4 transitions (PENDING → RUNNING → WAITING → RUNNING → COMPLETED)
- **WHEN** transition records are projected from the contract
- **THEN** the result SHALL contain 4 TransitionRecord entries in chronological order
- **AND** each record SHALL include `execution_id`, `from_status`, `to_status`, `trigger`, `actor`, `actor_category`, and `timestamp`

#### Scenario: Full session timeline (v2)

- **GIVEN** a session with 2 contracts (one tool_call COMPLETED, one ecs_request WAITING)
- **WHEN** the timeline is queried for that session via HTTP API
- **THEN** the response SHALL include both contracts as snapshots ordered by `created_at`
- **AND** all transition records across contracts SHALL be merged and ordered by timestamp
- **AND** `total_contracts` SHALL be `2`, `terminal_contracts` SHALL be `1`, `active_contracts` SHALL be `1`
- **AND** `has_suspended` SHALL be `true`

### Requirement: State Machine Topology Exposure `[v1-minimal / v2]`

The system SHALL expose the complete state machine topology as a static structure, including all state nodes, valid transitions, forbidden transitions, terminal states, and resumable states. v1 provides this as an internal function for debugging and test assertions; v2 exposes it via HTTP API.

#### Scenario: Internal topology for validation (v1-minimal)

- **WHEN** `ExecutionObserver.topology()` is called
- **THEN** it SHALL return all 7 state nodes (PENDING, RUNNING, WAITING, COMPLETED, FAILED, REJECTED, CANCELLED)
- **AND** each node SHALL indicate `is_terminal`, `is_initial`, `is_stable`, `is_resumable`
- **AND** all valid transition edges SHALL be listed with `from_status`, `to_status`, and `trigger`
- **AND** terminal states SHALL have no outbound edges
- **AND** `resumable_statuses` SHALL contain only `["waiting"]`

#### Scenario: Forbidden transitions included

- **WHEN** the topology is retrieved
- **THEN** it SHALL include forbidden transitions (e.g., COMPLETED → RUNNING, WAITING → COMPLETED)
- **AND** each forbidden transition SHALL include the `from_status`, `to_status`, and reason

#### Scenario: HTTP API exposure (v2)

- **WHEN** GET `/api/execution/topology` is called
- **THEN** the response SHALL be a StateMachineTopology JSON object
- **AND** the response SHALL be cacheable (topology is static)
- **AND** status code SHALL be 200

### Requirement: Execution State SSE Event `[v2]`

The system SHALL emit an `execution_state` SSE event each time an ExecutionContract undergoes a state transition, providing real-time observation for connected clients.

#### Scenario: SSE event on state transition

- **GIVEN** a contract transitions from RUNNING to COMPLETED via the "succeed" trigger
- **WHEN** the transition is performed within GraphRunner's streaming context
- **THEN** an SSE event with type `execution_state` SHALL be emitted
- **AND** the event payload SHALL include `execution_id`, `action_summary`, `from_status`, `to_status`, `trigger`, `actor_category`, `is_terminal`, `is_resumable`, `has_side_effects`, and `timestamp`

#### Scenario: SSE event is optional for consumers

- **GIVEN** a frontend client that does not handle `execution_state` events
- **WHEN** the event is emitted
- **THEN** the core conversation flow SHALL NOT be affected
- **AND** existing SSE events (`text`, `emotion`, `ecs`, `tool_result`) SHALL continue to work unchanged

### Requirement: Observation API Endpoints `[v2]`

The system SHALL provide HTTP API endpoints for querying execution observation data, decoupled from the graph execution flow.

#### Scenario: Query session timeline

- **GIVEN** a valid session_id with completed executions
- **WHEN** GET `/api/execution/{session_id}/timeline` is called
- **THEN** the response SHALL be an ExecutionTimeline JSON object
- **AND** status code SHALL be 200

#### Scenario: Query single contract snapshot

- **GIVEN** a valid execution_id
- **WHEN** GET `/api/execution/{execution_id}/snapshot` is called
- **THEN** the response SHALL be an ExecutionSnapshot JSON object
- **AND** status code SHALL be 200

#### Scenario: Query for non-existent session

- **GIVEN** a session_id with no execution data
- **WHEN** GET `/api/execution/{session_id}/timeline` is called
- **THEN** status code SHALL be 404
- **AND** the response SHALL include an error message
