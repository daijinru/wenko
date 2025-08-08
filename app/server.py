import json
import os
import uuid
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

from typing import Dict, Any
import io

from .logger import logger, setup_logger

# LangGraph imports
from langgraph.graph import StateGraph, END
# from langgraph.checkpoint.memory import MemoryCheckpoint
from langchain_core.messages import ToolMessage, HumanMessage, AIMessage

from .states import GraphState
from .config import config, load_config
from .chromadb import initialize_chromadb, WeightedText, generate_weighted_embedding, generate_and_store, vector_search, vector_compare, list_documents, delete_record, export_all_data

def init_app():
    """Initializes the application, loads config, and sets up ChromaDB."""

    # Setup logging
    log_dir = "./logs"
    os.makedirs(log_dir, exist_ok=True)
    setup_logger(log_dir)

    # Load config.json
    load_config("./config.json")

    # Initialize ChromaDB client and ensure tenant, database, and collection exist
    initialize_chromadb()

# --- LangGraph Integration ---
from .session import Session
from .prompts import InteractivePlanningSystemPrompt, Tool_Use_Case_Prompt, AI_Kanban_System_Prompt
global_session = Session()

# Helper to generate UUID
def GenerateUUID() -> str:
    return str(uuid.uuid4()).replace("-", "")

# Helper to send SSE messages (will be collected by the generator)
def _add_sse_message(state: GraphState, event_type: str, data: Dict[str, Any]) -> GraphState:
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
def process_stream_response(resp, logger, state):
    accumulated_content = ""
    text_message_id = GenerateUUID()
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

# 用于分析代码，给出代码解释的函数
def stream_code_explanation(state: GraphState):
    """
    代码解释流式处理
    """
    logger.info("Entered stream code explanation flow")
    content = state["user_input"]
    model_messages = [
        {"role": "user", "content": "请解释以下代码: " + content},
    ]
    model_request_body = {
        "model": config.ModelProviderModel,
        "messages": model_messages,
        "stream": True,  # 开启流式
        "temperature": 0.8,
    }
    req_headers = {
        "Authorization": "Bearer " + config.ModelProviderAPIKey,
        "Content-Type": "application/json"
    }
    try:
        with requests.post(config.ModelProviderURI, json=model_request_body, headers=req_headers, stream=True) as resp:
            resp.raise_for_status()
            yield from process_stream_response(resp, logger, state)
            logger.info(f"stream code explanation result: {state['model_response_content']}")
    except Exception as e:
        logger.error(f"code explanation stream error: {e}")
        state["model_response_content"] = f"模型调用失败: {e}"
        payload = {"type": "statusText", "payload": state["model_response_content"], "actionID": ""}
        sse_msg = {
            "id": state.get("sse_id_counter", 0),
            "event": "text",
            "data": json.dumps(payload)
        }
        yield f"id: {sse_msg['id']}\nevent: {sse_msg['event']}\ndata: {sse_msg['data']}\n\n"

def stream_kanban_daily(state: GraphState):
    """
    看板娘日常对话
    """
    logger.info("Entered stream kanban daily flow")
    content = state["user_input"]
            
    model_messages = [
        {"role": "system", "content": AI_Kanban_System_Prompt()},
        {"role": "user", "content": content},
    ]
    model_request_body = {
        "model": config.ModelProviderModel,
        "messages": model_messages,
        "stream": True,  # 开启流式
        "temperature": 0.8,
    }
    req_headers = {
        "Authorization": "Bearer " + config.ModelProviderAPIKey,
        "Content-Type": "application/json"
    }
    try:
        with requests.post(config.ModelProviderURI, json=model_request_body, headers=req_headers, stream=True) as resp:
            resp.raise_for_status()
            yield from process_stream_response(resp, logger, state)
            logger.info(f"stream kanban daily result: {state['model_response_content']}")
    except Exception as e:
        logger.error(f"kanban daily stream error: {e}")
        state["model_response_content"] = f"模型调用失败: {e}"
        payload = {"type": "statusText", "payload": state["model_response_content"], "actionID": ""}
        sse_msg = {
            "id": state.get("sse_id_counter", 0),
            "event": "text",
            "data": json.dumps(payload)
        }
        yield f"id: {sse_msg['id']}\nevent: {sse_msg['event']}\ndata: {sse_msg['data']}\n\n"

