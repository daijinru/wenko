"""Tests for ExecutionContract state machine, ToolNode, and ECSNode contract integration.

Covers:
- ExecutionStatus transitions (valid and invalid)
- ExecutionContract lifecycle
- Idempotency key checking
- ToolNode contract state advancement
- ECSNode suspend transitions
"""

import pytest
import asyncio
import sys
import os
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.state import (
    GraphState,
    SemanticInput,
    ExecutionStatus,
    ExecutionContract,
    InvalidTransitionError,
    TERMINAL_STATUSES,
    compute_idempotency_key,
    can_create_contract,
    ExecutionStep,
    ECSRequest,
)


class TestExecutionStatusTransitions:
    """Test all valid and invalid state transitions."""

    def test_pending_to_running(self):
        c = ExecutionContract(action_type="tool_call")
        c.transition("start", actor="tool_node")
        assert c.status == ExecutionStatus.RUNNING
        assert len(c.transitions) == 1
        assert c.transitions[0]["from"] == "pending"
        assert c.transitions[0]["to"] == "running"
        assert c.transitions[0]["trigger"] == "start"
        assert c.transitions[0]["actor"] == "tool_node"

    def test_running_to_completed(self):
        c = ExecutionContract(action_type="tool_call")
        c.transition("start", actor="tool_node")
        c.transition("succeed", actor="tool_node")
        assert c.status == ExecutionStatus.COMPLETED
        assert c.is_terminal

    def test_running_to_failed(self):
        c = ExecutionContract(action_type="tool_call")
        c.transition("start", actor="tool_node")
        c.transition("fail", actor="tool_node")
        assert c.status == ExecutionStatus.FAILED
        assert c.is_terminal

    def test_running_to_rejected(self):
        c = ExecutionContract(action_type="tool_call")
        c.transition("start", actor="tool_node")
        c.transition("reject", actor="tool_node")
        assert c.status == ExecutionStatus.REJECTED
        assert c.is_terminal

    def test_running_to_waiting(self):
        c = ExecutionContract(action_type="ecs_request")
        c.transition("start", actor="ecs_node")
        c.transition("suspend", actor="ecs_node")
        assert c.status == ExecutionStatus.WAITING
        assert not c.is_terminal

    def test_running_to_cancelled(self):
        c = ExecutionContract(action_type="tool_call")
        c.transition("start", actor="tool_node")
        c.transition("cancel", actor="graph_runner")
        assert c.status == ExecutionStatus.CANCELLED
        assert c.is_terminal

    def test_waiting_to_running_resume(self):
        c = ExecutionContract(action_type="ecs_request")
        c.transition("start", actor="ecs_node")
        c.transition("suspend", actor="ecs_node")
        c.transition("resume", actor="graph_runner")
        assert c.status == ExecutionStatus.RUNNING
        assert len(c.transitions) == 3

    def test_waiting_to_cancelled(self):
        c = ExecutionContract(action_type="ecs_request")
        c.transition("start", actor="ecs_node")
        c.transition("suspend", actor="ecs_node")
        c.transition("cancel", actor="graph_runner")
        assert c.status == ExecutionStatus.CANCELLED

    def test_waiting_timeout_to_cancelled(self):
        c = ExecutionContract(action_type="ecs_request")
        c.transition("start", actor="ecs_node")
        c.transition("suspend", actor="ecs_node")
        c.transition("timeout", actor="graph_runner")
        assert c.status == ExecutionStatus.CANCELLED

    def test_invalid_pending_to_completed(self):
        c = ExecutionContract(action_type="tool_call")
        with pytest.raises(InvalidTransitionError):
            c.transition("succeed", actor="tool_node")
        assert c.status == ExecutionStatus.PENDING

    def test_invalid_completed_to_any(self):
        c = ExecutionContract(action_type="tool_call")
        c.transition("start", actor="tool_node")
        c.transition("succeed", actor="tool_node")
        for trigger in ["start", "succeed", "fail", "reject", "suspend", "cancel", "resume"]:
            with pytest.raises(InvalidTransitionError):
                c.transition(trigger, actor="test")
        assert c.status == ExecutionStatus.COMPLETED

    def test_invalid_failed_to_any(self):
        c = ExecutionContract(action_type="tool_call")
        c.transition("start", actor="tool_node")
        c.transition("fail", actor="tool_node")
        with pytest.raises(InvalidTransitionError):
            c.transition("start", actor="test")
        assert c.status == ExecutionStatus.FAILED

    def test_invalid_waiting_to_completed(self):
        c = ExecutionContract(action_type="ecs_request")
        c.transition("start", actor="ecs_node")
        c.transition("suspend", actor="ecs_node")
        with pytest.raises(InvalidTransitionError):
            c.transition("succeed", actor="test")
        assert c.status == ExecutionStatus.WAITING

    def test_full_ecs_lifecycle(self):
        """PENDING → RUNNING → WAITING → RUNNING → COMPLETED"""
        c = ExecutionContract(action_type="ecs_request")
        c.transition("start", actor="ecs_node")
        c.transition("suspend", actor="ecs_node")
        c.transition("resume", actor="graph_runner")
        c.transition("succeed", actor="graph_runner")
        assert c.status == ExecutionStatus.COMPLETED
        assert len(c.transitions) == 4


