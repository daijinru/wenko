"""ECS Handler Module

Handles ECS request processing, state management, and memory integration.
"""

import logging
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Dict, Optional, Union

import memory_manager
from enum import Enum

from ecs_schema import (
    ECSAction,
    ECSContinuationData,
    ECSDisplayRequest,
    ECSRequest,
    ECSResponseData,
    ECSResponseResult,
    parse_ecs_request_from_dict,
)


class ComplexityLevel(Enum):
    """Form complexity levels for response guidance."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

logger = logging.getLogger(__name__)

# In-memory storage for pending ECS requests
# Key: request_id, Value: (ECSRequest, session_id, expires_at)
_pending_requests: Dict[str, tuple] = {}
_lock = Lock()


def store_ecs_request(request: Union[ECSRequest, Dict[str, Any]], session_id: str) -> None:
    """Store a pending ECS request.

    Args:
        request: The ECS request to store (ECSRequest object or dict)
        session_id: Associated session ID
    """
    # Convert dict to ECSRequest if needed
    if isinstance(request, dict):
        parsed = parse_ecs_request_from_dict(request)
        if parsed is None:
            logger.error(f"[ECS] Failed to parse dict as ECSRequest: {list(request.keys())}")
            return
        request = parsed

    expires_at = datetime.now() + timedelta(seconds=request.ttl_seconds)
    with _lock:
        _pending_requests[request.id] = (request, session_id, expires_at)
    logger.info(f"[ECS] Stored request {request.id} for session {session_id[:8]}...")


def store_display_request(request: ECSDisplayRequest, session_id: str) -> None:
    """Store a pending ECS visual display request.

    Args:
        request: The ECS display request to store
        session_id: Associated session ID
    """
    expires_at = datetime.now() + timedelta(seconds=request.ttl_seconds)
    with _lock:
        _pending_requests[request.id] = (request, session_id, expires_at)
    logger.info(f"[ECS] Stored display request {request.id} for session {session_id[:8]}...")


def get_ecs_request(request_id: str) -> Optional[tuple]:
    """Get a pending ECS request.

    Args:
        request_id: The request ID to look up

    Returns:
        Tuple of (ECSRequest, session_id, expires_at) or None if not found/expired
    """
    with _lock:
        if request_id not in _pending_requests:
            return None

        request, session_id, expires_at = _pending_requests[request_id]

        # Check expiration
        if datetime.now() > expires_at:
            del _pending_requests[request_id]
            logger.info(f"[ECS] Request {request_id} expired")
            return None

        return (request, session_id, expires_at)


def remove_ecs_request(request_id: str) -> bool:
    """Remove a ECS request from storage.

    Args:
        request_id: The request ID to remove

    Returns:
        True if removed, False if not found
    """
    with _lock:
        if request_id in _pending_requests:
            del _pending_requests[request_id]
            return True
        return False


def cleanup_expired_requests() -> int:
    """Remove all expired requests.

    Returns:
        Number of requests cleaned up
    """
    now = datetime.now()
    expired = []

    with _lock:
        for request_id, (_, _, expires_at) in _pending_requests.items():
            if now > expires_at:
                expired.append(request_id)

        for request_id in expired:
            del _pending_requests[request_id]

    if expired:
        logger.info(f"[ECS] Cleaned up {len(expired)} expired requests")

    return len(expired)


def process_ecs_response(response: ECSResponseData) -> ECSResponseResult:
    """Process user response to a ECS request.

    Args:
        response: The user's response data

    Returns:
        ECSResponseResult indicating success/failure and next action
    """
    logger.info(f"[ECS] ========== process_ecs_response START ==========")
    logger.info(f"[ECS] request_id: {response.request_id}")
    logger.info(f"[ECS] session_id: {response.session_id[:8]}...")
    logger.info(f"[ECS] action: {response.action}")
    logger.info(f"[ECS] data: {response.data}")

    # Get the original request
    request_data = get_ecs_request(response.request_id)

    if request_data is None:
        logger.info(f"[ECS] ERROR: request not found or expired")
        return ECSResponseResult(
            success=False,
            next_action="complete",
            error="请求已过期或不存在",
        )

    request, session_id, _ = request_data
    logger.info(f"[ECS] original request.type: {request.type}")
    logger.info(f"[ECS] original request.context: intent={request.context.intent if request.context else None}, memory_category={request.context.memory_category if request.context else None}")

    # Verify session ID matches
    if session_id != response.session_id:
        logger.info(f"[ECS] ERROR: session mismatch")
        return ECSResponseResult(
            success=False,
            next_action="complete",
            error="会话不匹配",
        )

    # Handle visual_display type (dismiss only)
    if isinstance(request, ECSDisplayRequest):
        logger.info(f"[ECS] -> handling visual_display type")
        return _process_display_dismiss(request, session_id, response.request_id)

    # Build field labels mapping for continuation context
    field_labels = {field.name: field.label for field in request.fields}

    # Handle based on action
    if response.action == ECSAction.REJECT:
        logger.info(f"[ECS] -> user REJECTED")
        # User rejected, build continuation data
        remove_ecs_request(response.request_id)
        logger.info(f"[ECS] User rejected request {response.request_id}")
        continuation_data = ECSContinuationData(
            request_title=request.title,
            action="reject",
            form_data=None,
            field_labels=field_labels,
        )
        return ECSResponseResult(
            success=True,
            next_action="continue",
            message="已跳过",
            continuation_data=continuation_data,
        )

    if response.action in (ECSAction.APPROVE, ECSAction.EDIT):
        # Process the form data
        result = _process_form_data(request, response.data, session_id)
        remove_ecs_request(response.request_id)
        # Add continuation data to result
        if result.success:
            result.continuation_data = ECSContinuationData(
                request_title=request.title,
                action="approve",
                form_data=response.data,
                field_labels=field_labels,
            )
        return result

    return ECSResponseResult(
        success=False,
        next_action="complete",
        error="未知操作",
    )


def _process_display_dismiss(
    request: ECSDisplayRequest,
    session_id: str,
    request_id: str,
) -> ECSResponseResult:
    """Process dismiss action for visual display request.

    Args:
        request: The display request
        session_id: Session ID
        request_id: Request ID

    Returns:
        ECSResponseResult indicating success
    """
    # Persist display to working memory before removing
    _persist_display_to_working_memory(request, session_id)

    # Remove the request
    remove_ecs_request(request_id)
    logger.info(f"[ECS] User dismissed display request {request_id}")

    # Visual display doesn't trigger continuation
    return ECSResponseResult(
        success=True,
        next_action="complete",
        message="已关闭",
    )


def _process_form_data(
    request: ECSRequest,
    data: Optional[Dict[str, Any]],
    session_id: str,
) -> ECSResponseResult:
    """Process form data from user response.

    Args:
        request: Original ECS request
        data: Form data from user
        session_id: Session ID

    Returns:
        ECSResponseResult
    """
    logger.info(f"[ECS] ---- _process_form_data START ----")
    logger.info(f"[ECS] request.type: {request.type}")
    logger.info(f"[ECS] request.context: {request.context}")
    logger.info(f"[ECS] form data: {data}")

    if data is None:
        data = {}

    # Validate required fields
    for field in request.fields:
        if field.required and field.name not in data:
            logger.info(f"[ECS] ERROR: required field missing: {field.name}")
            return ECSResponseResult(
                success=False,
                next_action="continue",
                error=f"必填字段 '{field.label}' 未填写",
            )

    # Check if we should save to memory based on request type or intent
    # Image types must be checked first - they have their own save logic
    # that respects user's category selection from the form
    if request.type in ("image_memory_confirm", "image_plan_confirm"):
        logger.info(f"[ECS] -> matched image type, calling _save_image_memory")
        logger.info(f"[ECS]    user selected category: {data.get('category', 'NOT SET')}")
        _save_image_memory(request, data, session_id)
    elif request.context and request.context.intent == "collect_preference":
        logger.info(f"[ECS] -> matched collect_preference, calling _save_to_memory")
        _save_to_memory(request, data, session_id)
    elif request.context and request.context.intent == "collect_plan":
        logger.info(f"[ECS] -> matched collect_plan, calling _save_plan")
        _save_plan(request, data, session_id)
    else:
        logger.info(f"[ECS] -> no matching handler, data not saved to memory")

    # Persist form data to working memory for session context continuity
    _persist_to_working_memory(request, data, session_id)

    logger.info(f"[ECS] ---- _process_form_data END ----")
    logger.info(f"[ECS] Processed form data for request {request.id}")

    return ECSResponseResult(
        success=True,
        next_action="continue",
        message="已保存",
    )


# Maximum size for context_variables in bytes (to prevent unbounded growth)
MAX_CONTEXT_VARIABLES_SIZE = 64 * 1024  # 64KB


def _persist_to_working_memory(
    request: ECSRequest,
    data: Dict[str, Any],
    session_id: str,
) -> None:
    """Persist ECS form data to working memory for session context continuity.

    This ensures that form submissions are available in subsequent conversations
    within the same session.

    Args:
        request: Original ECS request
        data: Form data to persist
        session_id: Session ID
    """
    import json

    try:
        # Get or create working memory
        wm = memory_manager.get_or_create_working_memory(session_id)
        updated_ctx = wm.context_variables.copy()

        # Build field labels mapping for readable context
        field_labels = {field.name: field.label for field in request.fields}

        # Format data with labels for better readability
        labeled_data = {}
        for field_name, value in data.items():
            label = field_labels.get(field_name, field_name)
            labeled_data[label] = value

        # Serialize fields definition for replay capability
        fields_def = []
        for field in request.fields:
            field_dict = {
                "name": field.name,
                "type": field.type.value if hasattr(field.type, 'value') else str(field.type),
                "label": field.label,
                "required": field.required,
            }
            if field.placeholder:
                field_dict["placeholder"] = field.placeholder
            if field.default is not None:
                field_dict["default"] = field.default
            if field.options:
                field_dict["options"] = [{"value": opt.value, "label": opt.label} for opt in field.options]
            if field.min is not None:
                field_dict["min"] = field.min
            if field.max is not None:
                field_dict["max"] = field.max
            if field.step is not None:
                field_dict["step"] = field.step
            fields_def.append(field_dict)

        # Store under a key based on request title
        ctx_key = f"ecs_{request.title}"
        updated_ctx[ctx_key] = {
            "fields": labeled_data,
            "fields_def": fields_def,  # Store original field definitions for replay
            "form_data": data,  # Store original form data (field_name -> value)
            "timestamp": datetime.now().isoformat(),
        }

        # Check size limit before updating
        ctx_json = json.dumps(updated_ctx)
        if len(ctx_json.encode('utf-8')) > MAX_CONTEXT_VARIABLES_SIZE:
            # Remove oldest entries to make room (LRU eviction)
            updated_ctx = _evict_oldest_context_entries(updated_ctx, ctx_key)
            logger.warning(f"[ECS] Context variables exceeded size limit, evicted oldest entries")

        # Update working memory
        memory_manager.update_working_memory(
            session_id,
            context_variables=updated_ctx,
        )
        logger.info(f"[ECS] Persisted form data to working memory: {ctx_key}")

    except Exception as e:
        logger.warning(f"[ECS] Failed to persist to working memory: {e}")


def _persist_display_to_working_memory(
    request: ECSDisplayRequest,
    session_id: str,
) -> None:
    """Persist ECS visual display data to working memory for session context continuity.

    This ensures that visual displays are available for replay in subsequent sessions.

    Args:
        request: Original ECS display request
        session_id: Session ID
    """
    import json

    try:
        # Get or create working memory
        wm = memory_manager.get_or_create_working_memory(session_id)
        updated_ctx = wm.context_variables.copy()

        # Serialize displays for storage and replay
        displays_def = []
        for display in request.displays:
            displays_def.append({
                "type": display.type.value if hasattr(display.type, 'value') else str(display.type),
                "data": display.data,
            })

        # Store under a key based on request title
        ctx_key = f"ecs_{request.title}"
        updated_ctx[ctx_key] = {
            "type": "visual_display",
            "displays": displays_def,
            "displays_def": displays_def,  # For replay capability
            "timestamp": datetime.now().isoformat(),
        }

        # Check size limit before updating
        ctx_json = json.dumps(updated_ctx)
        if len(ctx_json.encode('utf-8')) > MAX_CONTEXT_VARIABLES_SIZE:
            # Remove oldest entries to make room (LRU eviction)
            updated_ctx = _evict_oldest_context_entries(updated_ctx, ctx_key)
            logger.warning(f"[ECS] Context variables exceeded size limit, evicted oldest entries")

        # Update working memory
        memory_manager.update_working_memory(
            session_id,
            context_variables=updated_ctx,
        )
        logger.info(f"[ECS] Persisted display data to working memory: {ctx_key}")

    except Exception as e:
        logger.warning(f"[ECS] Failed to persist display to working memory: {e}")


def _evict_oldest_context_entries(
    ctx: Dict[str, Any],
    preserve_key: str,
) -> Dict[str, Any]:
    """Evict oldest context entries to make room for new data.

    Args:
        ctx: Current context variables
        preserve_key: Key to preserve (the new entry)

    Returns:
        Updated context with oldest entries removed
    """
    import json

    # Sort entries by timestamp (if available), remove oldest first
    entries_with_time = []
    for key, value in ctx.items():
        if key == preserve_key:
            continue
        if isinstance(value, dict) and "timestamp" in value:
            entries_with_time.append((key, value.get("timestamp", "")))
        else:
            # Entries without timestamp are considered oldest
            entries_with_time.append((key, ""))

    # Sort by timestamp ascending (oldest first)
    entries_with_time.sort(key=lambda x: x[1])

    # Remove entries until under size limit
    result = ctx.copy()
    for key, _ in entries_with_time:
        del result[key]
        if len(json.dumps(result).encode('utf-8')) <= MAX_CONTEXT_VARIABLES_SIZE:
            break

    return result


def _save_image_memory(
    request: ECSRequest,
    data: Dict[str, Any],
    session_id: str,
) -> None:
    """Save image-extracted memory to long-term memory.

    Handles the image_memory_confirm ECS type with fields: key, value, category.
    If user changed category to 'plan', delegates to _save_image_plan.

    Args:
        request: Original ECS request
        data: Form data containing key, value, category
        session_id: Session ID
    """
    logger.info(f"[ECS] ---- _save_image_memory START ----")
    try:
        key = data.get("key", "")
        value = data.get("value", "")
        category = data.get("category", "fact")

        logger.info(f"[ECS] key: {key[:50] if key else 'EMPTY'}...")
        logger.info(f"[ECS] value length: {len(value) if value else 0}")
        logger.info(f"[ECS] category: {category}")

        if not key or not value:
            logger.info(f"[ECS] ERROR: missing required fields (key={bool(key)}, value={bool(value)})")
            logger.warning("[ECS] Image memory form missing required fields")
            return

        # If user changed category to 'plan', delegate to plan handler
        if category == "plan":
            logger.info(f"[ECS] -> category is 'plan', delegating to _save_image_plan")
            logger.info(f"[ECS] User changed category to 'plan', delegating to plan handler")
            _save_image_plan(request, data, session_id)
            return

        logger.info(f"[ECS] -> saving as memory entry with category: {category}")
        memory_manager.create_memory_entry(
            category=category,
            key=key,
            value=value,
            session_id=session_id,
            confidence=0.9,
            source="image_extraction",
        )
        logger.info(f"[ECS] -> SUCCESS: saved memory entry [{category}] {key[:30]}...")
        logger.info(f"[ECS] Saved image memory: [{category}] {key}")

    except Exception as e:
        logger.info(f"[ECS] ERROR: exception in _save_image_memory: {e}")
        logger.warning(f"[ECS] Failed to save image memory: {e}")
    finally:
        logger.info(f"[ECS] ---- _save_image_memory END ----")


def _save_image_plan(
    request: ECSRequest,
    data: Dict[str, Any],
    session_id: str,
) -> None:
    """Save image-extracted plan to long-term memory.

    Handles the image_plan_confirm ECS type with fields:
    key, value, category, target_time, location, participants.
    If user changed category to non-plan type, delegates to _save_image_memory.

    Args:
        request: Original ECS request
        data: Form data containing plan fields
        session_id: Session ID
    """
    logger.info(f"[ECS] ---- _save_image_plan START ----")
    try:
        category = data.get("category", "plan")
        title = data.get("key", "")
        value = data.get("value", "")
        target_time_str = data.get("target_time", "")
        location = data.get("location", "")
        participants = data.get("participants", "")

        logger.info(f"[ECS] category: {category}")
        logger.info(f"[ECS] title: {title[:50] if title else 'EMPTY'}...")
        logger.info(f"[ECS] target_time_str: {target_time_str or 'EMPTY'}")
        logger.info(f"[ECS] location: {location or 'EMPTY'}")
        logger.info(f"[ECS] participants: {participants or 'EMPTY'}")

        # If user changed category to non-plan type, delegate to memory handler
        if category != "plan":
            logger.info(f"[ECS] -> category is NOT 'plan', delegating to _save_image_memory")
            logger.info(f"[ECS] User changed category to '{category}', delegating to memory handler")
            _save_image_memory(request, data, session_id)
            return

        if not title:
            logger.info(f"[ECS] ERROR: title is required but empty")
            logger.warning("[ECS] Image plan form missing required title field")
            return

        # Build description with location and participants
        description_parts = [value] if value else []
        if location:
            description_parts.append(f"地点: {location}")
        if participants:
            description_parts.append(f"参与者: {participants}")
        description = "\n".join(description_parts) if description_parts else None

        # Parse target datetime, use default if not provided
        # (e.g., when user changed category from non-plan to plan)
        if target_time_str:
            logger.info(f"[ECS] -> parsing target_time from string: {target_time_str}")
            target_time = datetime.fromisoformat(target_time_str.replace("Z", "+00:00"))
        else:
            # Default to tomorrow 9:00 AM if target_time not provided
            tomorrow = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
            tomorrow = tomorrow + timedelta(days=1)
            target_time = tomorrow
            logger.info(f"[ECS] -> no target_time provided, using default: {target_time}")
            logger.info(f"[ECS] No target_time provided, using default: {target_time}")

        logger.info(f"[ECS] -> creating plan: title={title[:30]}..., target_time={target_time}")
        # Create the plan
        plan = memory_manager.create_plan(
            title=title,
            description=description,
            target_time=target_time,
            session_id=session_id,
            reminder_offset_minutes=10,  # Default reminder
            repeat_type="none",
        )

        logger.info(f"[ECS] -> SUCCESS: created plan id={plan.id}")
        logger.info(f"[ECS] Created image plan: {plan.id} - {title} at {target_time}")

    except Exception as e:
        logger.info(f"[ECS] ERROR: exception in _save_image_plan: {e}")
        import traceback
        traceback.print_exc()
        logger.warning(f"[ECS] Failed to create image plan: {e}")
    finally:
        logger.info(f"[ECS] ---- _save_image_plan END ----")


def _save_plan(
    request: ECSRequest,
    data: Dict[str, Any],
    session_id: str,
) -> None:
    """Save ECS plan form data as a plan entry in long_term_memory.

    Plans are stored as memory entries with category='plan' and time-specific
    fields (target_time, reminder_offset_minutes, repeat_type, etc.)

    Args:
        request: Original ECS request
        data: Form data containing plan fields
        session_id: Session ID
    """
    try:
        title = data.get("title", "")
        description = data.get("description", "")
        target_datetime_str = data.get("target_datetime", "")
        reminder_offset_raw = data.get("reminder_offset")
        reminder_offset = int(reminder_offset_raw) if reminder_offset_raw is not None and reminder_offset_raw != "" else 10
        repeat_type = data.get("repeat_type", "none")

        if not title or not target_datetime_str:
            logger.warning("[ECS] Plan form missing required fields")
            return

        # Parse target datetime
        target_time = datetime.fromisoformat(target_datetime_str.replace("Z", "+00:00"))

        # Create the plan in long_term_memory table
        plan = memory_manager.create_plan(
            title=title,
            description=description if description else None,
            target_time=target_time,
            session_id=session_id,
            reminder_offset_minutes=reminder_offset,
            repeat_type=repeat_type,
        )

        logger.info(f"[ECS] Created plan in long_term_memory: {plan.id} - {title} at {target_time}")

    except Exception as e:
        logger.warning(f"[ECS] Failed to create plan: {e}")


def _save_to_memory(
    request: ECSRequest,
    data: Dict[str, Any],
    session_id: str,
) -> None:
    """Save ECS form data to long-term memory.

    Args:
        request: Original ECS request
        data: Form data to save
        session_id: Session ID
    """
    category = "preference"
    if request.context and request.context.memory_category:
        category = request.context.memory_category

    # Save each field as a separate memory entry
    for field in request.fields:
        if field.name in data and data[field.name]:
            value = data[field.name]

            # Format value for display
            if field.options and not isinstance(value, list):
                # Look up label for single select
                for opt in field.options:
                    if opt.value == value:
                        value = opt.label
                        break

            try:
                memory_manager.create_memory_entry(
                    category=category,
                    key=field.label,
                    value=value,
                    session_id=session_id,
                    confidence=0.9,
                    source="ecs_form",
                )
                logger.info(f"[ECS] Saved memory: [{category}] {field.label}: {value}")
            except Exception as e:
                logger.warning(f"[ECS] Failed to save memory: {e}")


def extract_ecs_from_llm_response(response_text: str) -> Optional[Union[ECSRequest, ECSDisplayRequest]]:
    """Extract ECS request from LLM JSON response.

    Args:
        response_text: Raw LLM response text (should be JSON)

    Returns:
        ECSRequest or ECSDisplayRequest if found and valid, None otherwise
    """
    import json

    try:
        # Strip markdown code block if present
        json_text = response_text.strip()
        if json_text.startswith("```"):
            lines = json_text.split("\n")
            # Find start (skip first line with ```)
            start_idx = 1 if lines[0].startswith("```") else 0
            # Find end (skip last line with ```)
            end_idx = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
            json_text = "\n".join(lines[start_idx:end_idx])

        data = json.loads(json_text.strip())

        # Debug: print all top-level keys in the response
        logger.info(f"[ECS] LLM response keys: {list(data.keys())}")

        if "ecs_request" not in data:
            logger.info(f"[ECS] No ecs_request found. Response preview: {response_text[:300]}...")
            return None

        ecs_data = data["ecs_request"]
        ecs_type = ecs_data.get("type", "form")
        logger.info(f"[ECS] Found ecs_request, type={ecs_type}")
        logger.info(f"[ECS] Raw ecs_request: {json.dumps(ecs_data, ensure_ascii=False)[:500]}")

        result = parse_ecs_request_from_dict(data["ecs_request"])

        if result:
            logger.info(f"[ECS] Successfully parsed: id={result.id}, type={result.type}, title={result.title}")
        else:
            logger.info(f"[ECS] Failed to parse ecs_request: {json.dumps(ecs_data, ensure_ascii=False)[:200]}")

        return result

    except json.JSONDecodeError as e:
        logger.info(f"[ECS] Response is not valid JSON: {e}")
        logger.info(f"[ECS] Raw response: {response_text[:300]}...")
        return None
    except Exception as e:
        logger.info(f"[ECS] Failed to parse ECS request: {e}")
        return None


def assess_form_complexity(
    form_data: Optional[Dict[str, Any]],
    field_labels: Optional[Dict[str, str]] = None,
) -> ComplexityLevel:
    """Assess the complexity of a submitted ECS form.

    Complexity is determined by:
    - Number of fields with data
    - Total content length of all field values

    Args:
        form_data: Dictionary of field names to values
        field_labels: Optional mapping of field names to labels

    Returns:
        ComplexityLevel enum value
    """
    if not form_data:
        return ComplexityLevel.LOW

    # Count non-empty fields
    field_count = 0
    total_content_length = 0

    for field_name, value in form_data.items():
        if value is None:
            continue

        if isinstance(value, list):
            value_str = ", ".join(str(v) for v in value)
        else:
            value_str = str(value)

        if value_str.strip():
            field_count += 1
            total_content_length += len(value_str)

    # Determine complexity level based on thresholds
    # High: >= 5 fields OR >= 200 characters
    # Medium: >= 3 fields OR >= 100 characters
    # Low: otherwise
    if field_count >= 5 or total_content_length >= 200:
        return ComplexityLevel.HIGH
    elif field_count >= 3 or total_content_length >= 100:
        return ComplexityLevel.MEDIUM
    else:
        return ComplexityLevel.LOW


def get_response_guidance(complexity: ComplexityLevel, action: str) -> str:
    """Get response quality guidance based on form complexity.

    Args:
        complexity: The assessed complexity level
        action: The user's action ("approve" or "reject")

    Returns:
        Guidance text for LLM prompt
    """
    # For reject actions, always use simple guidance
    if action == "reject":
        return "请简洁地回应用户的选择，可以换一种方式提问、跳过该话题或表达理解。"

    if complexity == ComplexityLevel.HIGH:
        return """请根据用户提供的详细信息，给出全面、深入的响应：
