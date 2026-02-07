from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime

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

    # Intent recognition result from IntentNode
    intent_result: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Intent recognition result with category, intent_type, confidence, source, matched_rule, mcp_service_name"
    )

    model_config = {
        "arbitrary_types_allowed": True
    }