# Nodes for the LangGraph
def initial_setup_node(state: GraphState) -> GraphState:
    logger.info("LangGraph: Initializing task state.")
    state["current_outer_loop"] = 0
    state["break_task"] = False
    state["task_completion_message"] = ""
    state["model_response_content"] = ""
    state["tool_call_name"] = None
    state["tool_call_arguments"] = None
    state["action_id_waiting_for_answer"] = None
    state["sse_messages"] = [] # Clear SSE messages for new task
    state["sse_id_counter"] = 0 # Reset SSE ID counter
    state["handle_sse_messages"] = ""

    # Add initial user message to chat history
    state["chat_history"].append(HumanMessage(content=state["user_input"]))

    return state

def check_interrupt_node(state: GraphState) -> GraphState:
    if check_interrupt(state):
        logger.info("<LangGraph Loop> Task interrupted: User interruption")
        state["break_task"] = True
        state["task_completion_message"] = "任务中断: 用户中断"
        state = _add_sse_message(state, "text", {"type": "statusText", "payload": state["task_completion_message"], "actionID": ""})
    return state

def check_loop_limits(state: GraphState) -> GraphState:
    if state["break_task"]:
        return state # Already marked for break

    if state["current_outer_loop"] >= max_outer_loop:
        state["break_task"] = True
        state["task_completion_message"] = "任务中断: 最大外层循环数"
        state = _add_sse_message(state, "text", {"type": "statusText", "payload": state["task_completion_message"], "actionID": ""})
        return state

    state["current_outer_loop"] += 1
    logger.info(f"Current outer loop: {state['current_outer_loop']}")
    return state

