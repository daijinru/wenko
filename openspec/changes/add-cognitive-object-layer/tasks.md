## Phase 0: Data Model Foundation

- [x] 0.1 Define `CognitiveObjectStatus` enum in `workflow/core/state.py`
- [x] 0.2 Define `CognitiveObject` Pydantic model in `workflow/core/state.py`
- [x] 0.3 Define `_CO_VALID_TRANSITIONS` transition rules in `workflow/core/state.py`
- [x] 0.4 Add `CognitiveObject.transition()` method with validation and history tracking
- [x] 0.5 Write unit tests for CO state machine (valid transitions, invalid transitions, traceability)

## Phase 1: Persistence and CRUD

- [x] 1.1 Create `cognitive_objects` and `co_execution_links` tables in `workflow/chat_db.py`
- [x] 1.2 Implement `CORegistry` service in `workflow/cognitive_object.py` (create, get, list_active, list_by_status, transition, search)
- [x] 1.3 Implement `link_execution()` and `link_memory()` methods in `CORegistry`
- [x] 1.4 Add CO REST API endpoints in `workflow/main.py`: `POST /api/co`, `GET /api/co`, `GET /api/co/{co_id}`, `PATCH /api/co/{co_id}/transition`, `POST /api/co/{co_id}/link-execution`
- [x] 1.5 Write integration tests for CORegistry CRUD and API endpoints
- [x] 1.6 Add `system.col_enabled` configuration flag to `app_settings`

## Phase 2: Execution Subsystem Integration

- [x] 2.1 Add optional `cognitive_object_id` field to `ExecutionContract` in `workflow/core/state.py`
- [ ] 2.2 Modify `GraphRunner` to assign new ExecutionContracts to owning CO when `col_enabled = true`
- [ ] 2.3 Emit `co.execution_completed` / `co.execution_failed` events when owned Execution reaches terminal state
- [ ] 2.4 Write tests for Execution → CO ownership and event reporting

## Phase 3: ReasoningNode Integration

- [ ] 3.1 Inject active CO context summary into ReasoningNode reasoning input (when `col_enabled = true`)
- [ ] 3.2 Enable ReasoningNode to suggest CO transitions via `suggest_transition` (not direct mutation)
- [ ] 3.3 Modify MemoryNode to associate execution summaries with linked CO
- [ ] 3.4 Write tests for ReasoningNode CO context injection and MemoryNode CO linking

## Phase 4: ECS Projection

- [ ] 4.1 Modify ECS projection to display CO status and metadata (Execution data as CO's internal detail)
- [ ] 4.2 Route user ECS actions to CO transitions (e.g., "mark complete" → CO.achieve)
- [ ] 4.3 Ensure closing ECS view does not affect CO lifecycle
- [ ] 4.4 Write integration tests for ECS → CO interaction
