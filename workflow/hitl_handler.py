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

    # Handle based on action
    if response.action == HITLAction.REJECT:
        # User rejected, just clean up
        remove_hitl_request(response.request_id)
        logger.info(f"[HITL] User rejected request {response.request_id}")
        return HITLResponseResult(
            success=True,
            next_action="continue",
            message="已跳过",
        )

    if response.action in (HITLAction.APPROVE, HITLAction.EDIT):
        # Process the form data
        result = _process_form_data(request, response.data, session_id)
        remove_hitl_request(response.request_id)
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

    logger.info(f"[HITL] Processed form data for request {request.id}")

    return HITLResponseResult(
        success=True,
        next_action="continue",
        message="已保存",
    )


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