def call_model(state: GraphState) -> GraphState:
    if state["break_task"]:
        return state

    model_messages = [
        {"role": "system", "content": InteractivePlanningSystemPrompt},
    ]
    # Add chat history, ensuring it's in the correct format for the model
    for msg in state["chat_history"]:
        if isinstance(msg, HumanMessage):
            model_messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            if msg.content:
                model_messages.append({"role": "assistant", "content": msg.content})
            if msg.tool_calls:
                # Convert LangChain tool_calls to model's expected format
                for tc in msg.tool_calls:
                    model_messages.append({
                        "role": "assistant",
                        "content": f"[TOOL_CALL][{tc['name']}][id:{tc.get('id', '')}] {json.dumps(tc['args'], ensure_ascii=False)}"
                    })
        elif isinstance(msg, ToolMessage):
            # 转为 assistant role，并在 content 里注明工具调用
            model_messages.append({
                "role": "assistant",
                "content": f"[TOOL_MESSAGE][{msg.tool_call_id}] {msg.content}"
            })


    model_request_body = {
        "model": config.ModelProviderModel,
        "messages": model_messages,
        "stream": True,
        "temperature": 0,
        "tools": Tool_Use_Case_Prompt["tools"],
        "tool_choice": Tool_Use_Case_Prompt["tool_choice"],
    }

    logger.info(f"🌍 Model request body: {json.dumps(model_request_body, indent=2)}")
    logger.info(f"🌍 Model provider URI: {config.ModelProviderURI}")

    try:
        req_headers = {
            "Authorization": "Bearer " + config.ModelProviderAPIKey,
            "Content-Type": "application/json"
        }
        
        # Use requests.post with stream=True for streaming response
        with requests.post(config.ModelProviderURI, json=model_request_body, headers=req_headers, stream=True) as resp:
            resp.raise_for_status()

            tool_call_detected = False
            tool_call_name = ""
            tool_call_arguments_builder = io.StringIO() # Use StringIO to build arguments

            text_message_id = GenerateUUID()
            accumulated_content = ""
            
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

                                content = delta.get("content")
                                if content:
                                    accumulated_content += content
                                    payload = {
                                        "type": "text",
                                        "payload": {
                                            "content": content,
                                            "meta": {"id": text_message_id},
                                        },
                                        "actionID": "",
                                    }
                                    state = _add_sse_message(state, "text", payload)

                                tool_calls = delta.get("tool_calls")
                                if tool_calls and len(tool_calls) > 0:
                                    tool_call_detected = True
                                    # Assuming only one tool call per delta for simplicity, as in Go code
                                    function_call = tool_calls[0].get("function", {})
                                    if function_call.get("name"):
                                        tool_call_name = function_call["name"]
                                    if function_call.get("arguments"):
                                        tool_call_arguments_builder.write(function_call["arguments"])
                                        logger.info(f"><Detected tool call arguments chunk: {function_call['arguments']}")

                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse JSON from model stream: {e}, line: {decoded_line}")
                            continue
            
            state["model_response_content"] = accumulated_content
            state["tool_call_name"] = tool_call_name
            state["tool_call_arguments"] = tool_call_arguments_builder.getvalue()

            if not tool_call_detected:
                logger.warning(f"No tool call detected! Current outer loop: {state['current_outer_loop']} / {max_outer_loop}")
                # 用 HumanMessage 提示模型必须使用工具调用
                prompt = "你没有使用工具调用，请务必使用工具调用，重新回答用户的问题：" + accumulated_content
                state["chat_history"].append(HumanMessage(content=prompt))
                # 这会在下次 call_model 时作为用户输入，强制模型调用工具
                state["tool_call_name"] = "no_tool_detected" # Custom signal for routing
                state["tool_call_arguments"] = "" # Clear arguments
            else:
                if state["tool_call_name"]:
                    try:
                        tool_args_dict = json.loads(state["tool_call_arguments"])
                        tool_call_id = GenerateUUID()
                        state["chat_history"].append(AIMessage(
                            content=accumulated_content,
                            tool_calls=[{
                                "id": tool_call_id,
                                "name": state["tool_call_name"],
                                "args": tool_args_dict
                            }]
                        ))
                        if state["tool_call_name"] == "ask_user":
                            state["action_id_waiting_for_answer"] = tool_call_id
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse tool arguments JSON: {state['tool_call_arguments']}")
                        state["chat_history"].append(AIMessage(content=accumulated_content))
                else:
                    state["chat_history"].append(AIMessage(content=accumulated_content))

    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling model provider: {e}")
        state["break_task"] = True
        state["task_completion_message"] = "调用大模型失败: " + str(e)
        state = _add_sse_message(state, "text", {"type": "statusText", "payload": state["task_completion_message"], "actionID": ""})

    return state

def handle_tool_call(state: GraphState) -> GraphState:
    if state["break_task"]:
        return state

    tool_name = state["tool_call_name"]
    tool_args_str = state["tool_call_arguments"]

    if tool_name == "no_tool_detected":
        state["user_input"] = "你没有使用工具调用，请务必使用工具调用，重新回答用户的问题：" + state["user_input"]
        return state # This will route back to call_model

    try:
        tool_args = json.loads(tool_args_str)
    except json.JSONDecodeError as e:
        logger.error(f"Tool arguments JSON parsing failed for {tool_name}: {e}, args: {tool_args_str}")
        state["break_task"] = True
        state["task_completion_message"] = f"工具解析失败: {tool_name} - {e}"
        state = _add_sse_message(state, "text", {"type": "statusText", "payload": state["task_completion_message"], "actionID": ""})
        return state

    if tool_name == "ask_user":
        action_id = state.get("action_id_waiting_for_answer")
        question = tool_args.get("question", "")
        payload = {
            "type": "ask",
            "payload": {
                "content": question,
                "meta": {
                    "answer": False,
                    "reason": "",
                    "id": action_id,
                },
            },
            "actionID": action_id,
        }
        state = _add_sse_message(state, "text", payload)
        logger.info(f"Waiting for user answer for actionID: {action_id}")
        # 关键：直接结束本轮对话
        state["break_task"] = True
        state["task_completion_message"] = "等待用户回答"
        return state

    elif tool_name == "task_complete":
        summary = tool_args.get("summary", "")
        state["break_task"] = True
        state["task_completion_message"] = "任务已完成: " + summary
        state = _add_sse_message(state, "text", {"type": "statusText", "payload": state["task_completion_message"], "actionID": ""})
        return state

    else:
        state["break_task"] = True
        state["task_completion_message"] = f"检测到未知工具调用: {tool_name}"
        state = _add_sse_message(state, "text", {"type": "statusText", "payload": state["task_completion_message"], "actionID": ""})
        return state

