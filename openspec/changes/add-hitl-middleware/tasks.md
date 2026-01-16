# HITL Middleware Implementation Tasks

## 1. Backend - HITL Core

- [x] 1.1 Create `workflow/hitl_schema.py` - Define Pydantic models for HITL Schema
  - HITLField, HITLOption, HITLActions, HITLRequest, HITLResponse
- [x] 1.2 Create `workflow/hitl_handler.py` - HITL request processing logic
  - Schema validation
  - Request state management (pending/completed/expired)
  - Memory integration
- [x] 1.3 Add HITL request storage (in-memory with TTL or SQLite)
- [x] 1.4 Extend `chat_processor.py` prompt template with HITL instruction

## 2. Backend - API Endpoints

- [x] 2.1 Add `POST /hitl/respond` endpoint in `main.py`
- [x] 2.2 Extend SSE stream to emit `hitl` events
- [x] 2.3 Parse hitl_request from LLM JSON response
- [x] 2.4 Handle approve/edit/reject actions

## 3. Frontend - HITL Form Component

- [x] 3.1 Create `HITLFormRenderer.jsx` - Dynamic form renderer
  - Map field types to Ant Design components
  - Handle required field validation
- [x] 3.2 Create `HITLFormField.jsx` - Individual field components
  - text, textarea, select, multiselect
  - radio, checkbox, number, slider
- [x] 3.3 Create `HITLActionButtons.jsx` - Approve/Edit/Reject buttons
- [x] 3.4 Add HITL form styling in CSS

## 4. Frontend - SSE Integration

- [x] 4.1 Extend SSE event handler for `hitl` event type
- [x] 4.2 Show HITL form overlay when hitl event received
- [x] 4.3 Implement `submitHITLResponse()` API call
- [x] 4.4 Resume chat after HITL completion

## 5. Integration & Testing

- [ ] 5.1 End-to-end test: AI generates HITL form → User approves → Memory saved
- [ ] 5.2 Test reject flow
- [ ] 5.3 Test edit flow
- [ ] 5.4 Test invalid schema handling
- [ ] 5.5 Test request expiration

## 6. Documentation

- [ ] 6.1 Update API documentation with HITL endpoints
- [ ] 6.2 Add HITL usage examples to prompt engineering guide
