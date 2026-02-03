from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime

class SemanticInput(BaseModel):
    """
    Normalized input representation from any source (Text, Image, Drag&Drop, etc.)
    """
    text: str = Field(default="", description="Primary text content")
    images: List[str] = Field(default_factory=list, description="List of image references/paths")
    intent: Optional[str] = Field(default=None, description="Detected intent if any")
    files: List[str] = Field(default_factory=list, description="List of file paths")
    raw_event: Optional[Dict[str, Any]] = Field(default=None, description="Original event data for debugging")

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

class HITLRequest(BaseModel):
    """Data contract for Human-in-the-loop requests"""
    type: Literal["confirmation", "selection", "clarification", "permission"]
    message: str
    options: List[Dict[str, Any]] = Field(default_factory=list)
    context_data: Dict[str, Any] = Field(default_factory=dict)

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
    hitl_request: Optional[HITLRequest] = None
    last_human_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = Field(default=None, description="Result from tool execution or error message")
    pending_tool_calls: List[Dict[str, Any]] = Field(default_factory=list, description="List of tool calls to be executed")

    model_config = {
        "arbitrary_types_allowed": True
    }
