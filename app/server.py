import os
from flask import Flask, request, jsonify, Response, abort
from flask_cors import CORS

from .logger import logger, setup_logger

# LangGraph imports
from langgraph.graph import StateGraph, END
# from langgraph.checkpoint.memory import MemoryCheckpoint
from langchain_core.messages import ToolMessage, HumanMessage

from .types import GraphState
from .config import load_config
from .chromadb import initialize_chromadb, WeightedText, generate_weighted_embedding, generate_and_store, vector_search, vector_compare, list_documents, delete_record, export_all_data

from .stream import stream_kanban_daily, stream_code_explanation, recognize_intent_with_llm

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
global_session = Session()

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

# Build the LangGraph
workflow = StateGraph(GraphState)

# Define nodes
from .nodes import add_nodes_to_workflow

add_nodes_to_workflow(workflow)

workflow.add_node("initial_setup", initial_setup_node)
workflow.add_node("intent_recognition", intent_recognition_node)

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

        # original the Custom Content from frontend, which is not processed but returned in the response
        original = request_data.get("original", "")

        logger.info(f"Storing: {weighted_texts[0].Text if weighted_texts else 'No text provided'}")
        doc_id = generate_and_store(texts=weighted_texts, original=original)
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

        # Get n_results from request, default to 10
        n_results = request_data.get("n_results", 10)
        results = vector_search(query_vector, n_results)

        return_results = []
        for result in results:
            content = result["metadata"].get("content")
            original = result["metadata"].get("original")
            return_results.append({
                "id": result["id"],
                "content": content,
                "original": original,
            })
        return jsonify(return_results), 200
    except Exception as e:
        logger.exception("Error in /search")
        logger.error(f"Error in /search: {e}")
        return jsonify({"error": str(e)}), 500

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