# Max loop counters
max_outer_loop = 2
max_inner_loop = 2

# Build the LangGraph
workflow = StateGraph(GraphState)

def recognize_intent_with_llm(user_input: str) -> str:
    """
    使用大模型进行意图识别
    """
    # 定义意图分类的提示词
    intent_prompt = f"""
    请根据以下用户输入识别其意图，并只返回意图标签：
    
    用户输入: "{user_input}"
    
    可能的意图包括：
    - code_explain: 如果这是代码，请解释代码
    - kanban_daily: code_explain 以外的意图
    
    请只返回一个最匹配的意图标签。
    """
    
    model_messages = [
        {"role": "system", "content": "你是一个意图识别助手，只能返回指定的意图标签。"},
        {"role": "user", "content": intent_prompt}
    ]
    
    model_request_body = {
        "model": config.ModelProviderModel,
        "messages": model_messages,
        "temperature": 0,
        "max_tokens": 20
    }
    
    try:
        req_headers = {
            "Authorization": "Bearer " + config.ModelProviderAPIKey,
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            config.ModelProviderURI, 
            json=model_request_body, 
            headers=req_headers
        )
        response.raise_for_status()
        
        result = response.json()
        intent = result["choices"][0]["message"]["content"].strip().lower()
        # 预置意图列表
        valid_intents = ["task_flow", "code_explain", "kanban_daily"]
        if intent in valid_intents:
            return intent
        else:
            logger.warning(f"Invalid intent detected: {intent}, defaulting to 'unknown'")
            return "unknown"
            
    except Exception as e:
        logger.error(f"Intent recognition failed: {e}")
        return "unknown"

def intent_recognition_node(state: GraphState) -> GraphState:
    """
    通过显性标记或大模型识别用户意图，
    """
    # TODO： 闲聊 small_talk、查询知识库 tool_knowledge_query、代码解析 tool_code_explain、 系统命令 tool_system_calendar(mcp)、
    user_input = state.get("user_input", "").lower()
    logger.info(f"User input: {user_input}")

    if "[task_flow]" in user_input:
        state["intent"] = "task_flow"
        # 看板娘日常
    elif "[kanban_daily]" in user_input:
        state["intent"] = "kanban_daily"
    else:
        intent = recognize_intent_with_llm(user_input)
        logger.info(f"Intent recognized with LLM: {intent}")
        state["intent"] = intent

        if "task_flow" in intent:
            state["intent"] = "task_flow"
        elif "kanban_daily" in intent:
            state["intent"] = "kanban_daily"
        elif "code_explain" in intent:
            state["intent"] = "code_explain"
        else:
            state["intent"] = "unknown"
    logger.info(f"Intent recognized: {state['intent']}")
    return state

# Define nodes
workflow.add_node("intent_recognition", intent_recognition_node)
workflow.add_node("initial_setup", initial_setup_node)
workflow.add_node("check_interrupt", check_interrupt_node)
workflow.add_node("check_loop_limits", check_loop_limits)
workflow.add_node("call_model", call_model)
workflow.add_node("handle_tool_call", handle_tool_call)

