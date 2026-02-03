# Tasks: Refactor to LangGraph Cognitive Architecture

## Phase 1: Foundation & State Definition
- [ ] Define `GraphState` Pydantic models in `workflow/core/state.py` <!-- id: 0 -->
    - Include `working_memory`, `long_term_memory_refs`, `semantic_input`, `emotional_context`.
- [ ] Define `SemanticInput` and Input Normalization logic <!-- id: 1 -->
    - Ensure strict separation between UI events and cognitive input.

## Phase 2: Core Nodes Implementation
- [x] Implement `MemoryNode` <!-- id: 2 -->
    - Port existing `memory_manager` logic to a graph node interface.
    - Support `load` (recall) and `save` (consolidate) operations.
- [x] Implement `EmotionNode` <!-- id: 3 -->
    - Port `emotion_detector` logic.
    - Ensure output updates `emotional_context` only (no control flow side effects).
- [x] Implement `ToolNode` for MCP <!-- id: 4 -->
    - Wrap MCP service calls into a standardized node execution pattern.
    - Handle tool execution errors gracefully within the node.
- [x] Implement `ReasoningNode` (The Brain) <!-- id: 5 -->
    - Construct Prompt using State fields (Memory + Emotion + Input).
    - Output structured decision (Call Tool vs. HITL vs. Reply).

## Phase 3: HITL & Control Flow
- [x] Implement `HITLNode` <!-- id: 6 -->
    - Design the suspension mechanism using LangGraph's `interrupt` or checkpoints.
    - Define the data contract for `hitl_request` and `hitl_response`.
- [x] Implement `GraphOrchestrator` <!-- id: 7 -->
    - Wire all nodes using `StateGraph`.
    - Define edges and conditional routing logic.

## Phase 4: Integration & Migration
- [ ] Create `GraphRunner` adapter <!-- id: 8 -->
    - Bridge the new Graph runner with the existing FastAPI endpoints.
    - Maintain backward compatibility for the frontend API temporarily.
- [ ] Verify End-to-End Flow <!-- id: 9 -->
    - [x] Test: Input -> Emotion -> Memory -> Reason -> Output.
    - [ ] Test: Failure -> HITL -> Resume.