1. 分析用户的需求和偏好
2. 提供具体、可操作的建议（至少3-5条）
3. 如适用，给出分步骤的计划或方案
4. 根据用户的约束条件（预算、时间等）调整建议
5. 主动补充用户可能没想到但有价值的信息

注意：响应应详尽但有条理，避免冗长的废话。用户花费了大量时间填写表单，请确保你的回复能给他们带来实质性的帮助。"""

    elif complexity == ComplexityLevel.MEDIUM:
        return """请根据用户的输入提供有价值的响应：
1. 确认理解用户的需求
2. 提供2-3条具体建议
3. 如有疑问，可以追问细节

确保回复有实质性内容，避免空洞的确认。"""

    else:  # LOW
        return "请简洁地回应用户的选择，并询问是否需要进一步帮助。"


def build_continuation_context(continuation_data: ECSContinuationData) -> str:
    """Build context string for LLM continuation based on user's ECS response.

    Args:
        continuation_data: Data from ECS response

    Returns:
        Formatted context string for LLM prompt
    """
    if continuation_data.action == "reject":
        guidance = get_response_guidance(ComplexityLevel.LOW, "reject")
        return f"""用户刚才跳过了表单 "{continuation_data.request_title}"。
用户选择不填写此表单。

【响应要求】
{guidance}"""

    # Action is approve
    if not continuation_data.form_data:
        guidance = get_response_guidance(ComplexityLevel.LOW, "approve")
        return f"""用户确认了表单 "{continuation_data.request_title}"，但未填写任何数据。

【响应要求】
{guidance}"""

    # Assess form complexity
    complexity = assess_form_complexity(
        continuation_data.form_data,
        continuation_data.field_labels,
    )
    guidance = get_response_guidance(complexity, "approve")

    logger.info(f"[ECS] Form complexity assessed: {complexity.value} for '{continuation_data.request_title}'")

    # Format the form data with labels
    data_lines = []
    for field_name, value in continuation_data.form_data.items():
        label = continuation_data.field_labels.get(field_name, field_name)
        if isinstance(value, list):
            value_str = ", ".join(str(v) for v in value)
        else:
            value_str = str(value)
        if value_str:  # Only include non-empty values
            data_lines.append(f"- {label}: {value_str}")

    if not data_lines:
        guidance = get_response_guidance(ComplexityLevel.LOW, "approve")
        return f"""用户确认了表单 "{continuation_data.request_title}"，但未填写任何数据。

【响应要求】
{guidance}"""

    data_str = "\n".join(data_lines)
    return f"""用户刚才通过表单提交了以下信息:
表单标题: {continuation_data.request_title}
{data_str}

【响应要求】
{guidance}"""