# Define edges
# workflow.set_entry_point("initial_setup")
workflow.set_entry_point("intent_recognition")

workflow.add_conditional_edges(
    "intent_recognition",
    lambda state: state["intent"],
    {
        "task_flow": "initial_setup",
        "code_explain": "code_explain",
        "kanban_daily": "kanban_daily",
        "unknown": "unknown_handler",
    },
)

# 工作流：关键词分类
def kanban_daily_node(state: GraphState) -> GraphState:
    logger.info("Entered kanban daily flow")
    # 关键词分类流程
    state["handle_sse_messages"] = "kanban_daily"
    return state
workflow.add_node("kanban_daily", kanban_daily_node)

# 工作流：代码解释
def code_explain_node(state: GraphState) -> GraphState:
    logger.info("Entered code explain flow")
    # 代码解释流程
    state["handle_sse_messages"] = "code_explain"
    return state
workflow.add_node("code_explain", code_explain_node)

# 工作流：未知流程
def fallback_handler_node(state: GraphState) -> GraphState:
    # 未知流程直接结束
    logger.info("Entered other flow")
    state["break_task"] = True
    state["task_completion_message"] = "Unready to handle this intent"
    state = _add_sse_message(state, "text", {"type": "statusText", "payload": state["task_completion_message"], "actionID": ""})
    return state
workflow.add_node("unknown_handler", fallback_handler_node)

# 工作流：工具调用
workflow.add_edge("initial_setup", "check_interrupt")
workflow.add_conditional_edges(
    "check_interrupt",
    lambda state: "break_task" if state["break_task"] else "continue",
    {
        "break_task": END, # If interrupted, end the graph
        "continue": "check_loop_limits",
    },
)
workflow.add_conditional_edges(
    "check_loop_limits",
    lambda state: "break_task" if state["break_task"] else "continue",
    {
        "break_task": END, # If outer loop limit reached, end the graph
        "continue": "call_model",
    },
)
workflow.add_conditional_edges(
    "call_model",
    lambda state: "break_task" if state["break_task"] else ("handle_tool" if state["tool_call_name"] else "no_tool"),
    {
        "handle_tool": "handle_tool_call",
        "no_tool": "handle_tool_call", # Route to handle_tool_call to process "no_tool_detected"
    },
)
workflow.add_conditional_edges(
    "handle_tool_call",
    lambda state: "break_task" if state["break_task"] else "call_model",
    {
        "break_task": END,
        "call_model": "check_loop_limits", # Go back to check_loop_limits after handling tool call
    },
)

# Compile the graph
app_graph = workflow.compile()

# Integrate LangGraph with Flask
def check_interrupt(state: GraphState) -> bool:
    # 遍历 chat_history，查找 content 为 "stop" 的 ToolMessage
    for msg in reversed(state["chat_history"]):
        if isinstance(msg, ToolMessage) and msg.content.strip().lower() == "stop":
            return True
    return False

# --- HTTP Handlers (Flask) ---

app = Flask(__name__)
CORS(app) # Enable CORS for all routes, equivalent to Go's enableCORS middleware

# --- LangGraph Task Handler ---

