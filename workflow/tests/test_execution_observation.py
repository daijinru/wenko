"""Tests for the Execution Observation Layer (v1 + v1-minimal).

Covers:
- ExecutionSnapshot projection from ExecutionContract
- ExecutionConsequenceView projection with was_suspended/has_side_effects
- TransitionRecord projection
- ExecutionObserver service methods
- StateMachineTopology completeness
- ReasoningNode consequence-based prompt generation
"""

import pytest
import json
import time
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.state import (
    ExecutionStatus,
    ExecutionContract,
    ExecutionSnapshot,
    ExecutionConsequenceView,
    TransitionRecord,
    StateNode,
    StateTransitionEdge,
    StateMachineTopology,
    ExecutionTimeline,
    TERMINAL_STATUSES,
    ACTOR_CATEGORY_MAP,
    STATUS_TO_CONSEQUENCE,
    _VALID_TRANSITIONS,
)

from observation import ExecutionObserver, _generate_action_summary


# --- Helpers ---

def _make_contract(
    action_type="tool_call",
    service="email",
    method="send",
    irreversible=False,
    status=None,
    transitions=None,
    result=None,
    error_message=None,
):
    """Create a test ExecutionContract with optional pre-set state."""
    c = ExecutionContract(
        action_type=action_type,
        action_detail={"service": service, "method": method},
        irreversible=irreversible,
    )
    if transitions:
        c.transitions = transitions
    if status:
        c.status = status
    if result:
        c.result = result
    if error_message:
        c.error_message = error_message
    return c


def _make_completed_tool_contract(irreversible=False, was_suspended=False):
    """Create a COMPLETED tool contract with realistic transition history."""
    c = _make_contract(irreversible=irreversible)
    now = time.time()
    c.created_at = now - 1.0

    if was_suspended:
        c.transitions = [
            {"from": "pending", "to": "running", "trigger": "start", "timestamp": now - 0.9, "actor": "tool_node"},
            {"from": "running", "to": "waiting", "trigger": "suspend", "timestamp": now - 0.8, "actor": "ecs_node"},
            {"from": "waiting", "to": "running", "trigger": "resume", "timestamp": now - 0.3, "actor": "graph_runner"},
            {"from": "running", "to": "completed", "trigger": "succeed", "timestamp": now - 0.1, "actor": "tool_node"},
        ]
    else:
        c.transitions = [
            {"from": "pending", "to": "running", "trigger": "start", "timestamp": now - 0.5, "actor": "tool_node"},
            {"from": "running", "to": "completed", "trigger": "succeed", "timestamp": now - 0.1, "actor": "tool_node"},
        ]

    c.status = ExecutionStatus.COMPLETED
    c.result = "Email sent successfully"
    return c


def _make_failed_contract():
    """Create a FAILED tool contract."""
    c = _make_contract()
    now = time.time()
    c.created_at = now - 0.5
    c.transitions = [
        {"from": "pending", "to": "running", "trigger": "start", "timestamp": now - 0.4, "actor": "tool_node"},
        {"from": "running", "to": "failed", "trigger": "fail", "timestamp": now - 0.1, "actor": "tool_node"},
    ]
    c.status = ExecutionStatus.FAILED
    c.error_message = "SMTP connection refused"
    return c


def _make_waiting_contract():
    """Create a WAITING ecs_request contract."""
    c = _make_contract(action_type="ecs_request", service="", method="")
    c.action_detail = {"type": "form", "id": "ecs-001", "title": "Confirm email send"}
    now = time.time()
    c.created_at = now - 2.0
    c.transitions = [
        {"from": "pending", "to": "running", "trigger": "start", "timestamp": now - 1.9, "actor": "ecs_node"},
        {"from": "running", "to": "waiting", "trigger": "suspend", "timestamp": now - 1.8, "actor": "ecs_node"},
    ]
    c.status = ExecutionStatus.WAITING
    return c


# ==========================================
# Test: Observation Data Models
# ==========================================

