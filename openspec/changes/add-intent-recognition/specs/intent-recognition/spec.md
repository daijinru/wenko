## ADDED Requirements

### Requirement: Multi-Layer Intent Recognition

The system SHALL provide a multi-layer intent recognition mechanism that identifies user intent before sending to the main LLM, optimizing token usage and improving strategy hit rates.

#### Scenario: Layer 1 matches memory intent via regex
- **WHEN** user message matches a memory-related pattern (e.g., "我叫小明", "我喜欢Python")
- **THEN** system logs "[Intent] Layer1: MATCHED {intent_type}" with confidence 1.0
- **AND** system returns the matched MemoryIntent without calling Layer 2

#### Scenario: Layer 1 matches HITL intent via keywords
- **WHEN** user message matches a HITL trigger pattern (e.g., "提醒我明天开会", "你好")
- **THEN** system logs "[Intent] Layer1: MATCHED {intent_type}" with confidence 1.0
- **AND** system returns the matched HITLIntent without calling Layer 2

#### Scenario: Layer 1 misses, Layer 2 matches
- **WHEN** user message does not match any Layer 1 rules
- **AND** Layer 2 LLM classifier returns intent with confidence >= threshold
- **THEN** system logs "[Intent] Layer2: MATCHED {intent_type}" with confidence score
- **AND** system returns the classified intent

#### Scenario: Both layers miss, fallback to normal chat
- **WHEN** user message does not match any Layer 1 rules
- **AND** Layer 2 LLM classifier returns no intent or confidence < threshold
- **THEN** system logs "[Intent] Fallback: using normal conversation"
- **AND** system returns None, indicating normal chat flow

### Requirement: Intent-Based Prompt Optimization

The system SHALL use intent-specific prompt snippets instead of full strategy instructions when an intent is matched.

#### Scenario: Intent matched, use snippet
- **WHEN** intent recognition returns a matched intent
- **THEN** system includes only the relevant strategy snippet (~300 chars) in the prompt
- **AND** system excludes the full HITL_INSTRUCTION (~3K chars)

#### Scenario: No intent matched, use simple prompt
- **WHEN** intent recognition returns None
- **THEN** system uses SIMPLE_SYSTEM_PROMPT without memory/HITL instructions
- **AND** token usage is minimized for casual conversation

### Requirement: Intent Recognition Logging

The system SHALL log intent recognition flow with structured format for observability.

#### Scenario: Log Layer 1 match
- **WHEN** Layer 1 matches an intent
- **THEN** system prints log in format: "[Intent] Layer1: MATCHED {intent} (confidence={score}, rule={rule_name})"

#### Scenario: Log Layer 2 classification
- **WHEN** Layer 2 is invoked
- **THEN** system prints log in format: "[Intent] Layer2: {MATCHED|no match} {intent} (confidence={score})"

#### Scenario: Log final decision
- **WHEN** intent recognition completes
- **THEN** system prints log in format: "[Intent] Using prompt snippet: {intent}" or "[Intent] Fallback: using normal conversation"

### Requirement: Intent Recognition Configuration

The system SHALL support configuration options for intent recognition behavior.

#### Scenario: Enable/disable intent recognition
- **WHEN** config contains `intent_recognition.enabled = false`
- **THEN** system bypasses intent recognition and uses original full-prompt behavior

#### Scenario: Configure Layer 2 model
- **WHEN** config contains `intent_recognition.layer2_model`
- **THEN** system uses specified model for Layer 2 classification
- **AND** defaults to main chat model if not specified

#### Scenario: Configure confidence threshold
- **WHEN** config contains `intent_recognition.layer2_confidence_threshold`
- **THEN** system uses specified threshold for Layer 2 match decisions
- **AND** defaults to 0.6 if not specified