@app.route("/task", methods=["POST"])
def new_task():
    logger.info("Creating new task...")
    # global_session.entries["ask"] = [] # Reset session for new task

    # From body, get text
    body = request.get_json()
    if not body or "text" not in body:
        return jsonify({"error": "Invalid request body: 'text' field is required."}), 400
    
    chat_request_text = body["text"]
    session_id = body.get("session_id", "default")

    previous_state = global_session.load_state(session_id)
    logger.info(f"Previous state: {previous_state}")
    if previous_state:
        # 恢复历史 chat_history 和等待回答的 action_id
        initial_state: GraphState = {
            "user_input": chat_request_text,
            "chat_history": previous_state["chat_history"],
            "sse_messages": [],
            "model_response_content": "",
            "tool_call_name": None,
            "tool_call_arguments": None,
            "current_outer_loop": 0,
            "break_task": False,
            "task_completion_message": "",
            "action_id_waiting_for_answer": previous_state.get("action_id_waiting_for_answer"),
            "sse_id_counter": 0,
        }
    else:
        # 新任务，初始化空状态
        initial_state: GraphState = {
            "user_input": chat_request_text,
            "chat_history": [],
            "sse_messages": [],
            "model_response_content": "",
            "tool_call_name": None,
            "tool_call_arguments": None,
            "current_outer_loop": 0,
            "break_task": False,
            "task_completion_message": "",
            "action_id_waiting_for_answer": None,
            "sse_id_counter": 0,
        }

    def event_stream():
        for s in app_graph.stream(initial_state):
            current_node_name = list(s.keys())[-1]
            current_state = s[current_node_name]

            # 持久化当前状态，方便下一次恢复
            global_session.save_state(session_id, current_state)

            if current_state.get("handle_sse_messages") == "kanban_daily":
                for sse_event in stream_kanban_daily(current_state):
                    yield sse_event
                current_state["handle_sse_messages"] = None

            if current_state.get("handle_sse_messages") == "code_explain":
                for sse_event in stream_code_explanation(current_state):
                    yield sse_event
                current_state["handle_sse_messages"] = None

            for msg in current_state["sse_messages"]:
                yield f"id: {msg['id']}\nevent: {msg['event']}\ndata: {msg['data']}\n\n"

            current_state["sse_messages"] = []

            if current_state["break_task"]:
                logger.info("Task completed or interrupted: " + current_state["task_completion_message"])
                break

        yield "data: [DONE]\n\n"

    return app.response_class(event_stream(), mimetype='text/event-stream')

@app.route("/answer", methods=["POST"])
def answer_handler():
    data = request.json
    action_id = data.get("actionID")
    answer = data.get("text", "")
    session_id = data.get("session_id", "default")

    if not action_id:
        return jsonify({"error": "Missing actionID"}), 400

    # 加载当前会话状态
    state = global_session.load_state(session_id)
    if not state:
        return jsonify({"error": "Session not found"}), 404

    # 追加 ToolMessage 到 chat_history
    state["chat_history"].append(
        ToolMessage(content=answer, tool_call_id=action_id)
    )
    global_session.save_state(session_id, state)
    logger.info(f"Received answer for actionID {action_id}: {answer}")
    return jsonify({"status": "ok"}), 200

# --- Static File(live2D) Serving ---

from flask import Response, abort

# /live2d 接口用于读取 live2d 目录下的文件
@app.route("/live2d/<path:filename>")
def live2d_send_from_directory(filename):
    live2d_dir = os.path.join(os.getcwd(), "live2d")
    file_path = os.path.join(live2d_dir, filename)
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return jsonify({"error": "File not found"}), 404
    try:
        def generate():
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    yield chunk

        # Guess mimetype by extension (optional)
        import mimetypes
        mimetype, _ = mimetypes.guess_type(file_path)
        return Response(generate(), mimetype=mimetype or "application/octet-stream")
    except Exception as e:
        logger.error(f"Error serving file {filename}: {e}")
        abort(500)

# --- ChromaDB Handlers ---

@app.route("/generate", methods=["POST"])
def generate_handler():
    """Handles requests to generate embeddings and store documents."""
    try:
        request_data = request.json
        if not request_data or "texts" not in request_data:
            return jsonify({"error": "Invalid request body: 'texts' field is required."}), 400

        weighted_texts_raw = request_data["texts"]
        weighted_texts = [WeightedText(text=t["Text"], weight=t["Weight"]) for t in weighted_texts_raw]

        logger.info(f"Storing: {weighted_texts[0].Text if weighted_texts else 'No text provided'}")
        doc_id = generate_and_store(weighted_texts)
        return jsonify({"id": doc_id}), 200
    except Exception as e:
        logger.exception("Error in /generate")
        logger.error(f"Error in /generate: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/search", methods=["POST"])