class TestObservationDataModels:
    """Test that observation data models can be constructed and serialized."""

    def test_execution_snapshot_construction(self):
        snap = ExecutionSnapshot(
            execution_id="test-001",
            action_type="tool_call",
            action_summary="email.send",
            current_status="pending",
            entered_at=time.time(),
            duration_in_state_ms=0.0,
            is_terminal=False,
            is_stable=False,
            is_resumable=False,
            has_side_effects=False,
            irreversible=False,
            transition_count=0,
        )
        assert snap.execution_id == "test-001"
        assert snap.is_terminal is False
        data = snap.model_dump()
        assert "execution_id" in data

    def test_consequence_view_construction(self):
        cv = ExecutionConsequenceView(
            execution_id="test-001",
            action_type="tool_call",
            action_summary="email.send",
            consequence_label="SUCCESS",
            has_side_effects=True,
            was_suspended=False,
            is_still_pending=False,
        )
        assert cv.consequence_label == "SUCCESS"
        assert cv.has_side_effects is True

    def test_transition_record_construction(self):
        tr = TransitionRecord(
            execution_id="test-001",
            sequence_number=0,
            from_status="pending",
            to_status="running",
            trigger="start",
            actor="tool_node",
            actor_category="tool",
            timestamp=time.time(),
            is_terminal_transition=False,
        )
        assert tr.actor_category == "tool"
        assert tr.is_terminal_transition is False

    def test_constants_defined(self):
        assert "tool_node" in ACTOR_CATEGORY_MAP
        assert ACTOR_CATEGORY_MAP["tool_node"] == "tool"
        assert ExecutionStatus.COMPLETED in STATUS_TO_CONSEQUENCE
        assert STATUS_TO_CONSEQUENCE[ExecutionStatus.COMPLETED] == "SUCCESS"


# ==========================================
# Test: ExecutionObserver.snapshot()
# ==========================================

class TestExecutionObserverSnapshot:
    """Test snapshot projection from ExecutionContract."""

    def setup_method(self):
        self.observer = ExecutionObserver()

    def test_snapshot_pending_contract(self):
        c = _make_contract()
        snap = self.observer.snapshot(c)
        assert snap.current_status == "pending"
        assert snap.is_terminal is False
        assert snap.is_stable is False
        assert snap.is_resumable is False
        assert snap.has_side_effects is False
        assert snap.transition_count == 0
        assert snap.last_actor is None
        assert snap.last_trigger is None

    def test_snapshot_waiting_contract(self):
        c = _make_waiting_contract()
        snap = self.observer.snapshot(c)
        assert snap.current_status == "waiting"
        assert snap.is_terminal is False
        assert snap.is_stable is True
        assert snap.is_resumable is True
        assert snap.last_trigger == "suspend"
        assert snap.last_actor == "ecs_node"
        assert snap.duration_in_state_ms > 0

    def test_snapshot_completed_contract(self):
        c = _make_completed_tool_contract()
        snap = self.observer.snapshot(c)
        assert snap.current_status == "completed"
        assert snap.is_terminal is True
        assert snap.is_stable is True
        assert snap.is_resumable is False
        assert snap.result == "Email sent successfully"

    def test_snapshot_completed_irreversible_has_side_effects(self):
        c = _make_completed_tool_contract(irreversible=True)
        snap = self.observer.snapshot(c)
        assert snap.has_side_effects is True
        assert snap.irreversible is True

    def test_snapshot_failed_contract(self):
        c = _make_failed_contract()
        snap = self.observer.snapshot(c)
        assert snap.current_status == "failed"
        assert snap.is_terminal is True
        assert snap.error_message == "SMTP connection refused"

    def test_snapshot_action_summary_tool(self):
        c = _make_contract(service="calendar", method="create")
        snap = self.observer.snapshot(c)
        assert snap.action_summary == "calendar.create"

    def test_snapshot_action_summary_ecs(self):
        c = _make_waiting_contract()
        snap = self.observer.snapshot(c)
        assert "Confirm email send" in snap.action_summary


