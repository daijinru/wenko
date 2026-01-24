# Tasks: Add Plan Reminder Feature

## 1. Backend - Memory System Extension

- [x] 1.1 Add `PLAN` to `MemoryCategory` enum in `memory_manager.py`
- [x] 1.2 Create `PlanEntry` dataclass with time-specific fields (target_time, reminder_time, repeat_rule, status)
- [x] 1.3 Add database table/schema for plans (using existing SQLite)
- [x] 1.4 Implement `create_plan()`, `get_due_plans()`, `mark_plan_completed()`, `delete_plan()` methods

## 2. Backend - HITL Plan Form

- [x] 2.1 Add `DATETIME` field type to `HITLFieldType` enum in `hitl_schema.py`
- [x] 2.2 Create plan collection HITL template with fields: title, description, target_datetime, reminder_offset, repeat_type
- [x] 2.3 Add `collect_plan` intent handling in `hitl_handler.py`
- [x] 2.4 Implement `_save_plan()` function to persist plan from HITL form data

## 3. Backend - LLM Plan Recognition

- [x] 3.1 Add plan recognition instructions to `HITL_INSTRUCTION` in `chat_processor.py`
- [x] 3.2 Define time expression patterns for LLM to detect (e.g., "明天下午3点", "下周三", "1月25日")
- [x] 3.3 Add example scenarios for plan intent detection in prompt

## 4. Backend - Plan CRUD API

- [x] 4.1 Create `GET /plans` endpoint to list all plans (支持分页和状态过滤)
- [x] 4.2 Create `POST /plans` endpoint to create a new plan
- [x] 4.3 Create `GET /plans/{id}` endpoint to get plan details
- [x] 4.4 Create `PUT /plans/{id}` endpoint to update a plan
- [x] 4.5 Create `DELETE /plans/{id}` endpoint to delete a plan
- [x] 4.6 Create `GET /plans/due` endpoint to query due plans (for Electron polling)
- [x] 4.7 Create `POST /plans/{id}/complete` endpoint to mark plan as completed
- [x] 4.8 Create `POST /plans/{id}/dismiss` endpoint to dismiss a plan
- [x] 4.9 Create `POST /plans/{id}/snooze` endpoint to snooze a plan

## 5. Electron - Polling and Notification

- [x] 5.1 Implement plan polling service in `main.cjs` (interval: 60s recommended)
- [x] 5.2 Send `plan:reminder` IPC event to renderer when plan is due
- [x] 5.3 Handle reminder acknowledgement from user (complete/snooze/dismiss)

## 6. Live2D - Reminder Display

- [x] 6.1 Listen for `plan:reminder` event in Live2D chat module
- [x] 6.2 Display reminder message through Live2D character (speech bubble + expression)
- [x] 6.3 Provide interaction buttons (完成/稍后提醒/取消)
- [x] 6.4 Send acknowledgement back to main process via IPC

## 7. Workflow Panel - Plan Management UI (Merged into Long-term Memory)

- [x] 7.1 ~~Create Plans page component~~ → Merged: Plans integrated as "计划" category in Long-term Memory tab
- [x] 7.2 Implement "Add Plan" form in Memory Form Dialog (标题、描述、目标时间、提醒偏移、重复类型)
- [x] 7.3 Implement plan edit functionality via Memory Form Dialog
- [x] 7.4 Implement plan delete with confirmation dialog
- [x] 7.5 Add "计划" category filter in Long-term Memory filter (alongside 偏好/事实/模式)
- [x] 7.6 ~~Add navigation entry to Plans page~~ → Not needed: Plans accessible via "计划" category filter
- [x] 7.7 Update use-long-term-memory hook to route 'plan' category to /plans API
- [x] 7.8 Add purple badge variant for plan category display
- [x] 7.9 Display plan-specific info (target_time, repeat_type, status) in memory list

## 8. Testing and Validation

- [ ] 8.1 Test plan creation via HITL: user message → HITL form → save plan
- [ ] 8.2 Test plan creation via Workflow panel: add form → API → save plan
- [ ] 8.3 Test plan CRUD in Workflow panel: list, edit, delete operations
- [ ] 8.4 Test reminder trigger: polling → due plan detection → Live2D notification
- [ ] 8.5 Test edge cases: past dates, timezone handling, repeat plans
