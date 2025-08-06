
from langchain_core.messages import AnyMessage

from typing import TypedDict, List, Dict, Any, Optional

class GraphState(TypedDict):
    user_input: str
    chat_history: List[AnyMessage] # To store messages for the LLM
    sse_messages: List[Dict[str, Any]] # To store messages to send via SSE
    model_response_content: str
    tool_call_name: Optional[str]
    tool_call_arguments: Optional[str]
    current_outer_loop: int
    break_task: bool # Renamed from break_done
    task_completion_message: str # Renamed from done_message
    action_id_waiting_for_answer: Optional[str] # For ask_user tool
    sse_id_counter: int # For SSE 'id' field
    handle_sse_messages: str # For handling SSE messages