# ==========================================
# Test: ExecutionObserver.consequence_view()
# ==========================================

class TestExecutionObserverConsequenceView:
    """Test consequence view projection for ReasoningNode."""

    def setup_method(self):
        self.observer = ExecutionObserver()

    def test_consequence_success(self):
        c = _make_completed_tool_contract()
        cv = self.observer.consequence_view(c)
        assert cv.consequence_label == "SUCCESS"
        assert cv.is_still_pending is False
        assert cv.result == "Email sent successfully"

    def test_consequence_success_irreversible(self):
        c = _make_completed_tool_contract(irreversible=True)
        cv = self.observer.consequence_view(c)
        assert cv.consequence_label == "SUCCESS"
        assert cv.has_side_effects is True

    def test_consequence_success_was_suspended(self):
        c = _make_completed_tool_contract(was_suspended=True)
        cv = self.observer.consequence_view(c)
        assert cv.was_suspended is True
        assert cv.consequence_label == "SUCCESS"

    def test_consequence_success_irreversible_and_suspended(self):
        c = _make_completed_tool_contract(irreversible=True, was_suspended=True)
        cv = self.observer.consequence_view(c)
        assert cv.has_side_effects is True
        assert cv.was_suspended is True

    def test_consequence_failed(self):
        c = _make_failed_contract()
        cv = self.observer.consequence_view(c)
        assert cv.consequence_label == "FAILED"
        assert cv.was_suspended is False
        assert cv.is_still_pending is False
        assert cv.error_message == "SMTP connection refused"

    def test_consequence_waiting(self):
        c = _make_waiting_contract()
        cv = self.observer.consequence_view(c)
        assert cv.consequence_label == "WAITING"
        assert cv.is_still_pending is True
        # WAITING has not materialized side effects
        assert cv.has_side_effects is False

    def test_consequence_pending_contract(self):
        c = _make_contract()
        cv = self.observer.consequence_view(c)
        assert cv.consequence_label == "NOT_STARTED"
        assert cv.is_still_pending is True
        assert cv.total_duration_ms is None

    def test_consequence_duration_computed_for_terminal(self):
        c = _make_completed_tool_contract()
        cv = self.observer.consequence_view(c)
        assert cv.total_duration_ms is not None
        assert cv.total_duration_ms > 0

    def test_consequence_views_batch(self):
        contracts = [
            _make_completed_tool_contract(),
            _make_failed_contract(),
            _make_waiting_contract(),
        ]
        cvs = self.observer.consequence_views(contracts)
        assert len(cvs) == 3
        labels = [cv.consequence_label for cv in cvs]
        assert "SUCCESS" in labels
        assert "FAILED" in labels
        assert "WAITING" in labels


# ==========================================
# Test: ExecutionObserver.transition_records()
# ==========================================

class TestExecutionObserverTransitionRecords:
    """Test per-execution transition record projection."""

    def setup_method(self):
        self.observer = ExecutionObserver()

    def test_transition_records_completed(self):
        c = _make_completed_tool_contract()
        records = self.observer.transition_records(c)
        assert len(records) == 2
        assert records[0].from_status == "pending"
        assert records[0].to_status == "running"
        assert records[0].sequence_number == 0
        assert records[1].from_status == "running"
        assert records[1].to_status == "completed"
        assert records[1].is_terminal_transition is True

    def test_transition_records_with_suspension(self):
        c = _make_completed_tool_contract(was_suspended=True)
        records = self.observer.transition_records(c)
        assert len(records) == 4
        triggers = [r.trigger for r in records]
        assert triggers == ["start", "suspend", "resume", "succeed"]

    def test_transition_records_actor_category(self):
        c = _make_completed_tool_contract()
        records = self.observer.transition_records(c)
        assert records[0].actor == "tool_node"
        assert records[0].actor_category == "tool"

    def test_transition_records_empty_for_pending(self):
        c = _make_contract()
        records = self.observer.transition_records(c)
        assert len(records) == 0

    def test_transition_records_chronological(self):
        c = _make_completed_tool_contract(was_suspended=True)
        records = self.observer.transition_records(c)
        timestamps = [r.timestamp for r in records]
        assert timestamps == sorted(timestamps)


