# Cognitive Graph Specification

## ADDED Requirements

### Requirement: Graph-Driven Chat Execution

The system SHALL execute chat requests through the LangGraph-based cognitive graph, processing user input through a sequence of specialized nodes (Emotion, Memory, Reasoning, Tools, HITL).

#### Scenario: Normal chat flow without tools or HITL

- **GIVEN** a user sends a chat message
- **WHEN** the `/chat` endpoint is called
- **THEN** the GraphRunner SHALL initialize a GraphState with the user message
- **AND** the graph SHALL execute nodes in order: EmotionNode → MemoryNode → ReasoningNode
- **AND** the system SHALL stream SSE events for emotion detection and response text
- **AND** a `done` event SHALL be emitted when execution completes

#### Scenario: Chat flow with MCP tool call

- **GIVEN** a user message requires tool execution
- **WHEN** ReasoningNode detects a tool_call in the LLM response
- **THEN** the graph SHALL route to ToolNode
- **AND** ToolNode SHALL execute the MCP tool and return an observation
- **AND** the graph SHALL route back to ReasoningNode with the observation
- **AND** ReasoningNode SHALL generate a final response incorporating the tool result

#### Scenario: Chat flow with HITL request

- **GIVEN** a user message triggers a HITL form request
- **WHEN** ReasoningNode detects a hitl_request in the LLM response
- **THEN** the graph SHALL route to HITLNode
- **AND** HITLNode SHALL set status to "suspended"
- **AND** the GraphRunner SHALL persist the GraphState to `graph_checkpoints` table
- **AND** an `hitl` SSE event SHALL be emitted with the form definition
- **AND** execution SHALL pause until user responds

### Requirement: Streaming LLM Response

The system SHALL stream LLM response tokens to the client as they are generated, providing real-time feedback during response generation.

#### Scenario: Streaming tokens during reasoning

- **GIVEN** ReasoningNode is generating a response
- **WHEN** the LLM API returns tokens incrementally
- **THEN** each token SHALL be yielded as an SSE `text` event
- **AND** tokens SHALL arrive at the client with minimal delay (<100ms per token)
- **AND** the complete response SHALL be persisted to dialogue_history after streaming completes

#### Scenario: Non-streaming fallback

- **GIVEN** the LLM API does not support streaming
- **WHEN** ReasoningNode calls the API
- **THEN** the complete response SHALL be returned as a single SSE `text` event
- **AND** execution SHALL continue normally

### Requirement: State Persistence for HITL

The system SHALL persist GraphState when execution is suspended for human intervention, enabling resumption after user response.

#### Scenario: Saving checkpoint on HITL suspension

- **GIVEN** HITLNode sets status to "suspended"
- **WHEN** GraphRunner detects the suspended status
- **THEN** the current GraphState SHALL be serialized to JSON
- **AND** the JSON SHALL be stored in `graph_checkpoints` table with session_id as key
- **AND** existing checkpoint for the session SHALL be replaced

#### Scenario: Resuming from checkpoint

- **GIVEN** a user submits HITL form response via `/hitl/respond`
- **WHEN** `/hitl/continue` endpoint is called
- **THEN** the GraphState SHALL be loaded from `graph_checkpoints`
- **AND** the HITL response SHALL be injected into the state
- **AND** the graph SHALL resume execution from ReasoningNode
- **AND** the checkpoint SHALL be deleted after successful resume

### Requirement: Emotion Detection Node

The EmotionNode SHALL analyze user input text and update the emotional context for downstream processing.

#### Scenario: Detecting user emotion

- **GIVEN** a user message with emotional indicators
- **WHEN** EmotionNode processes the message
- **THEN** the emotional_context SHALL be updated with detected emotion
- **AND** modulation_instruction SHALL be set for ReasoningNode prompt adjustment
- **AND** an SSE `emotion` event SHALL be emitted with the detection result

#### Scenario: Neutral emotion fallback

- **GIVEN** a user message with no clear emotional indicators
- **WHEN** EmotionNode processes the message
- **THEN** emotional_context.current_emotion SHALL be set to "neutral"
- **AND** a neutral modulation_instruction SHALL be provided

### Requirement: Memory Retrieval Node

The MemoryNode SHALL retrieve relevant long-term memories based on user input, enriching the context for response generation.

#### Scenario: Retrieving relevant memories

- **GIVEN** a user message about a previously discussed topic
- **WHEN** MemoryNode processes the message
- **THEN** working_memory.retrieved_memories SHALL contain matching MemoryRef items
- **AND** memory access statistics SHALL be updated
- **AND** retrieved memories SHALL be available to ReasoningNode for prompt construction

#### Scenario: No relevant memories found

