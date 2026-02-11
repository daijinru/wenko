"""Tests for the UI semantic translation layer (ExecutionUITranslator).

Verifies:
- snapshot → 执行舞台 data
- consequence_view → 行动解释 data
- timeline → 执行历史 data
- No engineering vocabulary in output keys
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.state import (
    ExecutionSnapshot,
    ExecutionConsequenceView,
    ExecutionTimeline,
    TransitionRecord,
)
from ui_translation import ExecutionUITranslator, _FORBIDDEN_KEYS


translator = ExecutionUITranslator()


def _all_keys(d: dict) -> set:
    """Recursively collect all keys from a dict (including nested dicts/lists)."""
    keys = set()
    for k, v in d.items():
        keys.add(k)
        if isinstance(v, dict):
            keys.update(_all_keys(v))
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    keys.update(_all_keys(item))
    return keys


class TestTranslateSnapshot:
    """translate_snapshot should produce human-readable dict from ExecutionSnapshot."""

    def _make_snapshot(self, **overrides):
        defaults = dict(
            execution_id="test-001",
            action_type="tool_call",
            action_summary="email.send",
            current_status="running",
            entered_at=time.time(),
            duration_in_state_ms=150.0,
            is_terminal=False,
            is_stable=False,
            is_resumable=False,
            has_side_effects=False,
            irreversible=False,
            transition_count=1,
        )
        defaults.update(overrides)
        return ExecutionSnapshot(**defaults)

    def test_running_snapshot(self):
        snap = self._make_snapshot()
        result = translator.translate_snapshot(snap)
        assert result["状态"] == "进行中"
        assert result["行动"] == "发送email"
        assert result["是否需要关注"] is False

    def test_waiting_snapshot(self):
        snap = self._make_snapshot(current_status="waiting", is_resumable=True)
        result = translator.translate_snapshot(snap)
        assert result["状态"] == "需要关注"
        assert result["是否需要关注"] is True

    def test_completed_with_side_effects(self):
        snap = self._make_snapshot(
            current_status="completed", is_terminal=True, has_side_effects=True
        )
        result = translator.translate_snapshot(snap)
        assert result["状态"] == "已完成"
        assert result["是否不可逆"] is True

    def test_no_forbidden_keys(self):
        snap = self._make_snapshot()
        result = translator.translate_snapshot(snap)
        found = _all_keys(result) & _FORBIDDEN_KEYS
        assert not found, f"Forbidden keys in output: {found}"


class TestTranslateConsequence:
    """translate_consequence should produce human-readable dict from ConsequenceView."""

    def _make_consequence(self, **overrides):
        defaults = dict(
            execution_id="test-001",
            action_type="tool_call",
            action_summary="email.send",
            consequence_label="SUCCESS",
            has_side_effects=False,
            was_suspended=False,
            is_still_pending=False,
        )
        defaults.update(overrides)
        return ExecutionConsequenceView(**defaults)

    def test_success(self):
        cv = self._make_consequence()
        result = translator.translate_consequence(cv)
        assert result["后果"] == "已完成"
        assert result["是否不可逆"] is False

    def test_success_irreversible(self):
        cv = self._make_consequence(has_side_effects=True)
        result = translator.translate_consequence(cv)
        assert result["后果"] == "已完成（不可撤销）"
        assert result["是否不可逆"] is True

    def test_failed(self):
        cv = self._make_consequence(
            consequence_label="FAILED", error_message="Connection refused"
        )
        result = translator.translate_consequence(cv)
        assert result["后果"] == "出了问题"
        assert result["错误"] == "Connection refused"

    def test_suspended(self):
        cv = self._make_consequence(was_suspended=True)
        result = translator.translate_consequence(cv)
        assert result["是否经过确认"] is True

    def test_no_forbidden_keys(self):
        cv = self._make_consequence()
        result = translator.translate_consequence(cv)
        found = _all_keys(result) & _FORBIDDEN_KEYS
        assert not found, f"Forbidden keys in output: {found}"


class TestTranslateTimeline:
    """translate_timeline should produce human-readable dict from ExecutionTimeline."""

    def _make_timeline(self, snapshots=None):
        if snapshots is None:
            now = time.time()
            snapshots = [
                ExecutionSnapshot(
                    execution_id="test-001",
                    action_type="tool_call",
                    action_summary="email.send",
                    current_status="completed",
                    entered_at=now,
                    duration_in_state_ms=100.0,
                    is_terminal=True,
                    is_stable=True,
                    is_resumable=False,
                    has_side_effects=True,
                    irreversible=True,
                    transition_count=2,
                    result="Sent",
                ),
                ExecutionSnapshot(
                    execution_id="test-002",
                    action_type="tool_call",
                    action_summary="data.read",
                    current_status="running",
                    entered_at=now,
                    duration_in_state_ms=50.0,
                    is_terminal=False,
                    is_stable=False,
                    is_resumable=False,
                    has_side_effects=False,
                    irreversible=False,
                    transition_count=1,
                ),
            ]
        return ExecutionTimeline(
            session_id="session-001",
            contracts=snapshots,
            transitions=[],
            total_contracts=len(snapshots),
            terminal_contracts=sum(1 for s in snapshots if s.is_terminal),
            active_contracts=sum(1 for s in snapshots if not s.is_terminal),
            has_suspended=False,
            has_irreversible_completed=any(s.has_side_effects for s in snapshots),
        )

    def test_timeline_structure(self):
        tl = self._make_timeline()
        result = translator.translate_timeline(tl)
        assert result["总数"] == 2
        assert result["已结束"] == 1
        assert result["进行中"] == 1
        assert result["含不可逆操作"] is True
        assert len(result["行动列表"]) == 2

    def test_action_items(self):
        tl = self._make_timeline()
        result = translator.translate_timeline(tl)
        first = result["行动列表"][0]
        assert first["行动"] == "发送email"
        assert first["状态"] == "已完成"

    def test_no_forbidden_keys(self):
        tl = self._make_timeline()
        result = translator.translate_timeline(tl)
        found = _all_keys(result) & _FORBIDDEN_KEYS
        assert not found, f"Forbidden keys in output: {found}"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
