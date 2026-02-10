"""
ExecutionObserver — Read-only projection service for execution state observation.

Does not hold state. Does not modify ExecutionContract.
Projects ExecutionContract data into observation views (Snapshot, ConsequenceView,
TransitionRecord, Timeline, Topology).
"""

import time
from typing import List, Optional

from core.state import (
    ExecutionContract,
    ExecutionStatus,
    ExecutionStep,
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


def _generate_action_summary(contract: ExecutionContract) -> str:
    """Generate a human-readable action summary from action_detail."""
    detail = contract.action_detail
    service = detail.get("service", "")
    method = detail.get("method", "")
    title = detail.get("title", "")

    if service and method:
        return f"{service}.{method}"
    if title:
        return title
    if contract.action_type == "ecs_request":
        ecs_type = detail.get("type", "")
        return f"ecs:{ecs_type}" if ecs_type else "ecs_request"
    return contract.action_type


class ExecutionObserver:
    """
    Read-only service: projects ExecutionContract and execution_trace
    into observation views. Does not hold state. Does not modify Contract.
    """

    def snapshot(self, contract: ExecutionContract) -> ExecutionSnapshot:
        """Project a single contract into an observation snapshot."""
        now = time.time()

        # Determine entered_at: timestamp of the last transition (when current state was entered)
        if contract.transitions:
            last_t = contract.transitions[-1]
            entered_at = last_t["timestamp"]
            last_actor = last_t.get("actor")
            last_trigger = last_t.get("trigger")
        else:
            entered_at = contract.created_at
            last_actor = None
            last_trigger = None

        duration_in_state_ms = (now - entered_at) * 1000

        is_terminal = contract.status in TERMINAL_STATUSES
        is_waiting = contract.status == ExecutionStatus.WAITING
        is_stable = is_terminal or is_waiting
        is_resumable = is_waiting
        # has_side_effects: irreversible AND has completed (side effects materialized)
        has_side_effects = contract.irreversible and contract.status == ExecutionStatus.COMPLETED

        return ExecutionSnapshot(
            execution_id=contract.execution_id,
            action_type=contract.action_type,
            action_summary=_generate_action_summary(contract),
            current_status=contract.status.value,
            entered_at=entered_at,
            duration_in_state_ms=duration_in_state_ms,
            is_terminal=is_terminal,
            is_stable=is_stable,
            is_resumable=is_resumable,
            has_side_effects=has_side_effects,
            irreversible=contract.irreversible,
            idempotency_key=contract.idempotency_key,
            timeout_seconds=contract.timeout_seconds,
            result=contract.result,
            error_message=contract.error_message,
            transition_count=len(contract.transitions),
            last_actor=last_actor,
            last_trigger=last_trigger,
        )

    def consequence_view(self, contract: ExecutionContract) -> ExecutionConsequenceView:
        """Project a single contract into a ReasoningNode consequence view."""
        consequence_label = STATUS_TO_CONSEQUENCE.get(contract.status, "UNKNOWN")
        was_suspended = any(t["to"] == "waiting" for t in contract.transitions)
        is_terminal = contract.status in TERMINAL_STATUSES
        is_still_pending = not is_terminal
        # has_side_effects: irreversible AND completed (effect materialized)
        has_side_effects = contract.irreversible and contract.status == ExecutionStatus.COMPLETED

        # Compute total duration if terminal
        total_duration_ms: Optional[float] = None
        if is_terminal and contract.transitions:
            last_timestamp = contract.transitions[-1]["timestamp"]
            total_duration_ms = (last_timestamp - contract.created_at) * 1000

        return ExecutionConsequenceView(
            execution_id=contract.execution_id,
            action_type=contract.action_type,
            action_summary=_generate_action_summary(contract),
            consequence_label=consequence_label,
            result=contract.result,
            error_message=contract.error_message,
            has_side_effects=has_side_effects,
            was_suspended=was_suspended,
            is_still_pending=is_still_pending,
            total_duration_ms=total_duration_ms,
        )

    def consequence_views(self, contracts: List[ExecutionContract]) -> List[ExecutionConsequenceView]:
        """Batch projection for ReasoningNode consumption."""
        return [self.consequence_view(c) for c in contracts]

    def transition_records(self, contract: ExecutionContract) -> List[TransitionRecord]:
        """Project a single contract's transitions into TransitionRecord list."""
        records = []
        for i, t in enumerate(contract.transitions):
            actor = t.get("actor", "unknown")
            actor_category = ACTOR_CATEGORY_MAP.get(actor, "system")
            to_status = t["to"]
            is_terminal_transition = to_status in {s.value for s in TERMINAL_STATUSES}

            records.append(TransitionRecord(
                execution_id=contract.execution_id,
                sequence_number=i,
                from_status=t["from"],
                to_status=to_status,
                trigger=t["trigger"],
                actor=actor,
                actor_category=actor_category,
                timestamp=t["timestamp"],
                is_terminal_transition=is_terminal_transition,
            ))
        return records

    @staticmethod
    def topology() -> StateMachineTopology:
        """Return the state machine topology (static constant)."""
        all_statuses = list(ExecutionStatus)
        terminal_values = {s.value for s in TERMINAL_STATUSES}

        nodes = []
        for status in all_statuses:
            nodes.append(StateNode(
                status=status.value,
                is_terminal=status in TERMINAL_STATUSES,
                is_initial=status == ExecutionStatus.PENDING,
                is_stable=(status in TERMINAL_STATUSES or status == ExecutionStatus.WAITING),
                is_resumable=status == ExecutionStatus.WAITING,
            ))

        edges = []
        for from_status, triggers in _VALID_TRANSITIONS.items():
            for trigger, to_status in triggers.items():
                from_val = from_status.value if isinstance(from_status, ExecutionStatus) else from_status
                to_val = to_status.value if isinstance(to_status, ExecutionStatus) else to_status
                edges.append(StateTransitionEdge(
                    from_status=from_val,
                    to_status=to_val,
                    trigger=trigger,
                ))

        # Compute forbidden transitions
        valid_pairs = {(e.from_status, e.to_status) for e in edges}
        forbidden = []
        for from_s in all_statuses:
            for to_s in all_statuses:
                if from_s == to_s:
                    continue
                if (from_s.value, to_s.value) not in valid_pairs:
                    if from_s in TERMINAL_STATUSES:
                        reason = f"{from_s.value} is a terminal state, no outbound transitions"
                    else:
                        reason = f"No valid trigger from {from_s.value} to {to_s.value}"
                    forbidden.append({
                        "from_status": from_s.value,
                        "to_status": to_s.value,
                        "reason": reason,
                    })

        return StateMachineTopology(
            nodes=nodes,
            edges=edges,
            forbidden_transitions=forbidden,
            terminal_statuses=[s.value for s in TERMINAL_STATUSES],
            resumable_statuses=[ExecutionStatus.WAITING.value],
            initial_status=ExecutionStatus.PENDING.value,
        )

    def timeline(
        self,
        session_id: str,
        contracts: List[ExecutionContract],
        trace: Optional[List[ExecutionStep]] = None,
    ) -> ExecutionTimeline:
        """Project a list of contracts into an ExecutionTimeline."""
        snapshots = [self.snapshot(c) for c in contracts]
        snapshots.sort(key=lambda s: s.entered_at)

        all_transitions: List[TransitionRecord] = []
        for c in contracts:
            all_transitions.extend(self.transition_records(c))
        all_transitions.sort(key=lambda t: t.timestamp)

        terminal_count = sum(1 for c in contracts if c.status in TERMINAL_STATUSES)
        waiting_count = sum(1 for c in contracts if c.status == ExecutionStatus.WAITING)
        active_count = len(contracts) - terminal_count

        has_irreversible_completed = any(
            c.irreversible and c.status == ExecutionStatus.COMPLETED
            for c in contracts
        )

        started_at = min(c.created_at for c in contracts) if contracts else None
        ended_at = None
        if contracts and terminal_count == len(contracts):
            ended_at = max(
                t["timestamp"]
                for c in contracts
                for t in c.transitions
            ) if any(c.transitions for c in contracts) else None

        return ExecutionTimeline(
            session_id=session_id,
            contracts=snapshots,
            transitions=all_transitions,
            total_contracts=len(contracts),
            terminal_contracts=terminal_count,
            active_contracts=active_count,
            has_suspended=waiting_count > 0,
            has_irreversible_completed=has_irreversible_completed,
            started_at=started_at,
            ended_at=ended_at,
        )
