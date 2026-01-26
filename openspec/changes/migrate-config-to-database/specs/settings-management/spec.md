## ADDED Requirements

### Requirement: Settings Database Storage

The system SHALL store application settings in SQLite database using a key-value structure.

#### Scenario: Settings table initialization
- **WHEN** the application starts for the first time
- **THEN** the system creates the `app_settings` table with proper schema
- **AND** initializes default configuration values

#### Scenario: Single setting retrieval
- **WHEN** a component requests a specific setting by key
- **THEN** the system returns the setting value with proper type conversion
- **AND** returns the default value if the setting does not exist

#### Scenario: Bulk settings retrieval
- **WHEN** a component requests all settings
- **THEN** the system returns a dictionary of all key-value pairs
- **AND** each value is properly typed according to its `value_type`

#### Scenario: Setting update
- **WHEN** a setting value is updated
- **THEN** the system persists the new value to the database
- **AND** updates the `updated_at` timestamp
- **AND** the new value is immediately available to all components

### Requirement: Settings Migration

The system SHALL automatically migrate existing configuration from `chat_config.json` to database on first run.

#### Scenario: Migration from JSON file
- **WHEN** the application starts with an existing `chat_config.json` file
- **AND** the database has no settings configured
- **THEN** the system imports all settings from the JSON file to database
- **AND** logs the migration result

#### Scenario: Clean installation
- **WHEN** the application starts without existing configuration
- **THEN** the system initializes settings with default values
- **AND** prompts user to configure API key through the Settings UI
