# Tasks: Integrate GraphRunner into Production Chat Flow

## Phase 1: ReasoningNode Enhancement

- [x] 1.1 Implement real LLM client integration in ReasoningNode <!-- id: 0 -->
    - Replace mock `_call_llm()` with httpx AsyncClient
    - Use `load_chat_config()` for API credentials
    - Handle API errors gracefully
- [x] 1.2 Integrate chat_processor prompt building <!-- id: 1 -->
    - Import and use `build_chat_context()` from chat_processor
    - Import and use `build_system_prompt()` for full prompt construction
    - Support intent recognition result injection
- [x] 1.3 Implement streaming token output <!-- id: 2 -->
    - Modify `compute()` to yield tokens via AsyncGenerator
    - Add `response_stream` field to return dict
    - Handle streaming vs non-streaming API responses
- [x] 1.4 Implement LLM response parsing <!-- id: 3 -->
    - Use `parse_llm_output()` from emotion_detector
    - Extract tool_call to `pending_tool_calls`
    - Extract hitl_request to state
    - Handle memory_update entries

## Phase 2: GraphRunner Enhancement

- [x] 2.1 Implement state initialization from request <!-- id: 4 -->
    - Load dialogue_history from chat_db
    - Build SemanticInput from ChatRequest/ImageChatRequest
    - Initialize WorkingMemory and EmotionalContext
- [x] 2.2 Implement streaming SSE event emission <!-- id: 5 -->
    - Detect `response_stream` in node updates
    - Iterate and yield SSE text events for each token
    - Emit emotion events from EmotionNode updates
- [x] 2.3 Implement HITL event handling <!-- id: 6 -->
    - Detect hitl_request in state updates
    - Format and emit `hitl` SSE event
    - Detect `status == "suspended"` and stop iteration
- [x] 2.4 Implement tool result event handling <!-- id: 7 -->
    - Emit `tool_result` SSE event after ToolNode execution
    - Handle tool followup response

## Phase 3: ImageNode Implementation

- [x] 3.1 Create ImageNode for Vision API integration <!-- id: 8 -->
    - Create `workflow/core/nodes/image.py`
    - Call `image_analyzer.analyze_image_text()` for OCR
    - Update `SemanticInput.text` with extracted text
    - Emit SSE text event with OCR result
- [x] 3.2 Create MemoryExtractionNode for image memory flow <!-- id: 9 -->
    - Extract memory from OCR text using `memory_extractor`
    - Generate HITL form for memory confirmation
    - Support plan detection with additional fields
- [x] 3.3 Extend GraphOrchestrator for image flow <!-- id: 10 -->
    - Add ImageNode and MemoryExtractionNode to graph
    - Support configurable entry point (text vs image)
    - Define image-specific routing logic
- [x] 3.4 Extend SemanticInput for image data <!-- id: 11 -->
    - Add `image_action` field ("analyze_only" | "analyze_for_memory")
    - Ensure images list is populated from ImageChatRequest
- [x] 3.5 Implement GraphRunner.run_image() method <!-- id: 12 -->
    - Accept ImageChatRequest
    - Initialize state with image data
    - Use image entry point in graph

## Phase 4: State Persistence

- [x] 4.1 Create graph_checkpoints database table <!-- id: 13 -->
    - Add migration in chat_db.py
    - Define schema: session_id, state_json, created_at, updated_at
- [x] 4.2 Implement checkpoint save on HITL suspension <!-- id: 14 -->
    - Serialize GraphState to JSON (handle Pydantic models)
    - Insert/update checkpoint in database
    - Log checkpoint creation
- [x] 4.3 Implement checkpoint load for resume <!-- id: 15 -->
    - Load JSON from database by session_id
    - Deserialize to GraphState
    - Delete checkpoint after successful resume
- [x] 4.4 Implement GraphRunner.resume() method <!-- id: 16 -->
    - Accept session_id and HITL response
    - Load checkpoint and inject response
    - Continue graph execution from appropriate node

## Phase 5: API Replacement

- [x] 5.1 Replace /chat endpoint with GraphRunner <!-- id: 17 -->
    - Remove old `stream_chat_response` function
    - Use `GraphRunner.run()` directly in endpoint
    - Maintain same SSE event format for frontend compatibility
- [x] 5.2 Replace /chat/image endpoint with GraphRunner <!-- id: 18 -->
    - Remove old `stream_image_analysis` function
    - Use `GraphRunner.run_image()` in endpoint
    - Maintain same SSE event format for frontend compatibility
- [ ] 5.3 Update /hitl/continue endpoint <!-- id: 19 -->
    - Load checkpoint and resume GraphRunner
    - Stream resumed execution results
    - Handle checkpoint not found errors
- [ ] 5.4 Delete legacy processing code <!-- id: 20 -->
    - Remove `stream_chat_response()` from main.py
    - Remove `stream_image_analysis()` from main.py
    - Keep reusable logic in chat_processor.py and image_analyzer.py

## Phase 6: Node Improvements

- [x] 6.1 Enhance EmotionNode with SSE emission support <!-- id: 21 -->
    - Add `emotion_event` to return dict for GraphRunner
    - Ensure compatibility with existing emotion detection
- [x] 6.2 Enhance MemoryNode with working memory sync <!-- id: 22 -->
    - Sync working_memory with memory_manager
    - Pass session_id context for better retrieval
- [x] 6.3 Enhance ToolNode with result formatting <!-- id: 23 -->
    - Format tool results for SSE emission
    - Add tool_result_event to return dict
- [x] 6.4 Enhance HITLNode with request formatting <!-- id: 24 -->
    - Use hitl_handler for consistent request format
    - Support both form and visual_display types

## Phase 7: Testing & Validation

- [ ] 7.1 Add unit tests for ReasoningNode LLM integration <!-- id: 25 -->
    - Mock httpx client
    - Test streaming and non-streaming paths
    - Test JSON parsing
- [ ] 7.2 Add unit tests for ImageNode flow <!-- id: 26 -->
    - Mock image_analyzer
    - Test OCR extraction
    - Test memory extraction and HITL generation
- [ ] 7.3 Add unit tests for GraphRunner flow <!-- id: 27 -->
    - Test normal chat flow
    - Test image analysis flow
    - Test tool call flow
    - Test HITL suspension and resume
- [ ] 7.4 Add integration tests for endpoints <!-- id: 28 -->
    - Verify /chat SSE event format compatibility
    - Verify /chat/image SSE event format compatibility
    - Test emotion, memory, HITL, MCP features
- [ ] 7.5 Manual end-to-end testing <!-- id: 29 -->
    - Test text chat via Electron app
    - Test image analysis via Electron app
    - Verify emotion display
    - Verify HITL form flow
    - Verify MCP tool calls

## Phase 8: Documentation & Cleanup

- [ ] 8.1 Update README with GraphRunner architecture <!-- id: 30 -->
    - Document cognitive graph flow for text and image
    - Remove references to old implementation
- [ ] 8.2 Add inline documentation to new code <!-- id: 31 -->
    - Document GraphRunner methods
    - Document ImageNode and MemoryExtractionNode
    - Document node interfaces