- **GIVEN** a user message about a new topic
- **WHEN** MemoryNode processes the message
- **THEN** working_memory.retrieved_memories SHALL be an empty list
- **AND** ReasoningNode SHALL proceed without memory context

### Requirement: Reasoning Node with Real LLM

The ReasoningNode SHALL call the configured LLM API to generate responses, using context from emotion detection and memory retrieval.

#### Scenario: Building prompt with full context

- **GIVEN** EmotionNode and MemoryNode have updated the state
- **WHEN** ReasoningNode constructs the LLM prompt
- **THEN** the prompt SHALL include working_memory_summary
- **AND** the prompt SHALL include relevant_long_term_memory
- **AND** the prompt SHALL include emotion_modulation instruction
- **AND** the prompt SHALL include HITL/MCP instructions based on intent

#### Scenario: Parsing LLM JSON response

- **GIVEN** the LLM returns a JSON-formatted response
- **WHEN** ReasoningNode parses the response
- **THEN** the response text SHALL be extracted to dialogue_history
- **AND** tool_call (if present) SHALL populate pending_tool_calls
- **AND** hitl_request (if present) SHALL be set in state
- **AND** memory_update entries SHALL trigger memory storage

### Requirement: Tool Execution Node

The ToolNode SHALL execute MCP tool calls and return observations to the reasoning loop.

#### Scenario: Successful tool execution

- **GIVEN** pending_tool_calls contains a valid MCP tool call
- **WHEN** ToolNode executes the tool
- **THEN** the tool result SHALL be captured
- **AND** observation SHALL be set with the result
- **AND** pending_tool_calls SHALL be cleared
- **AND** a `tool_result` SSE event SHALL be emitted

#### Scenario: Tool execution failure

- **GIVEN** pending_tool_calls contains a tool call
- **WHEN** the MCP tool execution fails
- **THEN** observation SHALL contain the error message
- **AND** execution SHALL continue (not crash)
- **AND** ReasoningNode SHALL receive the error in observation

### Requirement: SSE Event Compatibility

The GraphRunner SHALL emit SSE events in the same format as the legacy implementation, ensuring frontend compatibility.

#### Scenario: Event type mapping

- **GIVEN** a GraphRunner is processing a request
- **WHEN** nodes produce state updates
- **THEN** `text` events SHALL contain `{"type": "text", "payload": {"content": "..."}}`
- **AND** `emotion` events SHALL contain `{"type": "emotion", "payload": {"primary": "...", "confidence": ...}}`
- **AND** `hitl` events SHALL contain the full HITL request payload
- **AND** `tool_result` events SHALL contain tool execution results
- **AND** `done` events SHALL be emitted on successful completion
- **AND** `error` events SHALL be emitted on failure

### Requirement: Image Analysis via Graph

The system SHALL process image analysis requests through the cognitive graph, using ImageNode for OCR and MemoryExtractionNode for memory extraction.

#### Scenario: Image OCR extraction

- **GIVEN** a user uploads an image via `/chat/image`
- **WHEN** the GraphRunner processes the ImageChatRequest
- **THEN** ImageNode SHALL call the Vision API to extract text
- **AND** the extracted text SHALL be stored in `SemanticInput.text`
- **AND** an SSE `text` event SHALL be emitted with the OCR result prefixed with "📷 图片文本识别结果"

#### Scenario: Image memory extraction with HITL confirmation

- **GIVEN** an image contains extractable memory content
- **AND** the action is "analyze_for_memory"
- **WHEN** MemoryExtractionNode processes the OCR text
- **THEN** memory information SHALL be extracted using `memory_extractor`
- **AND** if confidence >= 0.3, a HITL form SHALL be generated for user confirmation
- **AND** the form SHALL include fields for key, value, and category
- **AND** an SSE `hitl` event SHALL be emitted with the form definition

#### Scenario: Image with plan detection

- **GIVEN** an image contains time-related plan information
- **WHEN** MemoryExtractionNode detects category="plan"
- **THEN** additional fields SHALL be included: target_time, location, participants
- **AND** the HITL form title SHALL be "保存计划到日程"

#### Scenario: Image with no extractable text

- **GIVEN** an image contains no readable text
- **WHEN** ImageNode processes the image
- **THEN** an SSE `text` event SHALL indicate no text was found
- **AND** execution SHALL complete with a `done` event
- **AND** no HITL form SHALL be generated

#### Scenario: Image analyze_only mode

- **GIVEN** an image is uploaded with action="analyze_only"
- **WHEN** the graph processes the request
- **THEN** only OCR extraction SHALL be performed
- **AND** no memory extraction or HITL form SHALL be generated
- **AND** execution SHALL complete after emitting the OCR result
