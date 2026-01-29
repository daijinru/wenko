"""HITL Handler Module

Handles HITL request processing, state management, and memory integration.
"""

import logging
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Dict, Optional, Union

import memory_manager
from enum import Enum

from hitl_schema import (
    HITLAction,
    HITLContinuationData,
    HITLDisplayRequest,
    HITLRequest,
    HITLResponseData,
    HITLResponseResult,
    parse_hitl_request_from_dict,
)


class ComplexityLevel(Enum):
    """Form complexity levels for response guidance."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

logger = logging.getLogger(__name__)

# In-memory storage for pending HITL requests
# Key: request_id, Value: (HITLRequest, session_id, expires_at)
_pending_requests: Dict[str, tuple] = {}
_lock = Lock()


def store_hitl_request(request: HITLRequest, session_id: str) -> None:
    """Store a pending HITL request.

    Args:
        request: The HITL request to store
        session_id: Associated session ID
    """
    expires_at = datetime.now() + timedelta(seconds=request.ttl_seconds)
    with _lock:
        _pending_requests[request.id] = (request, session_id, expires_at)
    logger.info(f"[HITL] Stored request {request.id} for session {session_id[:8]}...")


def store_display_request(request: HITLDisplayRequest, session_id: str) -> None:
    """Store a pending HITL visual display request.

    Args:
        request: The HITL display request to store
        session_id: Associated session ID
    """
    expires_at = datetime.now() + timedelta(seconds=request.ttl_seconds)
    with _lock:
        _pending_requests[request.id] = (request, session_id, expires_at)
    logger.info(f"[HITL] Stored display request {request.id} for session {session_id[:8]}...")


def get_hitl_request(request_id: str) -> Optional[tuple]:
    """Get a pending HITL request.

    Args:
        request_id: The request ID to look up

    Returns:
        Tuple of (HITLRequest, session_id, expires_at) or None if not found/expired
    """
    with _lock:
        if request_id not in _pending_requests:
            return None

        request, session_id, expires_at = _pending_requests[request_id]

        # Check expiration
        if datetime.now() > expires_at:
            del _pending_requests[request_id]
            logger.info(f"[HITL] Request {request_id} expired")
            return None

        return (request, session_id, expires_at)


def remove_hitl_request(request_id: str) -> bool:
    """Remove a HITL request from storage.

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
        logger.info(f"[HITL] Cleaned up {len(expired)} expired requests")

    return len(expired)


def process_hitl_response(response: HITLResponseData) -> HITLResponseResult:
    """Process user response to a HITL request.

    Args:
        response: The user's response data

    Returns:
        HITLResponseResult indicating success/failure and next action
    """
    # Get the original request
    request_data = get_hitl_request(response.request_id)

    if request_data is None:
        return HITLResponseResult(
            success=False,
            next_action="complete",
            error="请求已过期或不存在",
        )

    request, session_id, _ = request_data

    # Verify session ID matches
    if session_id != response.session_id:
        return HITLResponseResult(
            success=False,
            next_action="complete",
            error="会话不匹配",
        )

    # Handle visual_display type (dismiss only)
    if isinstance(request, HITLDisplayRequest):
        return _process_display_dismiss(request, session_id, response.request_id)

    # Build field labels mapping for continuation context
    field_labels = {field.name: field.label for field in request.fields}

    # Handle based on action
    if response.action == HITLAction.REJECT:
        # User rejected, build continuation data
        remove_hitl_request(response.request_id)
        logger.info(f"[HITL] User rejected request {response.request_id}")
        continuation_data = HITLContinuationData(
            request_title=request.title,
            action="reject",
            form_data=None,
            field_labels=field_labels,
        )
        return HITLResponseResult(
            success=True,
            next_action="continue",
            message="已跳过",
            continuation_data=continuation_data,
        )

    if response.action in (HITLAction.APPROVE, HITLAction.EDIT):
        # Process the form data
        result = _process_form_data(request, response.data, session_id)
        remove_hitl_request(response.request_id)
        # Add continuation data to result
        if result.success:
            result.continuation_data = HITLContinuationData(
                request_title=request.title,
                action="approve",
                form_data=response.data,
                field_labels=field_labels,
            )
        return result

    return HITLResponseResult(
        success=False,
        next_action="complete",
        error="未知操作",
    )


