# Tasks: Integrate Intent Node to Graph

## Phase 1: Core Implementation

- [x] **1.1** Create `workflow/core/nodes/intent.py` with IntentNode class
  - Import existing `IntentRecognizer`, `RuleBasedMatcher` from `intent_recognizer.py`
  - Import `is_intent_recognition_enabled` from `chat_processor.py`
  - Implement `compute(state: GraphState) -> Dict[str, Any]`
  - Add logging consistent with existing intent recognizer format

- [x] **1.2** Extend GraphState in `workflow/core/state.py`
  - Add `intent_result: Optional[Dict[str, Any]]` field
  - Add field description for documentation

- [x] **1.3** Update GraphOrchestrator in `workflow/core/graph.py`
  - Import IntentNode
  - Add intent node to text workflow
  - Update node ordering: intent → emotion → memory → reasoning
  - Keep image workflow unchanged

## Phase 2: ReasoningNode Integration

- [x] **2.1** Extract prompt snippet logic from `chat_processor.py`
  - Reuse existing `get_intent_snippet()` function via import in `chat_processor.py`
  - Intent snippet constants already exist in `chat_processor.py`

- [x] **2.2** Update ReasoningNode in `workflow/core/nodes/reasoning.py`
  - Check `state.intent_result` in prompt building
  - Use intent snippet when available
  - Fall back to full instruction when intent not available
  - Maintain MCP intent handling

## Phase 3: MCP Intent Support

- [x] **3.1** Add MCP keyword rules to IntentNode
  - Import `build_mcp_keyword_rules_from_services` from `intent_recognizer.py`
  - Get running MCP services from `mcp_manager`
  - Update matcher with dynamic MCP rules

- [x] **3.2** Update ReasoningNode for MCP intent
  - MCP intent handling via `chat_processor.build_system_prompt()` already supports MCP
  - IntentNode passes `mcp_service_name` in intent_result

## Phase 4: Testing & Validation

- [x] **4.1** Create unit tests for IntentNode
  - Test Layer 1 matching
  - Test disabled state behavior
  - Test fallback behavior
  - Created `workflow/tests/test_intent_node.py` with 10 passing tests

- [ ] **4.2** Integration test with full graph
  - Test intent → emotion → memory → reasoning flow
  - Verify intent_result propagates correctly
  - Test setting toggle behavior

- [ ] **4.3** Manual validation
  - Test with plan reminder messages
  - Test with MCP trigger keywords
  - Test with normal conversation
  - Verify logging output

## Dependencies

- Task 1.1 depends on: existing `intent_recognizer.py` (no changes needed)
- Task 2.1-2.2 depend on: Task 1.1, 1.2
- Task 3.1-3.2 depend on: Task 2.2
- Task 4.x depend on: Phase 1-3 completion

## Validation Criteria

1. Setting `system.intent_recognition_enabled=false` should bypass intent recognition
2. Plan reminder messages should trigger `plan_reminder` intent
3. MCP trigger keywords should trigger `mcp` intent with correct service name
4. Normal conversation should fall back to minimal prompt mode
5. Token usage should decrease for matched intents (verify via logging)