# ==========================================
# Test: ExecutionObserver.topology()
# ==========================================

class TestStateMachineTopology:
    """Test topology completeness and correctness."""

    def setup_method(self):
        self.topology = ExecutionObserver.topology()

    def test_all_7_nodes(self):
        assert len(self.topology.nodes) == 7
        statuses = {n.status for n in self.topology.nodes}
        assert statuses == {"pending", "running", "waiting", "completed", "failed", "rejected", "cancelled"}

    def test_initial_state(self):
        assert self.topology.initial_status == "pending"
        pending_node = next(n for n in self.topology.nodes if n.status == "pending")
        assert pending_node.is_initial is True
        assert pending_node.is_terminal is False

    def test_terminal_states(self):
        assert set(self.topology.terminal_statuses) == {"completed", "failed", "rejected", "cancelled"}
        for node in self.topology.nodes:
            if node.status in self.topology.terminal_statuses:
                assert node.is_terminal is True

    def test_terminal_nodes_no_outbound_edges(self):
        for terminal in self.topology.terminal_statuses:
            outbound = [e for e in self.topology.edges if e.from_status == terminal]
            assert len(outbound) == 0, f"Terminal {terminal} has outbound edges"

    def test_resumable_statuses(self):
        assert self.topology.resumable_statuses == ["waiting"]
        waiting_node = next(n for n in self.topology.nodes if n.status == "waiting")
        assert waiting_node.is_resumable is True

    def test_waiting_is_stable(self):
        waiting_node = next(n for n in self.topology.nodes if n.status == "waiting")
        assert waiting_node.is_stable is True

    def test_edges_match_valid_transitions(self):
        # Count edges should match total triggers in _VALID_TRANSITIONS
        total_triggers = sum(len(triggers) for triggers in _VALID_TRANSITIONS.values())
        assert len(self.topology.edges) == total_triggers

    def test_forbidden_transitions_exist(self):
        assert len(self.topology.forbidden_transitions) > 0
        # COMPLETED → RUNNING should be forbidden
        forbidden_pairs = {(f["from_status"], f["to_status"]) for f in self.topology.forbidden_transitions}
        assert ("completed", "running") in forbidden_pairs
        assert ("waiting", "completed") in forbidden_pairs

    def test_topology_serializable(self):
        data = self.topology.model_dump()
        assert "nodes" in data
        assert "edges" in data
        assert "forbidden_transitions" in data


# ==========================================
# Test: ExecutionObserver.timeline()
# ==========================================

class TestExecutionObserverTimeline:
    """Test session-level timeline projection."""

    def setup_method(self):
        self.observer = ExecutionObserver()

    def test_timeline_mixed_contracts(self):
        contracts = [
            _make_completed_tool_contract(),
            _make_waiting_contract(),
        ]
        tl = self.observer.timeline("session-001", contracts)
        assert tl.session_id == "session-001"
        assert tl.total_contracts == 2
        assert tl.terminal_contracts == 1
        assert tl.active_contracts == 1
        assert tl.has_suspended is True

    def test_timeline_all_terminal(self):
        contracts = [
            _make_completed_tool_contract(),
            _make_failed_contract(),
        ]
        tl = self.observer.timeline("session-002", contracts)
        assert tl.terminal_contracts == 2
        assert tl.active_contracts == 0
        assert tl.has_suspended is False

    def test_timeline_irreversible_completed(self):
        contracts = [_make_completed_tool_contract(irreversible=True)]
        tl = self.observer.timeline("session-003", contracts)
        assert tl.has_irreversible_completed is True

    def test_timeline_transitions_ordered(self):
        contracts = [
            _make_completed_tool_contract(was_suspended=True),
            _make_completed_tool_contract(),
        ]
        tl = self.observer.timeline("session-004", contracts)
        timestamps = [t.timestamp for t in tl.transitions]
        assert timestamps == sorted(timestamps)

    def test_timeline_empty(self):
        tl = self.observer.timeline("session-empty", [])
        assert tl.total_contracts == 0
        assert tl.started_at is None


