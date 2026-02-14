"""
ExecutionUITranslator — Semantic translation layer from Observer projections
to human-facing execution objects.

Translates ExecutionSnapshot, ExecutionConsequenceView, and ExecutionTimeline
into dicts with human-readable Chinese keys and values. No engineering
vocabulary (snapshot, contract, topology, transition, observer) appears
in the output.
"""

import logging
from core.state import (
    ExecutionSnapshot,
    ExecutionConsequenceView,
    ExecutionTimeline,
    STATUS_TO_HUMAN_LABEL,
    ExecutionStatus,
)
from observation import _humanize_action_summary, _humanize_consequence

logger = logging.getLogger(f"workflow.{__name__}")


# Engineering terms that MUST NOT appear in human-facing output
_FORBIDDEN_KEYS = {
    "snapshot", "contract", "topology", "transition", "observer",
    "projection", "state_machine", "node", "actor_category",
    "execution_id", "current_status", "consequence_label",
    "is_still_pending", "action_type", "idempotency_key",
    "entered_at", "duration_in_state_ms", "transition_count",
    "last_actor", "last_trigger", "is_stable",
}


def _status_to_human(status_str: str) -> str:
    """Convert status string to human label."""
    for es in ExecutionStatus:
        if es.value == status_str:
            return STATUS_TO_HUMAN_LABEL.get(es, status_str)
    logger.warning(f"[UITranslator] Unknown status: {status_str!r}, returning as-is")
    return status_str


class ExecutionUITranslator:
    """Translates Observer projections into human-facing execution views."""

    def translate_snapshot(self, snapshot: ExecutionSnapshot) -> dict:
        """Translate ExecutionSnapshot → 执行舞台 view data."""
        logger.info(
            f"[UITranslator] translate_snapshot: "
            f"status={snapshot.current_status} action={snapshot.action_summary!r} "
            f"terminal={snapshot.is_terminal} resumable={snapshot.is_resumable}"
        )
        result = {
            "行动": _humanize_action_summary(snapshot.action_summary),
            "状态": _status_to_human(snapshot.current_status),
            "是否需要关注": snapshot.is_resumable,
            "是否已结束": snapshot.is_terminal,
            "是否不可逆": snapshot.has_side_effects,
            "结果": snapshot.result,
            "错误": snapshot.error_message,
        }
        if snapshot.error_message:
            logger.warning(f"[UITranslator] snapshot error: {snapshot.error_message!r}")
        return result

    def translate_consequence(self, view: ExecutionConsequenceView) -> dict:
        """Translate ExecutionConsequenceView → 行动解释 view data."""
        logger.info(
            f"[UITranslator] translate_consequence: "
            f"action={view.action_summary!r} consequence={view.consequence_label!r} "
            f"side_effects={view.has_side_effects} pending={view.is_still_pending} "
            f"duration={view.total_duration_ms}ms"
        )
        result = {
            "行动": _humanize_action_summary(view.action_summary),
            "后果": _humanize_consequence(view.consequence_label, view.has_side_effects),
            "是否不可逆": view.has_side_effects,
            "是否经过确认": view.was_suspended,
            "是否仍在进行": view.is_still_pending,
            "结果": view.result,
            "错误": view.error_message,
            "耗时毫秒": view.total_duration_ms,
        }
        if view.error_message:
            logger.warning(f"[UITranslator] consequence error: {view.error_message!r}")
        return result

    def translate_timeline(self, timeline: ExecutionTimeline) -> dict:
        """Translate ExecutionTimeline → 执行历史 view data."""
        logger.info(
            f"[UITranslator] translate_timeline: "
            f"total={timeline.total_contracts} terminal={timeline.terminal_contracts} "
            f"active={timeline.active_contracts}"
        )
        actions = []
        for i, snap in enumerate(timeline.contracts):
            actions.append({
                "行动": _humanize_action_summary(snap.action_summary),
                "状态": _status_to_human(snap.current_status),
                "是否已结束": snap.is_terminal,
                "是否不可逆": snap.has_side_effects,
                "结果": snap.result,
                "错误": snap.error_message,
            })

        return {
            "行动列表": actions,
            "总数": timeline.total_contracts,
            "已结束": timeline.terminal_contracts,
            "进行中": timeline.active_contracts,
            "含等待": timeline.has_suspended,
            "含不可逆操作": timeline.has_irreversible_completed,
        }
