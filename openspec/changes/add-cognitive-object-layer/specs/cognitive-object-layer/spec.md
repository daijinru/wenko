## ADDED Requirements

### Requirement: Cognitive Object Data Model

The system SHALL define a `CognitiveObject` entity with stable identity (`co_id`), title, description, semantic boundary fields (`semantic_type`, `domain_tag`, `intent_category`), lifecycle status, transition history, execution links, memory references, external references, and CO-to-CO relation placeholders.

The `CognitiveObject` SHALL exist independently of any `ExecutionContract`. A CO MUST be able to persist with zero linked executions.

#### Scenario: CO created without execution
- **WHEN** a user expresses a trackable intent (e.g., "我要跟踪这个项目")
- **AND** no ExecutionContract exists yet
- **THEN** a CognitiveObject is created with status `emerging`, a stable `co_id`, and the user's description
- **AND** `linked_execution_ids` is empty

#### Scenario: CO with semantic enrichment
- **WHEN** a CognitiveObject is created
- **THEN** optional fields `semantic_type`, `domain_tag`, and `intent_category` MAY be populated
- **AND** the CO is queryable by these semantic fields

---

### Requirement: CO Lifecycle State Machine

The system SHALL manage CognitiveObject lifecycle through a six-state state machine: `emerging`, `active`, `waiting`, `blocked`, `stable`, `archived`.

All state transitions SHALL be validated against the transition rules. Invalid transitions SHALL be rejected. Every transition SHALL record `{from, to, trigger, timestamp, actor, reason}`.

The LLM SHALL NOT directly change CO status. All transitions MUST go through the `CORegistry.transition()` method with an explicit `actor` and `trigger`.

#### Scenario: Normal lifecycle progression
- **WHEN** a CO is in status `emerging`
- **AND** a `clarify` trigger is applied with actor `user`
- **THEN** the CO transitions to `active`
- **AND** a transition record is appended with the trigger, actor, timestamp, and reason

#### Scenario: Invalid transition rejected
- **WHEN** a CO is in status `emerging`
- **AND** a `achieve` trigger is attempted
- **THEN** the transition is rejected
- **AND** the CO status remains `emerging`

#### Scenario: Archived CO reactivation
- **WHEN** a CO is in status `archived`
- **AND** a `reactivate` trigger is applied with actor `user`
- **THEN** the CO transitions to `active`
- **AND** a transition record is appended

#### Scenario: All transitions traceable
- **WHEN** any CO state transition occurs
- **THEN** the transition history contains an entry with `from`, `to`, `trigger`, `timestamp`, `actor`, and `reason`
- **AND** the transition history is ordered chronologically

---

### Requirement: CO-Execution Relationship

The Execution subsystem SHALL be owned by the Cognitive Object Layer. The system SHALL support linking `ExecutionContract` instances to a `CognitiveObject` via an optional `cognitive_object_id` field on `ExecutionContract`. Execution is the internal execution mechanism of CO, not an independent layer.

One CO MAY own multiple ExecutionContracts. An ExecutionContract MAY have no owning CO (backward compatibility during migration). Execution termination SHALL NOT automatically terminate the owning CO.

#### Scenario: Execution owned by CO
- **WHEN** an ExecutionContract is created with `cognitive_object_id` set
- **THEN** the execution is recorded as an execution sub-unit in the CO's `linked_execution_ids`
- **AND** the CO's `updated_at` timestamp is refreshed

#### Scenario: All executions end but CO persists
- **WHEN** all ExecutionContracts owned by a CO reach terminal status
- **AND** the CO is in status `active`
- **THEN** the CO remains in status `active`
- **AND** the CO is still queryable and operable

#### Scenario: CO without any execution
- **WHEN** a CO exists with zero ExecutionContracts
- **THEN** the CO is still valid and queryable
- **AND** the CO's lifecycle state machine operates normally

---

### Requirement: CO Persistence

The system SHALL persist CognitiveObjects in SQLite, surviving across sessions and application restarts. The system SHALL provide a `CORegistry` service for CRUD operations, status transitions, and queries.

