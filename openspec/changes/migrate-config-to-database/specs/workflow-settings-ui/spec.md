## ADDED Requirements

### Requirement: Settings Tab in Workflow Panel

The Workflow panel SHALL provide a "Settings" tab for managing application configuration through a graphical interface.

#### Scenario: Settings tab display
- **WHEN** user opens the Workflow panel
- **THEN** a "设置" (Settings) tab is visible alongside existing tabs
- **AND** clicking the tab displays the settings management interface

#### Scenario: LLM configuration display
- **WHEN** user views the Settings tab
- **THEN** the LLM configuration section displays current values for:
  - API Base URL
  - API Key (masked by default)
  - Model name
  - System prompt
  - Max tokens
  - Temperature

#### Scenario: API Key visibility toggle
- **WHEN** user clicks the visibility toggle on the API Key field
- **THEN** the API Key value toggles between masked (****) and plain text display

#### Scenario: Settings modification
- **WHEN** user modifies a configuration value
- **AND** clicks the Save button
- **THEN** the new value is persisted to the database
- **AND** the system shows a success notification
- **AND** the configuration change takes effect immediately

#### Scenario: Invalid configuration handling
- **WHEN** user enters an invalid value (e.g., non-numeric temperature)
- **THEN** the system displays a validation error message
- **AND** prevents saving until the error is corrected

### Requirement: Settings REST API

The system SHALL provide RESTful API endpoints for settings management.

#### Scenario: Get all settings
- **WHEN** a GET request is made to `/api/settings`
- **THEN** the system returns all settings as a JSON object
- **AND** responds with status code 200

#### Scenario: Get single setting
- **WHEN** a GET request is made to `/api/settings/{key}`
- **THEN** the system returns the setting value
- **AND** responds with status code 200 if found
- **AND** responds with status code 404 if not found

#### Scenario: Update single setting
- **WHEN** a PUT request is made to `/api/settings/{key}` with a new value
- **THEN** the system updates the setting in database
- **AND** responds with status code 200 and the updated setting

#### Scenario: Batch update settings
- **WHEN** a PUT request is made to `/api/settings` with multiple key-value pairs
- **THEN** the system updates all provided settings
- **AND** responds with status code 200 and the updated settings count

#### Scenario: Reset settings
- **WHEN** a POST request is made to `/api/settings/reset`
- **THEN** the system restores all settings to their default values
- **AND** responds with status code 200 and a success message
