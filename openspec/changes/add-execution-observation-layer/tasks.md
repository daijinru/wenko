# v1 — 认知层地基

## 1. [v1] Observation Data Models

- [x] 1.1 Define `ExecutionSnapshot` model in `workflow/core/state.py` with all fields (identity, current state, derived properties, constraints, result, transition count)
- [x] 1.2 Define `ExecutionConsequenceView` model in `workflow/core/state.py` with consequence_label, has_side_effects, was_suspended, is_still_pending
- [x] 1.3 Define `TransitionRecord` model in `workflow/core/state.py` with sequence_number, actor_category mapping
- [x] 1.4 Define `ACTOR_CATEGORY_MAP` and `STATUS_TO_CONSEQUENCE` constants in `workflow/core/state.py`
- [x] 1.5 Write unit tests for v1 observation data models (ExecutionSnapshot, ExecutionConsequenceView, TransitionRecord)

## 2. [v1] ExecutionObserver Service — Core

- [x] 2.1 Create `workflow/observation.py` with `ExecutionObserver` class
- [x] 2.2 Implement `snapshot()` method: project ExecutionContract → ExecutionSnapshot
- [x] 2.3 Implement `consequence_view()` method: project ExecutionContract → ExecutionConsequenceView (with was_suspended computed from transition history)
- [x] 2.4 Implement `consequence_views()` method: batch projection for ReasoningNode consumption
- [x] 2.5 Implement `action_summary` generation from `action_detail` (default: `{service}.{method}`)
- [x] 2.6 Write unit tests for Observer core methods (snapshot of each status, consequence_view with/without suspension)

## 3. [v1] ReasoningNode Integration (Critical Path)

- [x] 3.1 Refactor `ReasoningNode._build_tool_result_from_contracts()` → `_build_tool_result_from_consequences()` consuming `List[ExecutionConsequenceView]`
- [x] 3.2 Remove direct `ExecutionStatus` enum comparison from ReasoningNode consequence-reading code path
- [x] 3.3 Include `has_side_effects` and `was_suspended` indicators in LLM prompt injection text
- [x] 3.4 Add irreversibility warning text in prompt when `has_side_effects: true`
- [x] 3.5 Write unit tests: ReasoningNode produces correct prompt text from ConsequenceView (success, failure, rejected, irreversible+suspended)
- [x] 3.6 Verify backward compatibility: when no contracts exist, fallback to legacy `observation` string still works

## 4. [v1] Resume Alignment Check

- [x] 4.1 Add pre-resume snapshot generation in `GraphRunner.resume()`
- [x] 4.2 Add WAITING contract count validation with warning log
- [x] 4.3 Write tests for alignment check (normal case, count mismatch warning)

## 5. [v1] Memory Execution Summary

- [x] 5.1 Add execution summary generation in `MemoryNode.consolidate()` for terminal contracts
- [x] 5.2 Implement summary format: `type: "execution_fact"`, `action_summary`, `final_status`, `irreversible`, `duration_ms`, truncated `result_summary`/`error_summary`
- [x] 5.3 Write tests for memory execution summary (completed, failed, summary truncation)

## 6. [v1] Validation — v1 Gate

- [x] 6.1 Run all existing tests to ensure no regressions (34 passed)
- [x] 6.2 Run `openspec validate add-execution-observation-layer --strict` (valid)

---

# v1-minimal — 极简实现，v2 强化

## 7. [v1-minimal] Per-Execution Timeline & Topology (Internal)

- [x] 7.1 Implement per-execution `transition_records()` method in Observer: project single contract's transitions → List[TransitionRecord]
- [x] 7.2 Implement `topology()` static method: project `_VALID_TRANSITIONS` + `TERMINAL_STATUSES` → StateMachineTopology (including forbidden transitions)
- [x] 7.3 Define `StateNode`, `StateTransitionEdge`, `StateMachineTopology` models in `workflow/core/state.py`
- [x] 7.4 Define `ExecutionTimeline` model in `workflow/core/state.py` (for v2 reuse)
- [x] 7.5 Write unit tests for topology completeness (all 7 nodes, all edges, forbidden transitions) and per-execution transition ordering

---

# v2 — 工程与产品能力

## 8. [v2] Full Session Timeline

- [x] 8.1 Implement full `timeline()` method: project list of contracts + trace → ExecutionTimeline with cross-contract aggregation
- [x] 8.2 Write tests for session-level timeline (multi-contract ordering, aggregation stats, has_suspended, has_irreversible_completed)

## 9. [v2] API Endpoints

- [ ] 9.1 Add `GET /api/execution/{session_id}/timeline` endpoint in `workflow/main.py`
- [ ] 9.2 Add `GET /api/execution/{execution_id}/snapshot` endpoint in `workflow/main.py`
- [ ] 9.3 Add `GET /api/execution/topology` endpoint in `workflow/main.py`
- [ ] 9.4 Implement checkpoint-based data retrieval for timeline and snapshot queries
- [ ] 9.5 Write integration tests for all 3 endpoints (success, 404, data correctness)

## 10. [v2] SSE Event Emission

- [ ] 10.1 Add `execution_state` SSE event emission in `GraphRunner.run()` after ToolNode/ECSNode state transitions
- [ ] 10.2 Add `execution_state` SSE event emission in `GraphRunner.resume()` after resume transitions
- [ ] 10.3 Verify existing SSE events (`text`, `emotion`, `ecs`, `tool_result`) remain unchanged
- [ ] 10.4 Write tests for SSE event payload structure

## 11. [v2] Validation — v2 Gate

- [ ] 11.1 Run all existing tests + v1 tests to ensure no regressions
- [ ] 11.2 Run `openspec validate add-execution-observation-layer --strict`
