## ADDED Requirements

### Requirement: Deep Thinking Mode Toggle
The system SHALL provide a user-configurable toggle to enable or disable deep thinking (extended reasoning) mode for LLM interactions.

#### Scenario: User enables deep thinking mode
- **WHEN** user enables deep thinking mode in settings
- **THEN** the system stores the preference as `llm.deep_thinking_enabled = true`
- **AND** subsequent LLM API calls use parameters that encourage deeper reasoning
- **AND** the configured temperature value is preserved

#### Scenario: User disables deep thinking mode
- **WHEN** user disables deep thinking mode in settings (or uses default)
- **THEN** the system stores the preference as `llm.deep_thinking_enabled = false`
- **AND** subsequent LLM API calls use parameters that minimize reasoning overhead
- **AND** temperature is reduced to minimize divergent thinking
- **AND** system prompt includes instruction to provide direct answers without showing reasoning process

#### Scenario: Deep thinking toggle UI displays cost warning
- **WHEN** user views the deep thinking toggle in settings
- **THEN** the UI displays a clear warning about potential increased token consumption
- **AND** the UI displays a warning about potential increased response time
- **AND** the warning recommends enabling only when deep analysis is needed

### Requirement: Deep Thinking Parameter Application
The system SHALL apply appropriate API parameters based on the deep thinking mode setting when making LLM calls.

#### Scenario: API call with deep thinking enabled
- **WHEN** deep thinking mode is enabled
- **AND** system makes an LLM API call
- **THEN** the request uses the user-configured temperature
- **AND** if the API supports reasoning parameters, they are set to encourage deeper thinking

#### Scenario: API call with deep thinking disabled
- **WHEN** deep thinking mode is disabled
- **AND** system makes an LLM API call
- **THEN** the request uses a reduced temperature (e.g., 0.3) to minimize divergent reasoning
- **AND** the system prompt includes a directive to respond directly without showing reasoning
- **AND** any `<thinking>` tagged content in responses is filtered out

### Requirement: API Compatibility Handling
The system SHALL gracefully handle varying levels of deep thinking support across different LLM providers.

#### Scenario: API does not support reasoning parameters
- **WHEN** deep thinking mode is enabled
- **AND** the target API does not support reasoning/thinking parameters
- **THEN** the system falls back to prompt-level control only
- **AND** no error is raised to the user
- **AND** the request completes successfully with basic compatibility mode
