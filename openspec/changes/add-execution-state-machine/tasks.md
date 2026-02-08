## 1. Data Model Foundation

- [x] 1.1 Define `ExecutionStatus` enum in `workflow/core/state.py`
- [x] 1.2 Define `ExecutionContract` model in `workflow/core/state.py` with `transition()` method and validation
- [x] 1.3 Add `pending_executions` and `completed_executions` fields to `GraphState`
- [x] 1.4 Write unit tests for `ExecutionContract.transition()` covering all valid and invalid state transitions

## 2. ToolNode Contract Integration

- [x] 2.1 Modify `ToolNode.execute()` to create and advance `ExecutionContract` state transitions
- [x] 2.2 Maintain backward compatibility by also writing to `observation` field
- [x] 2.3 Write unit tests for ToolNode success/failure contract transitions

## 3. ECSNode Contract Integration

- [x] 3.1 Modify `ECSNode.execute()` to advance contract through `PENDING → RUNNING → WAITING`
- [x] 3.2 Write unit tests for ECSNode suspend contract transitions

## 4. ReasoningNode Contract Consumption

- [x] 4.1 Modify `ReasoningNode.compute()` to create `ExecutionContract` instead of raw `pending_tool_calls` dicts
- [x] 4.2 Modify `ReasoningNode.compute()` to read `completed_executions` for structured status
- [x] 4.3 Implement idempotency key checking for irreversible operations
- [x] 4.4 Write unit tests for ReasoningNode contract creation and reading

## 5. Graph Routing Adaptation

- [x] 5.1 Update `route_reasoning()` in `graph.py` to check `pending_executions` alongside `pending_tool_calls`
- [x] 5.2 Verify graph topology remains unchanged (tools → reasoning loop, ecs → END)

## 6. GraphRunner Resume Validation

- [x] 6.1 Update `GraphRunner.resume()` to validate contract is in `WAITING` status before resuming
- [x] 6.2 Update checkpoint serialization to include `ExecutionContract` data
- [x] 6.3 Implement contract `WAITING → RUNNING → COMPLETED` transition on resume
- [x] 6.4 Write integration test for full suspend/resume cycle with contract validation

## 7. Execution Trace Activation

- [x] 7.1 Wire `execution_trace` population into ToolNode and ECSNode `_record_trace()` methods
- [x] 7.2 Verify execution_trace is serialized/deserialized in checkpoints (via GraphState Pydantic model)
- [x] 7.3 Write test verifying execution_trace contains complete transition history

## 8. Backward Compatibility and Cleanup

- [x] 8.1 Ensure `pending_tool_calls` and `observation` fields continue to work during transition period
- [x] 8.2 Document migration path for removing legacy fields in future

### Migration notes (8.2)

Legacy fields to remove in a future change after all consumers are migrated:
- `GraphState.pending_tool_calls` → replaced by `pending_executions` (contracts with `action_type="tool_call"`)
- `GraphState.observation` → replaced by `completed_executions[].result` / `completed_executions[].error_message`
- `ToolNode` string-prefix observation format → replaced by `ExecutionStatus` enum on contracts
- `route_reasoning()` legacy branch → remove `state.pending_tool_calls` check once all callers use contracts

During the transition period, both old and new fields are populated in parallel:
- `ReasoningNode` sets both `pending_tool_calls` and `pending_executions`
- `ToolNode` returns both `observation` and `completed_executions`
- `route_reasoning()` checks both `pending_tool_calls` and `pending_executions`
- `ReasoningNode._build_tool_result_from_contracts()` is preferred over raw `state.observation`