def _process_display_dismiss(
    request: HITLDisplayRequest,
    session_id: str,
    request_id: str,
) -> HITLResponseResult:
    """Process dismiss action for visual display request.

    Args:
        request: The display request
        session_id: Session ID
        request_id: Request ID

    Returns:
        HITLResponseResult indicating success
    """
    # Persist display to working memory before removing
    _persist_display_to_working_memory(request, session_id)

    # Remove the request
    remove_hitl_request(request_id)
    logger.info(f"[HITL] User dismissed display request {request_id}")

    # Visual display doesn't trigger continuation
    return HITLResponseResult(
        success=True,
        next_action="complete",
        message="已关闭",
    )


def _process_form_data(
    request: HITLRequest,
    data: Optional[Dict[str, Any]],
    session_id: str,
) -> HITLResponseResult:
    """Process form data from user response.

    Args:
        request: Original HITL request
        data: Form data from user
        session_id: Session ID

    Returns:
        HITLResponseResult
    """
    if data is None:
        data = {}

    # Validate required fields
    for field in request.fields:
        if field.required and field.name not in data:
            return HITLResponseResult(
                success=False,
                next_action="continue",
                error=f"必填字段 '{field.label}' 未填写",
            )

    # Check if we should save to memory based on intent or request type
    if request.context and request.context.intent == "collect_preference":
        _save_to_memory(request, data, session_id)
    elif request.context and request.context.intent == "collect_plan":
        _save_plan(request, data, session_id)
    # Handle image memory/plan types
    elif request.type == "image_memory_confirm":
        _save_image_memory(request, data, session_id)
    elif request.type == "image_plan_confirm":
        _save_image_plan(request, data, session_id)

    # Persist form data to working memory for session context continuity
    _persist_to_working_memory(request, data, session_id)

    logger.info(f"[HITL] Processed form data for request {request.id}")

    return HITLResponseResult(
        success=True,
        next_action="continue",
        message="已保存",
    )


# Maximum size for context_variables in bytes (to prevent unbounded growth)
MAX_CONTEXT_VARIABLES_SIZE = 64 * 1024  # 64KB


def _persist_to_working_memory(
    request: HITLRequest,
    data: Dict[str, Any],
    session_id: str,
) -> None:
    """Persist HITL form data to working memory for session context continuity.

    This ensures that form submissions are available in subsequent conversations
    within the same session.

    Args:
        request: Original HITL request
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
        ctx_key = f"hitl_{request.title}"
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
            logger.warning(f"[HITL] Context variables exceeded size limit, evicted oldest entries")

        # Update working memory
        memory_manager.update_working_memory(
            session_id,
            context_variables=updated_ctx,
        )
        logger.info(f"[HITL] Persisted form data to working memory: {ctx_key}")

    except Exception as e:
        logger.warning(f"[HITL] Failed to persist to working memory: {e}")


def _persist_display_to_working_memory(
    request: HITLDisplayRequest,
    session_id: str,
) -> None:
    """Persist HITL visual display data to working memory for session context continuity.

    This ensures that visual displays are available for replay in subsequent sessions.

    Args:
        request: Original HITL display request
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
        ctx_key = f"hitl_{request.title}"
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
            logger.warning(f"[HITL] Context variables exceeded size limit, evicted oldest entries")

        # Update working memory
        memory_manager.update_working_memory(
            session_id,
            context_variables=updated_ctx,
        )
        logger.info(f"[HITL] Persisted display data to working memory: {ctx_key}")

    except Exception as e:
        logger.warning(f"[HITL] Failed to persist display to working memory: {e}")


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
    request: HITLRequest,
    data: Dict[str, Any],
    session_id: str,
) -> None:
    """Save image-extracted memory to long-term memory.

    Handles the image_memory_confirm HITL type with fields: key, value, category.

    Args:
        request: Original HITL request
        data: Form data containing key, value, category
        session_id: Session ID
    """
    try:
        key = data.get("key", "")
        value = data.get("value", "")
        category = data.get("category", "fact")

        if not key or not value:
            logger.warning("[HITL] Image memory form missing required fields")
            return

        memory_manager.create_memory_entry(
            category=category,
            key=key,
            value=value,
            session_id=session_id,
            confidence=0.9,
            source="image_extraction",
        )
        logger.info(f"[HITL] Saved image memory: [{category}] {key}")

    except Exception as e:
        logger.warning(f"[HITL] Failed to save image memory: {e}")


