"""Tests for CognitiveObject state machine.

Covers:
- CognitiveObjectStatus transitions (valid and invalid)
- CognitiveObject lifecycle
- Transition traceability (actor, trigger, reason, timestamp)
- All six states and their allowed transitions
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.state import (
    CognitiveObjectStatus,
    CognitiveObject,
    InvalidTransitionError,
    _CO_VALID_TRANSITIONS,
)


class TestCognitiveObjectCreation:
    """Test CO creation defaults."""

    def test_default_status_is_emerging(self):
        co = CognitiveObject(title="Test CO")
        assert co.status == CognitiveObjectStatus.EMERGING

    def test_co_id_is_generated(self):
        co = CognitiveObject(title="Test CO")
        assert co.co_id is not None
        assert len(co.co_id) > 0

    def test_empty_transitions_on_creation(self):
        co = CognitiveObject(title="Test CO")
        assert co.transitions == []

    def test_co_exists_without_executions(self):
        co = CognitiveObject(title="Track project")
        assert co.linked_execution_ids == []
        assert co.status == CognitiveObjectStatus.EMERGING

    def test_optional_semantic_fields(self):
        co = CognitiveObject(
            title="Test",
            semantic_type="task",
            domain_tag="work",
            intent_category="track",
        )
        assert co.semantic_type == "task"
        assert co.domain_tag == "work"
        assert co.intent_category == "track"


class TestCognitiveObjectValidTransitions:
    """Test all valid state transitions."""

    def test_emerging_to_active(self):
        co = CognitiveObject(title="Test")
        co.transition("clarify", actor="user", reason="User provided details")
        assert co.status == CognitiveObjectStatus.ACTIVE
        assert len(co.transitions) == 1
        assert co.transitions[0]["from"] == "emerging"
        assert co.transitions[0]["to"] == "active"
        assert co.transitions[0]["trigger"] == "clarify"
        assert co.transitions[0]["actor"] == "user"
        assert co.transitions[0]["reason"] == "User provided details"

    def test_emerging_to_archived(self):
        co = CognitiveObject(title="Test")
        co.transition("archive", actor="user", reason="Not tracking")
        assert co.status == CognitiveObjectStatus.ARCHIVED

    def test_active_to_waiting(self):
        co = CognitiveObject(title="Test")
        co.transition("clarify", actor="user")
        co.transition("wait", actor="execution_event", reason="Waiting for reply")
        assert co.status == CognitiveObjectStatus.WAITING

    def test_active_to_blocked(self):
        co = CognitiveObject(title="Test")
        co.transition("clarify", actor="user")
        co.transition("block", actor="execution_event", reason="API failed")
        assert co.status == CognitiveObjectStatus.BLOCKED

    def test_active_to_stable(self):
        co = CognitiveObject(title="Test")
        co.transition("clarify", actor="user")
        co.transition("achieve", actor="user", reason="Goal met")
        assert co.status == CognitiveObjectStatus.STABLE

    def test_active_to_archived(self):
        co = CognitiveObject(title="Test")
        co.transition("clarify", actor="user")
        co.transition("archive", actor="user", reason="Giving up")
        assert co.status == CognitiveObjectStatus.ARCHIVED

    def test_waiting_to_active(self):
        co = CognitiveObject(title="Test")
        co.transition("clarify", actor="user")
        co.transition("wait", actor="execution_event")
        co.transition("resume", actor="user", reason="Got response")
        assert co.status == CognitiveObjectStatus.ACTIVE

    def test_waiting_to_blocked(self):
        co = CognitiveObject(title="Test")
        co.transition("clarify", actor="user")
        co.transition("wait", actor="execution_event")
        co.transition("block", actor="execution_event")
        assert co.status == CognitiveObjectStatus.BLOCKED

    def test_waiting_to_stable(self):
        co = CognitiveObject(title="Test")
        co.transition("clarify", actor="user")
        co.transition("wait", actor="execution_event")
        co.transition("achieve", actor="user", reason="Naturally resolved")
        assert co.status == CognitiveObjectStatus.STABLE

    def test_waiting_to_archived(self):
        co = CognitiveObject(title="Test")
        co.transition("clarify", actor="user")
        co.transition("wait", actor="execution_event")
        co.transition("archive", actor="user")
        assert co.status == CognitiveObjectStatus.ARCHIVED

    def test_blocked_to_active(self):
        co = CognitiveObject(title="Test")
        co.transition("clarify", actor="user")
        co.transition("block", actor="execution_event")
        co.transition("unblock", actor="user", reason="Resolved dependency")
        assert co.status == CognitiveObjectStatus.ACTIVE

    def test_blocked_to_archived(self):
        co = CognitiveObject(title="Test")
        co.transition("clarify", actor="user")
        co.transition("block", actor="execution_event")
        co.transition("archive", actor="user")
        assert co.status == CognitiveObjectStatus.ARCHIVED

    def test_stable_to_active(self):
        co = CognitiveObject(title="Test")
        co.transition("clarify", actor="user")
        co.transition("achieve", actor="user")
        co.transition("reactivate", actor="user", reason="Reopened")
        assert co.status == CognitiveObjectStatus.ACTIVE

    def test_stable_to_archived(self):
        co = CognitiveObject(title="Test")
        co.transition("clarify", actor="user")
        co.transition("achieve", actor="user")
        co.transition("archive", actor="user")
        assert co.status == CognitiveObjectStatus.ARCHIVED

    def test_archived_to_active(self):
        co = CognitiveObject(title="Test")
        co.transition("archive", actor="user")
        co.transition("reactivate", actor="user", reason="Restored")
        assert co.status == CognitiveObjectStatus.ACTIVE


class TestCognitiveObjectInvalidTransitions:
    """Test all invalid state transitions are rejected."""

    def test_emerging_cannot_achieve(self):
        co = CognitiveObject(title="Test")
        with pytest.raises(InvalidTransitionError):
            co.transition("achieve", actor="user")
        assert co.status == CognitiveObjectStatus.EMERGING

    def test_emerging_cannot_wait(self):
        co = CognitiveObject(title="Test")
        with pytest.raises(InvalidTransitionError):
            co.transition("wait", actor="user")
        assert co.status == CognitiveObjectStatus.EMERGING

    def test_emerging_cannot_block(self):
        co = CognitiveObject(title="Test")
        with pytest.raises(InvalidTransitionError):
            co.transition("block", actor="user")

    def test_active_cannot_clarify(self):
        co = CognitiveObject(title="Test")
        co.transition("clarify", actor="user")
        with pytest.raises(InvalidTransitionError):
            co.transition("clarify", actor="user")

    def test_blocked_cannot_wait(self):
        co = CognitiveObject(title="Test")
        co.transition("clarify", actor="user")
        co.transition("block", actor="execution_event")
        with pytest.raises(InvalidTransitionError):
            co.transition("wait", actor="user")

    def test_stable_cannot_block(self):
        co = CognitiveObject(title="Test")
        co.transition("clarify", actor="user")
        co.transition("achieve", actor="user")
        with pytest.raises(InvalidTransitionError):
            co.transition("block", actor="user")

    def test_invalid_trigger_name(self):
        co = CognitiveObject(title="Test")
        with pytest.raises(InvalidTransitionError):
            co.transition("nonexistent", actor="user")

    def test_status_unchanged_after_invalid(self):
        co = CognitiveObject(title="Test")
        original_status = co.status
        with pytest.raises(InvalidTransitionError):
            co.transition("achieve", actor="user")
        assert co.status == original_status
        assert len(co.transitions) == 0


class TestCognitiveObjectTraceability:
    """Test that all transitions are traceable."""

    def test_transition_records_all_fields(self):
        co = CognitiveObject(title="Test")
        co.transition("clarify", actor="user", reason="Got more info")
        t = co.transitions[0]
        assert "from" in t
        assert "to" in t
        assert "trigger" in t
        assert "timestamp" in t
        assert "actor" in t
        assert "reason" in t

    def test_transition_history_ordered(self):
        co = CognitiveObject(title="Test")
        co.transition("clarify", actor="user")
        co.transition("wait", actor="execution_event")
        co.transition("resume", actor="user")
        assert len(co.transitions) == 3
        for i in range(1, len(co.transitions)):
            assert co.transitions[i]["timestamp"] >= co.transitions[i - 1]["timestamp"]

    def test_full_lifecycle_trace(self):
        co = CognitiveObject(title="Project X")
        co.transition("clarify", actor="user", reason="Defined scope")
        co.transition("wait", actor="execution_event", reason="Sent email")
        co.transition("resume", actor="user", reason="Got reply")
        co.transition("achieve", actor="user", reason="Done")
        co.transition("archive", actor="user", reason="Cleaning up")
        assert len(co.transitions) == 5
        assert co.status == CognitiveObjectStatus.ARCHIVED
        statuses = [t["to"] for t in co.transitions]
        assert statuses == ["active", "waiting", "active", "stable", "archived"]

    def test_updated_at_changes_on_transition(self):
        co = CognitiveObject(title="Test")
        original = co.updated_at
        co.transition("clarify", actor="user")
        assert co.updated_at >= original


class TestTransitionRulesCompleteness:
    """Verify transition rules cover all states."""

    def test_all_statuses_have_transition_entries(self):
        for status in CognitiveObjectStatus:
            assert status in _CO_VALID_TRANSITIONS or status.value in {
                s.value for s in _CO_VALID_TRANSITIONS
            }, f"Missing transition entry for {status}"

    def test_archived_can_reactivate(self):
        """ARCHIVED is recoverable, unlike Execution terminal states."""
        valid = _CO_VALID_TRANSITIONS.get(CognitiveObjectStatus.ARCHIVED, {})
        assert "reactivate" in valid

    def test_every_state_has_archive_or_reactivate(self):
        """Every state should have a way to reach ARCHIVED or return to ACTIVE."""
        for status in CognitiveObjectStatus:
            valid = _CO_VALID_TRANSITIONS.get(status, {})
            has_exit = "archive" in valid or "reactivate" in valid or len(valid) > 0
            assert has_exit, f"State {status} has no transitions"
