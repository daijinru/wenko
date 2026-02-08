import logging
from typing import List, Dict, Any, Optional, Literal
from enum import Enum
from uuid import uuid4
from pydantic import BaseModel, Field
from datetime import datetime

logger = logging.getLogger(f"workflow.{__name__}")

class SemanticInput(BaseModel):
    """
    Normalized input representation from any source (Text, Image, Drag&Drop, etc.)
    """
    text: str = Field(default="", description="Primary text content")
    images: List[str] = Field(default_factory=list, description="List of image references/paths or base64 data")
    intent: Optional[str] = Field(default=None, description="Detected intent if any")
    files: List[str] = Field(default_factory=list, description="List of file paths")
    raw_event: Optional[Dict[str, Any]] = Field(default=None, description="Original event data for debugging")
    image_action: Optional[str] = Field(default=None, description="Image action: 'analyze_only' or 'analyze_for_memory'")

class EmotionalContext(BaseModel):
    """
    Current emotional state of the user and system modulation parameters.
    """
    current_emotion: str = Field(default="neutral", description="Detected user emotion")
    valence: float = Field(default=0.0, description="Positive/Negative sentiment (-1.0 to 1.0)")
    arousal: float = Field(default=0.0, description="Intensity of emotion (0.0 to 1.0)")
    modulation_instruction: str = Field(default="", description="System prompt instruction for tone modulation")

class MemoryRef(BaseModel):
    """Reference to a long-term memory item"""
    id: str
    content: str
    type: str  # preference, fact, pattern
    confidence: float

class WorkingMemory(BaseModel):
    """
    Short-term context and current task state.
    """
    short_term_context: List[Dict[str, Any]] = Field(default_factory=list, description="Recent relevant context items")
    current_goals: List[str] = Field(default_factory=list, description="Stack of current goals")
    retrieved_memories: List[MemoryRef] = Field(default_factory=list, description="Relevant long-term memories for current turn")

class ExecutionStep(BaseModel):
    """Snapshot of a key decision or action in the cognitive graph"""
    node_id: str
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())
    action: str
    result: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ECSRequest(BaseModel):
    """Data contract for Externalized Cognitive Step requests"""
    type: str  # e.g., 'form', 'confirmation', 'visual_display', etc.
    message: str
    options: List[Dict[str, Any]] = Field(default_factory=list)
    context_data: Dict[str, Any] = Field(default_factory=dict)

