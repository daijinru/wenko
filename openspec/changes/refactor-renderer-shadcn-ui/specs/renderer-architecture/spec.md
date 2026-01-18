## ADDED Requirements

### Requirement: Renderer Architecture

The Electron renderer SHALL follow a modular architecture with separation of concerns:

1. **UI Components**: shadcn/ui based components organized by feature
2. **Business Logic**: Encapsulated in custom hooks
3. **API Layer**: Centralized HTTP client with type safety
4. **Type Definitions**: TypeScript types for all API contracts

#### Scenario: Component organization
- **WHEN** a developer needs to modify a feature
- **THEN** they can locate all related code within a single feature folder
- **AND** changes are isolated from other features

#### Scenario: API client usage
- **WHEN** making an API request
- **THEN** the request uses the centralized API client
- **AND** errors are handled consistently with user feedback
- **AND** response data is type-checked

#### Scenario: State management via hooks
- **WHEN** a component needs to manage feature state
- **THEN** it uses a dedicated custom hook
- **AND** the hook encapsulates all related state and operations
- **AND** the component focuses only on rendering

### Requirement: HTTP Client Abstraction

The renderer SHALL use a centralized HTTP client that provides:

1. Unified error handling with toast notifications
2. Type-safe request/response handling
3. Configurable base URL
4. Consistent JSON parsing

#### Scenario: Successful API call
- **WHEN** an API call succeeds
- **THEN** the response is parsed and returned with correct TypeScript types
- **AND** no error message is shown

#### Scenario: Failed API call
- **WHEN** an API call fails with a network error
- **THEN** an error toast is displayed to the user
- **AND** the error is logged for debugging
- **AND** the function throws or returns an error state

#### Scenario: API response error
- **WHEN** the API returns an error status code
- **THEN** the error message from the response is shown to the user
- **AND** the function handles the error appropriately

### Requirement: Component Library

The renderer SHALL use shadcn/ui components with Tailwind CSS styling that:

1. Support theme customization via CSS variables
2. Maintain accessibility standards (via Radix UI primitives)
3. Allow custom styling while preserving functionality

#### Scenario: Theme switching
- **WHEN** the user switches themes
- **THEN** all components update their appearance
- **AND** the classic Mac OS 9 theme is available as an option
- **AND** theme preference persists across sessions

#### Scenario: Component customization
- **WHEN** a component needs custom styling
- **THEN** developers can modify the component source directly
- **AND** Tailwind utility classes can be applied
- **AND** the component's core functionality is preserved

### Requirement: TypeScript Support

The renderer codebase SHALL use TypeScript with strict mode for:

1. All new code files (.tsx, .ts)
2. Type definitions for API contracts
3. Component props interfaces

#### Scenario: Type safety enforcement
- **WHEN** code violates type constraints
- **THEN** the build fails with clear error messages
- **AND** the IDE provides inline error highlighting

#### Scenario: API type definitions
- **WHEN** defining API response types
- **THEN** types match the Python backend's Pydantic models
- **AND** optional fields are properly marked
- **AND** nested objects have their own type definitions
