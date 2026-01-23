# Live2D Image Chat Capability

## ADDED Requirements

### Requirement: Image Paste Support

The system SHALL support pasting images from clipboard into the Live2D chat input area.

#### Scenario: User pastes image from clipboard
- **WHEN** user presses Ctrl+V (or Cmd+V on macOS) while the chat input is focused
- **AND** the clipboard contains an image
- **THEN** the system SHALL display a preview of the pasted image above the input area
- **AND** the system SHALL show an "Analyze Image" button
- **AND** the system SHALL show a "Cancel" button to remove the preview

#### Scenario: User pastes non-image content
- **WHEN** user pastes content that is not an image
- **THEN** the system SHALL handle it as regular text paste (existing behavior)

#### Scenario: Image file size exceeds limit
- **WHEN** user pastes an image larger than 4MB
- **THEN** the system SHALL automatically compress the image before sending
- **AND** the system SHALL display a notification about compression

---

### Requirement: Image Analysis API

The system SHALL provide an API endpoint to analyze images and extract text content using Vision LLM.

#### Scenario: Analyze image with text content
- **WHEN** client sends a POST request to `/chat/image` with valid Base64 image data
- **AND** the image contains readable text
- **THEN** the system SHALL return the extracted text content via SSE stream
- **AND** the response SHALL include a text event with the extracted content

#### Scenario: Analyze image without text content
- **WHEN** client sends a POST request to `/chat/image` with valid image data
- **AND** the image does not contain readable text
- **THEN** the system SHALL return a message indicating no text was found
- **AND** the system SHALL NOT generate a HITL request for memory saving

#### Scenario: Invalid image data
- **WHEN** client sends a request with invalid or corrupted image data
- **THEN** the system SHALL return an error event with appropriate message

---

### Requirement: Image to Memory Extraction

The system SHALL extract structured memory information from analyzed image text and present it to the user for confirmation.

#### Scenario: Extract memory from image text
- **WHEN** image analysis successfully extracts text content
- **AND** the extracted text contains information worth saving as memory
- **THEN** the system SHALL use memory extractor to identify key, value, and category
- **AND** the system SHALL generate a HITL request with pre-filled memory fields
- **AND** the HITL form SHALL allow user to edit the extracted information

#### Scenario: User confirms memory from image
- **WHEN** user clicks "Approve" on the image memory HITL form
- **THEN** the system SHALL save the memory to long-term memory storage
- **AND** the system SHALL display a confirmation notification

#### Scenario: User rejects memory from image
- **WHEN** user clicks "Reject" or "Skip" on the image memory HITL form
- **THEN** the system SHALL NOT save any memory
- **AND** the system SHALL close the HITL form

---

### Requirement: Image Preview UI

The system SHALL display a visual preview when an image is pasted or selected for analysis.

#### Scenario: Display image preview
- **WHEN** an image is pasted or uploaded
- **THEN** the system SHALL display a thumbnail preview (max 200px width)
- **AND** the preview SHALL appear above the chat input area
- **AND** the preview SHALL include action buttons (Analyze, Cancel)

#### Scenario: Show analysis progress
- **WHEN** user clicks "Analyze Image" button
- **THEN** the system SHALL display a loading indicator on the preview
- **AND** the Analyze button SHALL be disabled during analysis
- **AND** the system SHALL show "Analyzing..." text

#### Scenario: Display analysis result
- **WHEN** image analysis completes successfully
- **THEN** the system SHALL display the extracted text in the chat message area
- **AND** the image preview SHALL be cleared
- **AND** if memory HITL is triggered, the HITL form SHALL be displayed

---

### Requirement: Vision LLM Configuration

The system SHALL support configuring the Vision LLM model used for image analysis.

#### Scenario: Use default vision model
- **WHEN** `vision_model` is not specified in chat_config.json
- **THEN** the system SHALL use the value of `model` field for vision analysis

#### Scenario: Use custom vision model
- **WHEN** `vision_model` is specified in chat_config.json
- **THEN** the system SHALL use that model for image analysis
- **AND** regular chat SHALL continue using the `model` field

#### Scenario: Vision model not supported
- **WHEN** the configured model does not support vision capabilities
- **THEN** the system SHALL return an error indicating vision is not supported
