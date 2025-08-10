from .types import GraphState
import json
from .session import MessageType
import uuid

# Helper to send SSE messages (will be collected by the generator)
def add_sse_message(state: GraphState, event_type: str, data: MessageType) -> GraphState:
    state["sse_id_counter"] += 1
    out_message = {
        "type": event_type,
        "payload": data,
        "actionID": data.get("actionID", "") # Ensure actionID is passed if present
    }
    state["sse_messages"].append({
        "id": state["sse_id_counter"],
        "event": event_type,
        "data": json.dumps(out_message)
    })
    return state

# TODO 增加工具类型
def process_stream_response(resp, logger, state: GraphState):
    accumulated_content = ""
    text_message_id = generate_uuid()
    sse_id_counter = state.get("sse_id_counter", 0)
    for line in resp.iter_lines():
        if line:
            decoded_line = line.decode('utf-8')
            if decoded_line.startswith("data: "):
                data = decoded_line[6:]
                if data == "[DONE]":
                    break
                try:
                    or_resp = json.loads(data)
                    if or_resp.get("choices") and len(or_resp["choices"]) > 0:
                        choice = or_resp["choices"][0]
                        delta = choice.get("delta", {})
                        content_piece = delta.get("content")
                        if content_piece:
                            accumulated_content += content_piece
                            payload = {
                                "type": "text",
                                "payload": {
                                    "content": content_piece,
                                    "meta": {"id": text_message_id},
                                    "type": "text",
                                },
                                "actionID": "",
                            }
                            sse_msg = {
                                "id": sse_id_counter,
                                "event": "text",
                                "data": json.dumps(payload)
                            }
                            sse_id_counter += 1
                            yield f"id: {sse_msg['id']}\nevent: {sse_msg['event']}\ndata: {sse_msg['data']}\n\n"
                except Exception as e:
                    logger.error(f"Stream JSON decode error: {e}, line: {decoded_line}")
                    continue
    state["model_response_content"] = accumulated_content
    state["sse_id_counter"] = sse_id_counter

# Helper to generate UUID
def generate_uuid() -> str:
    return str(uuid.uuid4()).replace("-", "")