#### Scenario: CO survives session restart
- **WHEN** a CognitiveObject is created in session A
- **AND** the application is restarted
- **THEN** the CO is retrievable in session B with all fields intact

#### Scenario: Query active COs
- **WHEN** a user requests their active items
- **THEN** the system returns all COs not in `archived` status
- **AND** results are ordered by `updated_at` descending

#### Scenario: Query by semantic fields
- **WHEN** a user queries COs by `domain_tag = "work"`
- **THEN** the system returns only COs with matching `domain_tag`

---

### Requirement: CO-Memory Boundary

Memory (long-term facts) and CognitiveObjects (active things) SHALL be distinct entities. Memory records facts ("what happened"). CO represents things ("what IS").

A CO MAY reference Memory entries via `linked_memory_ids`. Memory entries SHALL exist independently of any CO. The Memory layer SHALL NOT hold references to CO (unidirectional dependency: CO → Memory).

#### Scenario: CO references memory
- **WHEN** a Memory entry is created during execution linked to a CO
- **THEN** the Memory entry ID MAY be added to the CO's `linked_memory_ids`
- **AND** the Memory entry itself does not contain a CO reference

#### Scenario: Memory exists without CO
- **WHEN** a Memory entry is created (e.g., user preference)
- **AND** no CO is associated
- **THEN** the Memory entry is fully functional and queryable

---

### Requirement: ECS as CO Projection Interface

The ECS (Externalized Cognitive Step) layer SHALL serve as the projection interface for CognitiveObjects, not for ExecutionContracts directly. User actions through ECS SHALL affect the underlying CO.

Closing an ECS view SHALL NOT destroy or archive the associated CO. Reopening an ECS view SHALL restore the CO's current state.

#### Scenario: User action through ECS affects CO
- **WHEN** a user marks an item as "completed" through the ECS interface
- **THEN** the CO receives an `achieve` trigger with actor `user`
- **AND** the CO transitions to `stable` status

#### Scenario: Closing ECS preserves CO
- **WHEN** a user closes the ECS projection view
- **THEN** the associated CO remains in its current status
- **AND** the CO is still accessible via API and future ECS projections

---

### Requirement: Semantic Enhancement Fields

CognitiveObjects SHALL support optional semantic enrichment fields for future cognitive graph capabilities: `semantic_type`, `domain_tag`, `intent_category`, `external_references`, and `related_co_ids`.

The `related_co_ids` field SHALL store CO-to-CO relationships with typed relations (`blocks`, `depends_on`, `part_of`, `related_to`). In the initial implementation, this field is stored but traversal/query logic is not implemented.

#### Scenario: External reference attached
- **WHEN** a CO is created or updated with an external reference
- **THEN** the reference is stored as `{"type": "url", "value": "...", "label": "..."}`
- **AND** the reference is retrievable with the CO

#### Scenario: CO-to-CO relation stored
- **WHEN** a CO relation is added (e.g., CO-A blocks CO-B)
- **THEN** the relation is stored in CO-A's `related_co_ids` as `{"co_id": "CO-B-id", "relation": "blocks"}`
- **AND** no graph traversal or dependency resolution is performed

---

### Requirement: Gradual Migration Support

The COL SHALL be introduced gradually without breaking existing functionality. The system SHALL support a configuration flag `system.col_enabled` to control COL integration phases.

Phase 0 (data model only) and Phase 1 (standalone CRUD) SHALL work with `col_enabled = false`. Phase 2+ (Execution linking, ReasoningNode integration) SHALL require `col_enabled = true`.

#### Scenario: System operates without COL enabled
- **WHEN** `system.col_enabled` is `false`
- **THEN** all existing functionality (Execution, Observer, ECS, Memory) operates identically to pre-COL behavior
- **AND** CO API endpoints are available but do not affect the cognitive graph

#### Scenario: Gradual activation
- **WHEN** `system.col_enabled` is set to `true`
- **THEN** new ExecutionContracts MAY be linked to CognitiveObjects via `cognitive_object_id`
- **AND** ReasoningNode receives CO context in its reasoning input
- **AND** existing unlinked ExecutionContracts continue to function normally