# ==========================================
# Test: Action Summary Generation
# ==========================================

class TestActionSummaryGeneration:
    """Test human-readable action summary generation."""

    def test_tool_call_summary(self):
        c = _make_contract(service="email", method="send")
        summary = _generate_action_summary(c)
        assert summary == "email.send"

    def test_ecs_request_with_title(self):
        c = ExecutionContract(
            action_type="ecs_request",
            action_detail={"type": "form", "title": "Confirm action"},
        )
        summary = _generate_action_summary(c)
        assert summary == "Confirm action"

    def test_ecs_request_without_title(self):
        c = ExecutionContract(
            action_type="ecs_request",
            action_detail={"type": "confirmation"},
        )
        summary = _generate_action_summary(c)
        assert "confirmation" in summary

    def test_fallback_summary(self):
        c = ExecutionContract(
            action_type="unknown_type",
            action_detail={},
        )
        summary = _generate_action_summary(c)
        assert summary == "unknown_type"


# ==========================================
# Test: ReasoningNode Consequence-Based Prompt
# ==========================================

class TestReasoningNodeConsequencePrompt:
    """Test that ReasoningNode generates correct prompt text from ConsequenceView."""

    def test_success_prompt(self):
        cv = ExecutionConsequenceView(
            execution_id="test-001",
            action_type="tool_call",
            action_summary="email.send",
            consequence_label="SUCCESS",
            result="Email sent",
            has_side_effects=False,
            was_suspended=False,
            is_still_pending=False,
        )
        line = self._format_consequence(cv)
        assert "[SUCCESS]" in line
        assert "email.send" in line
        assert "Email sent" in line

    def test_success_irreversible_prompt(self):
        cv = ExecutionConsequenceView(
            execution_id="test-002",
            action_type="tool_call",
            action_summary="email.send",
            consequence_label="SUCCESS",
            result="Email sent",
            has_side_effects=True,
            was_suspended=False,
            is_still_pending=False,
        )
        line = self._format_consequence(cv)
        assert "IRREVERSIBLE" in line

    def test_success_suspended_prompt(self):
        cv = ExecutionConsequenceView(
            execution_id="test-003",
            action_type="tool_call",
            action_summary="email.send",
            consequence_label="SUCCESS",
            result="Email sent",
            has_side_effects=False,
            was_suspended=True,
            is_still_pending=False,
        )
        line = self._format_consequence(cv)
        assert "human-confirmed" in line

    def test_failed_prompt(self):
        cv = ExecutionConsequenceView(
            execution_id="test-004",
            action_type="tool_call",
            action_summary="email.send",
            consequence_label="FAILED",
            error_message="Connection refused",
            has_side_effects=False,
            was_suspended=False,
            is_still_pending=False,
        )
        line = self._format_consequence(cv)
        assert "[FAILED]" in line
        assert "Connection refused" in line

    def test_rejected_prompt(self):
        cv = ExecutionConsequenceView(
            execution_id="test-005",
            action_type="tool_call",
            action_summary="email.send",
            consequence_label="REJECTED",
            error_message="Permission denied",
            has_side_effects=False,
            was_suspended=False,
            is_still_pending=False,
        )
        line = self._format_consequence(cv)
        assert "[REJECTED]" in line

    def test_ecs_request_filtered_out(self):
        cv = ExecutionConsequenceView(
            execution_id="test-006",
            action_type="ecs_request",
            action_summary="Confirm",
            consequence_label="SUCCESS",
            has_side_effects=False,
            was_suspended=True,
            is_still_pending=False,
        )
        line = self._format_consequence(cv)
        assert line == ""  # ecs_request should be filtered out

    def _format_consequence(self, cv: ExecutionConsequenceView) -> str:
        """Reproduce the formatting logic from ReasoningNode."""
        if cv.action_type != "tool_call":
            return ""
        label = cv.consequence_label
        side_effect_tag = " IRREVERSIBLE" if cv.has_side_effects else ""
        suspended_tag = " (human-confirmed)" if cv.was_suspended else ""
        if label == "SUCCESS":
            return f"[{label}{side_effect_tag}{suspended_tag}] {cv.action_summary}: {cv.result}"
        elif label in ("FAILED", "REJECTED", "CANCELLED"):
            return f"[{label}] {cv.action_summary}: {cv.error_message}"
        return ""


