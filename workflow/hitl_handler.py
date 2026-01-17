"""HITL Handler Module

Handles HITL request processing, state management, and memory integration.
"""

import logging
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Dict, Optional

import memory_manager
from hitl_schema import (
    HITLAction,
    HITLContinuationData,
    HITLRequest,
    HITLResponseData,
    HITLResponseResult,
    parse_hitl_request_from_dict,
)

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

    # Check if we should save to memory
    if request.context and request.context.intent == "collect_preference":
        _save_to_memory(request, data, session_id)

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

        # Store under a key based on request title
        ctx_key = f"hitl_{request.title}"
        updated_ctx[ctx_key] = {
            "fields": labeled_data,
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


def extract_hitl_from_llm_response(response_text: str) -> Optional[HITLRequest]:
    """Extract HITL request from LLM JSON response.

    Args:
        response_text: Raw LLM response text (should be JSON)

    Returns:
        HITLRequest if found and valid, None otherwise
    """
    import json

    try:
        data = json.loads(response_text)

        if "hitl_request" not in data:
            return None

        return parse_hitl_request_from_dict(data["hitl_request"])

    except json.JSONDecodeError:
        return None
    except Exception as e:
        logger.warning(f"[HITL] Failed to parse HITL request: {e}")
        return None


def build_continuation_context(continuation_data: HITLContinuationData) -> str:
    """Build context string for LLM continuation based on user's HITL response.

    Args:
        continuation_data: Data from HITL response

    Returns:
        Formatted context string for LLM prompt
    """
    if continuation_data.action == "reject":
        return f"""用户刚才跳过了表单 "{continuation_data.request_title}"。
用户选择不填写此表单。请根据用户的选择适当调整对话，可以换一种方式提问、跳过该话题或表达理解。"""

    # Action is approve
    if not continuation_data.form_data:
        return f"""用户确认了表单 "{continuation_data.request_title}"，但未填写任何数据。"""

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
        return f"""用户确认了表单 "{continuation_data.request_title}"，但未填写任何数据。"""

    data_str = "\n".join(data_lines)
    return f"""用户刚才通过表单提交了以下信息:
表单标题: {continuation_data.request_title}
{data_str}

请根据用户的选择继续对话。"""
