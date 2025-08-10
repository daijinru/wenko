from .helper import GraphState
from typing import List, Dict, Any, Optional

# from langgraph import LangGraphPH, HTTPResponse, Logger # Remove these, they are not standard LangGraph imports
class Payload:
    def __init__(self, content: str, meta: Dict[str, Any], type: str):
        self.content = content
        self.meta = meta
        self.type = type

class MessageType:
    def __init__(self, Type: str, Payload: Payload, ActionID: Optional[str] = None):
        self.Type = Type
        self.Payload = Payload
        self.ActionID = ActionID

# LangGraph State Definition
# TODO 增加近期简短摘要（最近6-10轮对话）、last_intent、last_action、last_expression

class Session:
    def __init__(self):
        self.entries = {"ask": []}
        self.states = {}

    def add_entry(self, key, message: MessageType):
        self.entries[key].append(message)

    def get_entries(self, key) -> List[MessageType]:
        return self.entries.get(key, [])

    def update_entry(self, key, index, entry: MessageType):
        if key in self.entries and 0 <= index < len(self.entries[key]):
            self.entries[key][index] = entry
            return True
        return False
    def save_state(self, session_id: str, state: GraphState):
        self.states[session_id] = state

    def load_state(self, session_id: str) -> Optional[GraphState]:
        return self.states.get(session_id)
        