class TestExecutionContract:
    """Test ExecutionContract properties and defaults."""

    def test_unique_execution_id(self):
        c1 = ExecutionContract(action_type="tool_call")
        c2 = ExecutionContract(action_type="tool_call")
        assert c1.execution_id != c2.execution_id

    def test_default_status_is_pending(self):
        c = ExecutionContract(action_type="tool_call")
        assert c.status == ExecutionStatus.PENDING

    def test_is_terminal_property(self):
        for status in TERMINAL_STATUSES:
            c = ExecutionContract(action_type="tool_call", status=status)
            assert c.is_terminal

        c = ExecutionContract(action_type="tool_call", status=ExecutionStatus.PENDING)
        assert not c.is_terminal
        c = ExecutionContract(action_type="tool_call", status=ExecutionStatus.RUNNING)
        assert not c.is_terminal
        c = ExecutionContract(action_type="tool_call", status=ExecutionStatus.WAITING)
        assert not c.is_terminal

    def test_serialization_roundtrip(self):
        c = ExecutionContract(
            action_type="tool_call",
            action_detail={"service": "email", "method": "send"},
            irreversible=True,
        )
        c.transition("start", actor="tool_node")
        c.transition("succeed", actor="tool_node")
        c.result = "sent"

        data = c.model_dump()
        c2 = ExecutionContract.model_validate(data)
        assert c2.status == ExecutionStatus.COMPLETED
        assert c2.result == "sent"
        assert c2.irreversible is True
        assert len(c2.transitions) == 2


class TestIdempotencyKey:
    """Test idempotency key computation and duplicate prevention."""

    def test_compute_key(self):
        detail = {"service": "email", "method": "send", "args": {"to": "a@b.com"}}
        key = compute_idempotency_key(detail)
        assert key is not None
        assert key.startswith("email:send:")

    def test_same_args_same_key(self):
        detail = {"service": "email", "method": "send", "args": {"to": "a@b.com"}}
        assert compute_idempotency_key(detail) == compute_idempotency_key(detail)

    def test_different_args_different_key(self):
        d1 = {"service": "email", "method": "send", "args": {"to": "a@b.com"}}
        d2 = {"service": "email", "method": "send", "args": {"to": "c@d.com"}}
        assert compute_idempotency_key(d1) != compute_idempotency_key(d2)

    def test_missing_service_returns_none(self):
        assert compute_idempotency_key({"method": "send"}) is None

    def test_can_create_blocks_completed_irreversible(self):
        detail = {"service": "email", "method": "send", "args": {"to": "a@b.com"}}
        key = compute_idempotency_key(detail)
        existing = ExecutionContract(
            action_type="tool_call",
            action_detail=detail,
            irreversible=True,
            idempotency_key=key,
            status=ExecutionStatus.COMPLETED,
        )
        assert can_create_contract(detail, [existing]) is False

    def test_can_create_allows_failed_irreversible(self):
        detail = {"service": "email", "method": "send", "args": {"to": "a@b.com"}}
        key = compute_idempotency_key(detail)
        existing = ExecutionContract(
            action_type="tool_call",
            action_detail=detail,
            irreversible=True,
            idempotency_key=key,
            status=ExecutionStatus.FAILED,
        )
        assert can_create_contract(detail, [existing]) is True

    def test_can_create_allows_non_irreversible(self):
        detail = {"service": "search", "method": "query", "args": {"q": "test"}}
        key = compute_idempotency_key(detail)
        existing = ExecutionContract(
            action_type="tool_call",
            action_detail=detail,
            irreversible=False,
            idempotency_key=key,
            status=ExecutionStatus.COMPLETED,
        )
        assert can_create_contract(detail, [existing]) is True