# ==========================================
# v2 Tests: API Endpoints
# ==========================================

class TestAPIEndpointHelpers:
    """Test checkpoint-based data retrieval helpers used by API endpoints."""

    def setup_method(self):
        """Create an in-memory SQLite database with graph_checkpoints table."""
        import sqlite3
        self._conn = sqlite3.connect(":memory:")
        self._conn.execute(
            "CREATE TABLE graph_checkpoints (session_id TEXT PRIMARY KEY, state_json TEXT, updated_at TIMESTAMP)"
        )
        self._conn.commit()

    def teardown_method(self):
        self._conn.close()

    def _insert_checkpoint(self, session_id, state_data):
        """Insert a checkpoint for testing."""
        self._conn.execute(
            "INSERT INTO graph_checkpoints (session_id, state_json, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (session_id, json.dumps(state_data)),
        )
        self._conn.commit()

    def _load_contracts(self, session_id):
        """Simulate _load_contracts_from_checkpoint logic."""
        cursor = self._conn.execute(
            "SELECT state_json FROM graph_checkpoints WHERE session_id = ?",
            (session_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        state_data = json.loads(row[0])
        contracts = []
        for ce in state_data.get("completed_executions", []):
            contracts.append(ExecutionContract.model_validate(ce))
        for pe in state_data.get("pending_executions", []):
            contracts.append(ExecutionContract.model_validate(pe))
        return contracts

    def _find_contract(self, execution_id):
        """Simulate _find_contract_by_execution_id logic."""
        cursor = self._conn.execute("SELECT state_json FROM graph_checkpoints")
        for row in cursor.fetchall():
            state_data = json.loads(row[0])
            for ce in state_data.get("completed_executions", []):
                if ce.get("execution_id") == execution_id:
                    return ExecutionContract.model_validate(ce)
            for pe in state_data.get("pending_executions", []):
                if pe.get("execution_id") == execution_id:
                    return ExecutionContract.model_validate(pe)
        return None

    def test_load_contracts_success(self):
        """9.4: Checkpoint-based retrieval returns contracts."""
        c = _make_completed_tool_contract()
        self._insert_checkpoint("sess-001", {
            "completed_executions": [c.model_dump()],
            "pending_executions": [],
        })
        contracts = self._load_contracts("sess-001")
        assert contracts is not None
        assert len(contracts) == 1
        assert contracts[0].execution_id == c.execution_id

    def test_load_contracts_not_found(self):
        """9.4: Non-existent session returns None."""
        result = self._load_contracts("nonexistent")
        assert result is None

    def test_load_contracts_mixed(self):
        """9.4: Returns both completed and pending contracts."""
        c1 = _make_completed_tool_contract()
        c2 = _make_contract()  # pending
        self._insert_checkpoint("sess-002", {
            "completed_executions": [c1.model_dump()],
            "pending_executions": [c2.model_dump()],
        })
        contracts = self._load_contracts("sess-002")
        assert len(contracts) == 2

    def test_find_contract_by_execution_id_success(self):
        """9.4: Find a specific contract by execution_id across checkpoints."""
        c = _make_completed_tool_contract()
        self._insert_checkpoint("sess-003", {
            "completed_executions": [c.model_dump()],
            "pending_executions": [],
        })
        found = self._find_contract(c.execution_id)
        assert found is not None
        assert found.execution_id == c.execution_id

    def test_find_contract_by_execution_id_not_found(self):
        """9.4: Non-existent execution_id returns None."""
        found = self._find_contract("nonexistent-id")
        assert found is None


class TestAPIEndpointTimeline:
    """Test timeline endpoint behavior (integration logic)."""

    def setup_method(self):
        self.observer = ExecutionObserver()

    def test_timeline_returns_correct_structure(self):
        """9.1: Timeline endpoint returns ExecutionTimeline JSON structure."""
        contracts = [
            _make_completed_tool_contract(),
            _make_waiting_contract(),
        ]
        tl = self.observer.timeline("sess-api-001", contracts)
        data = tl.model_dump()
        assert data["session_id"] == "sess-api-001"
        assert data["total_contracts"] == 2
        assert "contracts" in data
        assert "transitions" in data

    def test_timeline_empty_session(self):
        """9.1: Timeline with no contracts returns empty but valid structure."""
        tl = self.observer.timeline("empty-sess", [])
        data = tl.model_dump()
        assert data["total_contracts"] == 0
        assert data["contracts"] == []
        assert data["transitions"] == []


class TestAPIEndpointSnapshot:
    """Test snapshot endpoint behavior (integration logic)."""

    def setup_method(self):
        self.observer = ExecutionObserver()

    def test_snapshot_returns_correct_structure(self):
        """9.2: Snapshot endpoint returns ExecutionSnapshot JSON structure."""
        c = _make_completed_tool_contract()
        snap = self.observer.snapshot(c)
        data = snap.model_dump()
        assert "execution_id" in data
        assert "current_status" in data
        assert "is_terminal" in data
        assert "action_summary" in data
        assert data["current_status"] == "completed"

    def test_snapshot_waiting_contract_structure(self):
        """9.2: Snapshot of WAITING contract shows resumable."""
        c = _make_waiting_contract()
        snap = self.observer.snapshot(c)
        data = snap.model_dump()
        assert data["is_resumable"] is True
        assert data["is_terminal"] is False


class TestAPIEndpointTopology:
    """Test topology endpoint behavior (integration logic)."""

    def test_topology_returns_correct_structure(self):
        """9.3: Topology endpoint returns StateMachineTopology JSON structure."""
        topo = ExecutionObserver.topology()
        data = topo.model_dump()
        assert "nodes" in data
        assert "edges" in data
        assert "terminal_statuses" in data
        assert "initial_status" in data
        assert data["initial_status"] == "pending"

    def test_topology_is_static_and_cacheable(self):
        """9.3: Two calls return structurally identical results."""
        t1 = ExecutionObserver.topology().model_dump()
        t2 = ExecutionObserver.topology().model_dump()
        assert t1 == t2


# ==========================================
# v2 Tests: SSE Event Emission
# ==========================================

class TestSSEExecutionStatePayload:
    """Test execution_state SSE event payload structure and correctness."""

    def test_build_execution_state_event_completed(self):
        """10.4: Verify execution_state payload for a completed contract."""
        from graph_runner import GraphRunner
        runner = GraphRunner.__new__(GraphRunner)  # Skip __init__

        c = _make_completed_tool_contract(irreversible=True)
        last_t = c.transitions[-1]
        event = runner._build_execution_state_event(
            c, last_t["from"], last_t["to"], last_t["trigger"]
        )

        assert event["execution_id"] == c.execution_id
        assert event["from_status"] == "running"
        assert event["to_status"] == "completed"
        assert event["trigger"] == "succeed"
        assert event["is_terminal"] is True
        assert event["is_resumable"] is False
        assert event["has_side_effects"] is True
        assert event["action_summary"] == "email.send"
        assert "actor_category" in event
        assert "timestamp" in event

    def test_build_execution_state_event_waiting(self):
        """10.4: Verify execution_state payload for a waiting (suspended) contract."""
        from graph_runner import GraphRunner
        runner = GraphRunner.__new__(GraphRunner)

        c = _make_waiting_contract()
        last_t = c.transitions[-1]
        event = runner._build_execution_state_event(
            c, last_t["from"], last_t["to"], last_t["trigger"]
        )

        assert event["to_status"] == "waiting"
        assert event["is_terminal"] is False
        assert event["is_resumable"] is True
        assert event["has_side_effects"] is False

    def test_build_execution_state_event_failed(self):
        """10.4: Verify execution_state payload for a failed contract."""
        from graph_runner import GraphRunner
        runner = GraphRunner.__new__(GraphRunner)

        c = _make_failed_contract()
        last_t = c.transitions[-1]
        event = runner._build_execution_state_event(
            c, last_t["from"], last_t["to"], last_t["trigger"]
        )

        assert event["to_status"] == "failed"
        assert event["is_terminal"] is True
        assert event["is_resumable"] is False
        assert event["has_side_effects"] is False

    def test_detect_new_transitions(self):
        """10.4: Detect new transitions from contract state changes."""
        from graph_runner import GraphRunner
        runner = GraphRunner.__new__(GraphRunner)

        c = _make_completed_tool_contract()

        # Initially no previous state
        prev = {}
        new = runner._detect_new_transitions(prev, [c.model_dump()], [])
        assert len(new) == 2  # start + succeed transitions
        assert new[0][2] == "running"  # to_status
        assert new[1][2] == "completed"  # to_status

    def test_detect_new_transitions_incremental(self):
        """10.4: Only detect transitions newer than previously seen."""
        from graph_runner import GraphRunner
        runner = GraphRunner.__new__(GraphRunner)

        c = _make_completed_tool_contract()
        prev = {c.execution_id: 1}  # Already saw 1 transition (start)
        new = runner._detect_new_transitions(prev, [c.model_dump()], [])
        assert len(new) == 1  # Only the succeed transition
        assert new[0][2] == "completed"

    def test_detect_new_transitions_no_change(self):
        """10.4: No new transitions when count hasn't changed."""
        from graph_runner import GraphRunner
        runner = GraphRunner.__new__(GraphRunner)

        c = _make_completed_tool_contract()
        prev = {c.execution_id: 2}  # Saw all 2 transitions
        new = runner._detect_new_transitions(prev, [c.model_dump()], [])
        assert len(new) == 0


class TestSSEExistingEventsUnaffected:
    """10.3: Verify existing SSE event formats are not modified."""

    def test_format_sse_text(self):
        """Existing text event format is preserved."""
        from graph_runner import GraphRunner
        runner = GraphRunner.__new__(GraphRunner)
        result = runner._format_sse("text", {"type": "text", "payload": {"content": "hello"}})
        assert result.startswith("event: text\n")
        assert '"type": "text"' in result
        assert result.endswith("\n\n")

    def test_format_sse_emotion(self):
        """Existing emotion event format is preserved."""
        from graph_runner import GraphRunner
        runner = GraphRunner.__new__(GraphRunner)
        result = runner._format_sse("emotion", {"type": "emotion", "payload": {"primary": "happy"}})
        assert result.startswith("event: emotion\n")
        assert '"primary": "happy"' in result

    def test_format_sse_done(self):
        """Existing done event format is preserved."""
        from graph_runner import GraphRunner
        runner = GraphRunner.__new__(GraphRunner)
        result = runner._format_sse("done", {"type": "done"})
        assert result.startswith("event: done\n")

    def test_format_sse_execution_state(self):
        """New execution_state event uses same SSE format."""
        from graph_runner import GraphRunner
        runner = GraphRunner.__new__(GraphRunner)
        payload = {
            "execution_id": "test-001",
            "action_summary": "email.send",
            "from_status": "running",
            "to_status": "completed",
            "trigger": "succeed",
            "actor_category": "tool",
            "is_terminal": True,
            "is_resumable": False,
            "has_side_effects": False,
            "timestamp": 1707350400.123,
        }
        result = runner._format_sse("execution_state", payload)
        assert result.startswith("event: execution_state\n")
        assert '"execution_id": "test-001"' in result
        assert result.endswith("\n\n")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