def _save_image_plan(
    request: HITLRequest,
    data: Dict[str, Any],
    session_id: str,
) -> None:
    """Save image-extracted plan to long-term memory.

    Handles the image_plan_confirm HITL type with fields:
    key, value, category, target_time, location, participants.

    Args:
        request: Original HITL request
        data: Form data containing plan fields
        session_id: Session ID
    """
    try:
        title = data.get("key", "")
        value = data.get("value", "")
        target_time_str = data.get("target_time", "")
        location = data.get("location", "")
        participants = data.get("participants", "")

        if not title or not target_time_str:
            logger.warning("[HITL] Image plan form missing required fields")
            return

        # Build description with location and participants
        description_parts = [value] if value else []
        if location:
            description_parts.append(f"地点: {location}")
        if participants:
            description_parts.append(f"参与者: {participants}")
        description = "\n".join(description_parts) if description_parts else None

        # Parse target datetime
        target_time = datetime.fromisoformat(target_time_str.replace("Z", "+00:00"))

        # Create the plan
        plan = memory_manager.create_plan(
            title=title,
            description=description,
            target_time=target_time,
            session_id=session_id,
            reminder_offset_minutes=10,  # Default reminder
            repeat_type="none",
        )

        logger.info(f"[HITL] Created image plan: {plan.id} - {title} at {target_time}")

    except Exception as e:
        logger.warning(f"[HITL] Failed to create image plan: {e}")


def _save_plan(
    request: HITLRequest,
    data: Dict[str, Any],
    session_id: str,
) -> None:
    """Save HITL plan form data as a plan entry in long_term_memory.

    Plans are stored as memory entries with category='plan' and time-specific
    fields (target_time, reminder_offset_minutes, repeat_type, etc.)

    Args:
        request: Original HITL request
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
            logger.warning("[HITL] Plan form missing required fields")
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

        logger.info(f"[HITL] Created plan in long_term_memory: {plan.id} - {title} at {target_time}")

    except Exception as e:
        logger.warning(f"[HITL] Failed to create plan: {e}")


def _save_to_memory(
    request: HITLRequest,
    data: Dict[str, Any],
    session_id: str,
) -> None:
    """Save HITL form data to long-term memory.

    Args:
        request: Original HITL request
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
                    source="hitl_form",
                )
                logger.info(f"[HITL] Saved memory: [{category}] {field.label}: {value}")
            except Exception as e:
                logger.warning(f"[HITL] Failed to save memory: {e}")


def extract_hitl_from_llm_response(response_text: str) -> Optional[Union[HITLRequest, HITLDisplayRequest]]:
    """Extract HITL request from LLM JSON response.

    Args:
        response_text: Raw LLM response text (should be JSON)

    Returns:
        HITLRequest or HITLDisplayRequest if found and valid, None otherwise
    """
    import json

    try:
        data = json.loads(response_text)

        # Debug: print all top-level keys in the response
        print(f"[HITL] LLM response keys: {list(data.keys())}")

        if "hitl_request" not in data:
            print(f"[HITL] No hitl_request found. Response preview: {response_text[:300]}...")
            return None

        hitl_data = data["hitl_request"]
        hitl_type = hitl_data.get("type", "form")
        print(f"[HITL] Found hitl_request, type={hitl_type}")
        print(f"[HITL] Raw hitl_request: {json.dumps(hitl_data, ensure_ascii=False)[:500]}")

        result = parse_hitl_request_from_dict(data["hitl_request"])

        if result:
            print(f"[HITL] Successfully parsed: id={result.id}, type={result.type}, title={result.title}")
        else:
            print(f"[HITL] Failed to parse hitl_request: {json.dumps(hitl_data, ensure_ascii=False)[:200]}")

        return result

    except json.JSONDecodeError as e:
        print(f"[HITL] Response is not valid JSON: {e}")
        print(f"[HITL] Raw response: {response_text[:300]}...")
        return None
    except Exception as e:
        print(f"[HITL] Failed to parse HITL request: {e}")
        return None


def assess_form_complexity(
    form_data: Optional[Dict[str, Any]],
    field_labels: Optional[Dict[str, str]] = None,
) -> ComplexityLevel:
    """Assess the complexity of a submitted HITL form.

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


def build_continuation_context(continuation_data: HITLContinuationData) -> str:
    """Build context string for LLM continuation based on user's HITL response.

    Args:
        continuation_data: Data from HITL response

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

    logger.info(f"[HITL] Form complexity assessed: {complexity.value} for '{continuation_data.request_title}'")

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