class ExecutionStatus(str, Enum):
    """Minimal and complete execution status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

# Valid state transitions: {from_status: {trigger: to_status}}
_VALID_TRANSITIONS: Dict[str, Dict[str, str]] = {
    ExecutionStatus.PENDING: {
        "start": ExecutionStatus.RUNNING,
    },
    ExecutionStatus.RUNNING: {
        "succeed": ExecutionStatus.COMPLETED,
        "fail": ExecutionStatus.FAILED,
        "reject": ExecutionStatus.REJECTED,
        "suspend": ExecutionStatus.WAITING,
        "cancel": ExecutionStatus.CANCELLED,
    },
    ExecutionStatus.WAITING: {
        "resume": ExecutionStatus.RUNNING,
        "cancel": ExecutionStatus.CANCELLED,
        "timeout": ExecutionStatus.CANCELLED,
    },
    # Terminal states: no transitions out
    ExecutionStatus.COMPLETED: {},
    ExecutionStatus.FAILED: {},
    ExecutionStatus.REJECTED: {},
    ExecutionStatus.CANCELLED: {},
}

TERMINAL_STATUSES = frozenset({
    ExecutionStatus.COMPLETED,
    ExecutionStatus.FAILED,
    ExecutionStatus.REJECTED,
    ExecutionStatus.CANCELLED,
})


class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    pass


class ExecutionContract(BaseModel):
    """A concrete execution attempt bound to an action."""

    # Identity
    execution_id: str = Field(default_factory=lambda: str(uuid4()))
    action_type: str  # "tool_call" | "ecs_request"
    action_detail: Dict[str, Any] = Field(default_factory=dict)

    # Constraints
    irreversible: bool = False
    idempotency_key: Optional[str] = None
    timeout_seconds: Optional[int] = None

    # State Machine
    status: ExecutionStatus = ExecutionStatus.PENDING
    transitions: List[Dict[str, Any]] = Field(default_factory=list)

    # Result
    result: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Timestamps
    created_at: float = Field(default_factory=lambda: datetime.now().timestamp())
    updated_at: float = Field(default_factory=lambda: datetime.now().timestamp())

    def transition(self, trigger: str, actor: str) -> None:
        """
        Advance the state machine via a named trigger.

        Args:
            trigger: The transition trigger (e.g. "start", "succeed", "fail")
            actor: Who is performing this transition (e.g. "tool_node", "ecs_node")

        Raises:
            InvalidTransitionError: If the transition is not valid from current status
        """
        valid = _VALID_TRANSITIONS.get(self.status, {})
        if trigger not in valid:
            logger.warning(
                f"[Contract:{self.execution_id[:8]}] Invalid transition: "
                f"trigger='{trigger}' from status='{self.status.value}' "
                f"(valid: {list(valid.keys()) or 'none - terminal'})"
            )
            raise InvalidTransitionError(
                f"Cannot apply trigger '{trigger}' from status '{self.status.value}'. "
                f"Valid triggers: {list(valid.keys()) or '(none - terminal state)'}"
            )

        from_status = self.status
        to_status = valid[trigger]
        self.status = to_status
        self.updated_at = datetime.now().timestamp()
        self.transitions.append({
            "from": from_status.value,
            "to": to_status.value,
            "trigger": trigger,
            "timestamp": self.updated_at,
            "actor": actor,
        })
        logger.info(
            f"[Contract:{self.execution_id[:8]}] {from_status.value} --{trigger}--> {to_status.value} "
            f"(actor={actor}, type={self.action_type})"
        )

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES


def compute_idempotency_key(action_detail: Dict[str, Any]) -> Optional[str]:
    """Compute an idempotency key from action details."""
    service = action_detail.get("service", "")
    method = action_detail.get("method", "")
    args = action_detail.get("args", {})
    if service and method:
        import hashlib
        args_str = str(sorted(args.items())) if isinstance(args, dict) else str(args)
        args_hash = hashlib.md5(args_str.encode()).hexdigest()[:8]
        return f"{service}:{method}:{args_hash}"
    return None


def can_create_contract(
    action_detail: Dict[str, Any],
    existing_contracts: List["ExecutionContract"],
) -> bool:
    """Check if a new contract can be created for the given action.

    Blocks creation if an irreversible contract with the same idempotency key
    has already COMPLETED.
    """
    key = compute_idempotency_key(action_detail)
    if key is None:
        return True
    for existing in existing_contracts:
        if (existing.irreversible
                and existing.status == ExecutionStatus.COMPLETED
                and existing.idempotency_key == key):
            return False
    return True


class GraphState(BaseModel):
    """
    The Single Source of Truth for the cognitive system.
    """
    # Identity & Lifecycle
    conversation_id: str
    status: Literal["idle", "processing", "suspended", "error"] = "idle"

    # Core Components
    semantic_input: SemanticInput = Field(default_factory=SemanticInput)
    emotional_context: EmotionalContext = Field(default_factory=EmotionalContext)
    working_memory: WorkingMemory = Field(default_factory=WorkingMemory)

    # History & Trace
    dialogue_history: List[Dict[str, Any]] = Field(default_factory=list, description="Standard OpenAI format messages")
    execution_trace: List[ExecutionStep] = Field(default_factory=list)

    # Interaction State
    ecs_request: Optional[ECSRequest] = None
    ecs_full_request: Optional[Dict[str, Any]] = Field(default=None, description="Full ECS request data for frontend")
    last_human_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = Field(default=None, description="Result from tool execution or error message")
    pending_tool_calls: List[Dict[str, Any]] = Field(default_factory=list, description="List of tool calls to be executed")

    # Output fields for streaming
    response: Optional[str] = Field(default=None, description="Generated response text")
    detected_emotion: Optional[Dict[str, Any]] = Field(default=None, description="Emotion detected from response")
    memories_to_store: List[Dict[str, Any]] = Field(default_factory=list, description="Memories to be saved")

    # Tool call tracking for loop detection
    tool_call_history: List[Dict[str, Any]] = Field(default_factory=list, description="History of tool calls for loop detection")

    # Execution State Machine
    pending_executions: List[ExecutionContract] = Field(default_factory=list, description="Contracts pending execution")
    completed_executions: List[ExecutionContract] = Field(default_factory=list, description="Contracts that have reached a terminal or waiting state")

    # Intent recognition result from IntentNode
    intent_result: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Intent recognition result with category, intent_type, confidence, source, matched_rule, mcp_service_name"
    )

    model_config = {
        "arbitrary_types_allowed": True
    }