def search_handler():
    """Handles requests to perform vector similarity search."""
    try:
        request_data = request.json
        if not request_data or "texts" not in request_data or not request_data["texts"]:
            return jsonify({"error": "Invalid request body: 'texts' field should not be empty."}), 400
        print(f"request_data: {request_data}")
        weighted_texts_raw = request_data["texts"]
        weighted_texts = [WeightedText(text=t["Text"], weight=t["Weight"]) for t in weighted_texts_raw]

        logger.info(f"Generating text vector for search: {weighted_texts[0].Text if weighted_texts else 'No text provided'}")
        query_vector = generate_weighted_embedding(weighted_texts)
        logger.info("Text vector generated successfully for search.")

        results = vector_search(query_vector)

        return_results = []
        for result in results:
            content = result["metadata"].get("content")
            return_results.append({
                "id": result["id"],
                "content": content
            })
        return jsonify(return_results), 200
    except Exception as e:
        logger.exception("Error in /search")
        logger.error(f"Error in /search: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/chat", methods=["POST"])
def chat_handler():
    """Placeholder for chat functionality."""
    # The original Go code had mux.HandleFunc("/chat", Chat) but the Chat function was not provided.
    logger.info("Chat endpoint hit (placeholder).")
    return jsonify({"message": "Chat functionality not implemented yet."}), 200

@app.route("/compare", methods=["POST"])
def compare_handler():
    """Handles requests to compare a new text's embedding with an existing document's embedding."""
    try:
        request_data = request.json
        if not request_data or "texts" not in request_data or "id" not in request_data:
            return jsonify({"error": "Invalid request body: 'texts' and 'id' fields are required."}), 400

        weighted_texts_raw = request_data["texts"]
        doc_id = request_data["id"]
        weighted_texts = [WeightedText(text=t["Text"], weight=t["Weight"]) for t in weighted_texts_raw]

        result = vector_compare(weighted_texts, doc_id)
        logger.info(f"Comparison result: {result}")
        return jsonify({"result": result}), 200
    except Exception as e:
        logger.exception("Error in /compare")
        logger.error(f"Error in /compare: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/documents", methods=["POST"])
def documents_handler():
    """Handles requests to list documents with pagination."""
    try:
        request_data = request.json
        limit = request_data.get("limit", 10) # Default limit
        offset = request_data.get("offset", 0) # Default offset

        documents = list_documents(limit, offset)

        all_results = []
        if documents and documents.get('ids'):
            for i in range(len(documents['ids'])):
                result_item = {
                    "id": documents['ids'][i],
                    "metadata": documents['metadatas'][i],
                }
                all_results.append(result_item)
        return jsonify(all_results), 200
    except Exception as e:
        logger.error(f"Error in /documents: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/delete", methods=["GET"]) # Go code uses GET with query param
def delete_handler():
    """Handles requests to delete a document by ID."""
    try:
        doc_id = request.args.get("id") # Get ID from query parameter
        if not doc_id:
            return jsonify({"error": "ID query parameter is missing."}), 400

        logger.info(f"Deleting record: {doc_id}")
        deleted_id = delete_record(doc_id)
        return jsonify({"id": deleted_id}), 200
    except Exception as e:
        logger.error(f"Error in /delete: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/export", methods=["POST"])
def export_handler():
    """Handles requests to export all document data."""
    try:
        logger.info("Received request to export all data.")
        export_all_data()
        # The Go code returns a message with YYYYMMDD, but the actual filename includes HHMMSS.
        # Let's return a more generic message or the actual filename.
        return jsonify({"message": "Data export initiated. Check ./exports directory."}), 200
    except Exception as e:
        logger.error(f"Error in /export: {e}")
        return jsonify({"error": str(e)}), 500