class TestGraphStateWithContracts:
    """Test GraphState with execution contract fields."""

    def test_default_empty_executions(self):
        state = GraphState(conversation_id="test-1")
        assert state.pending_executions == []
        assert state.completed_executions == []

    def test_state_with_contracts(self):
        c = ExecutionContract(action_type="tool_call", action_detail={"service": "s", "method": "m"})
        state = GraphState(
            conversation_id="test-1",
            pending_executions=[c],
        )
        assert len(state.pending_executions) == 1
        assert state.pending_executions[0].action_type == "tool_call"

    def test_state_serialization_with_contracts(self):
        c = ExecutionContract(action_type="tool_call")
        c.transition("start", actor="tool_node")
        state = GraphState(
            conversation_id="test-1",
            pending_executions=[c],
        )
        data = state.model_dump()
        state2 = GraphState.model_validate(data)
        assert state2.pending_executions[0].status == ExecutionStatus.RUNNING


class TestToolNodeContractIntegration:
    """Test ToolNode with ExecutionContract state transitions."""

    @pytest.mark.asyncio
    async def test_successful_tool_execution_advances_contract(self):
        from core.nodes.tool_node import ToolNode

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.result = "search results here"

        contract = ExecutionContract(
            action_type="tool_call",
            action_detail={"service": "search", "method": "query", "args": {"q": "test"}},
        )

        state = GraphState(
            conversation_id="test-1",
            pending_executions=[contract],
            pending_tool_calls=[{"service": "search", "method": "query", "args": {"q": "test"}}],
        )

        node = ToolNode()
        with patch("core.nodes.tool_node.execute_mcp_tool", new_callable=AsyncMock, return_value=mock_result):
            result = await node.execute(state)

        assert result["pending_tool_calls"] == []
        assert "observation" in result
        # Contract should be in completed_executions
        assert len(result.get("completed_executions", [])) == 1
        completed = result["completed_executions"][0]
        assert completed.status == ExecutionStatus.COMPLETED
        assert completed.result == "search results here"
        assert result["pending_executions"] == []

    @pytest.mark.asyncio
    async def test_failed_tool_execution_fails_contract(self):
        from core.nodes.tool_node import ToolNode

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error = "connection refused"

        contract = ExecutionContract(
            action_type="tool_call",
            action_detail={"service": "email", "method": "send", "args": {}},
        )

        state = GraphState(
            conversation_id="test-1",
            pending_executions=[contract],
            pending_tool_calls=[{"service": "email", "method": "send", "args": {}}],
        )

        node = ToolNode()
        with patch("core.nodes.tool_node.execute_mcp_tool", new_callable=AsyncMock, return_value=mock_result):
            result = await node.execute(state)

        completed = result["completed_executions"][0]
        assert completed.status == ExecutionStatus.FAILED
        assert completed.error_message == "connection refused"

    @pytest.mark.asyncio
    async def test_exception_during_tool_fails_contract(self):
        from core.nodes.tool_node import ToolNode

        contract = ExecutionContract(
            action_type="tool_call",
            action_detail={"service": "broken", "method": "call", "args": {}},
        )

        state = GraphState(
            conversation_id="test-1",
            pending_executions=[contract],
            pending_tool_calls=[{"service": "broken", "method": "call", "args": {}}],
        )

        node = ToolNode()
        with patch("core.nodes.tool_node.execute_mcp_tool", new_callable=AsyncMock, side_effect=Exception("boom")):
            result = await node.execute(state)

        completed = result["completed_executions"][0]
        assert completed.status == ExecutionStatus.FAILED
        assert "boom" in completed.error_message


class TestECSNodeContractIntegration:
    """Test ECSNode with ExecutionContract state transitions."""

    @pytest.mark.asyncio
    async def test_ecs_suspends_contract(self):
        from core.nodes.ecs import ECSNode

        contract = ExecutionContract(
            action_type="ecs_request",
            action_detail={"type": "form", "message": "confirm?"},
        )

        state = GraphState(
            conversation_id="test-1",
            ecs_request=ECSRequest(type="form", message="confirm?"),
            pending_executions=[contract],
        )

        node = ECSNode()
        result = await node.execute(state)

        assert result["status"] == "suspended"
        assert len(result["completed_executions"]) == 1
        suspended = result["completed_executions"][0]
        assert suspended.status == ExecutionStatus.WAITING
        assert result["pending_executions"] == []

    @pytest.mark.asyncio
    async def test_ecs_without_request_skips(self):
        from core.nodes.ecs import ECSNode

        state = GraphState(conversation_id="test-1")
        node = ECSNode()
        result = await node.execute(state)
        assert result["status"] == "processing"


class TestExecutionTrace:
    """Test that execution trace records contract transitions."""

    def test_transition_record_structure(self):
        c = ExecutionContract(action_type="tool_call")
        c.transition("start", actor="tool_node")
        assert len(c.transitions) == 1
        t = c.transitions[0]
        assert t["from"] == "pending"
        assert t["to"] == "running"
        assert t["trigger"] == "start"
        assert t["actor"] == "tool_node"
        assert "timestamp" in t
