import json
import os
import logging
import uuid
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import chromadb
import numpy as np
from datetime import datetime

from typing import TypedDict, List, Dict, Any, Optional
import time
import io

# LangGraph imports
from langgraph.graph import StateGraph, END
# from langgraph.checkpoint.memory import MemoryCheckpoint
from langchain_core.messages import AnyMessage, ToolMessage, HumanMessage, AIMessage

# --- Configuration and Global Variables ---

class Config:
    """Configuration settings loaded from config.json."""
    def __init__(self):
        self.OllamaURL = ""
        self.ModelProviderURI = ""
        self.ModelProviderModel = ""
        self.ModelProviderAPIKey = ""
        self.Collection = ""
        self.ChromaDBURL = ""
        self.ChromDBTenants = ""
        self.ChromaDBDatabase = ""

config = Config()
logger = logging.getLogger(__name__)
chroma_client = None
chroma_collection = None # This will store the ChromaDB collection object

class WeightedText:
    """Represents text with an associated weight."""
    def __init__(self, text: str, weight: float):
        self.Text = text
        self.Weight = weight

def init_app():
    """Initializes the application, loads config, and sets up ChromaDB."""
    global config, logger, chroma_client, chroma_collection

    # Setup logging
    log_dir = "./logs"
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, "app.log")),
            logging.StreamHandler()
        ]
    )
    logger.info("Logger initialized.")

    # Load config.json
    try:
        with open("config.json", "r") as f:
            data = json.load(f)
            config.OllamaURL = data.get("OllamaURL", "")
            config.ModelProviderURI = data.get("ModelProviderURI", "")
            config.ModelProviderModel = data.get("ModelProviderModel", "")
            config.ModelProviderAPIKey = data.get("ModelProviderAPIKey", "")
            config.Collection = data.get("Collection", "")
            config.ChromaDBURL = data.get("ChromaDBURL", "")
            config.ChromDBTenants = data.get("ChromDBTenants", "")
            config.ChromaDBDatabase = data.get("ChromaDBDatabase", "")
    except FileNotFoundError:
        logger.critical("config.json not found. Please create one.")
        raise
    except json.JSONDecodeError as e:
        logger.critical(f"Failed to parse config.json: {e}")
        raise

    # Initialize ChromaDB client and ensure tenant, database, and collection exist
    try:
        # 解析 ChromaDBURL，拆分 host 和 port，假设格式为 "http://host:port" 或 "host:port"
        from urllib.parse import urlparse

        parsed_url = urlparse(config.ChromaDBURL if config.ChromaDBURL.startswith("http") else "http://" + config.ChromaDBURL)
        host = parsed_url.hostname or "localhost"
        port = parsed_url.port or 8000
        # ssl = parsed_url.scheme == "https"

        # headers 和 settings 可根据需要传入，这里暂时传 None
        chroma_client = chromadb.HttpClient(
            host=host,
            port=port,
            ssl=False,
            headers=None,
            settings=None,
            tenant=config.ChromDBTenants,
            database=config.ChromaDBDatabase,
        )
        logger.info(f"🌍 Initialized ChromaDB client at {host}:{port} with tenant '{config.ChromDBTenants}' and database '{config.ChromaDBDatabase}'")

        # 直接获取集合
        chroma_collection = chroma_client.get_or_create_collection(
            name=config.Collection,
            metadata={"hnsw:space": "ip"}
        )
        logger.info(f"Embedding collection '{chroma_collection.name}' ensured.")

    except Exception as e:
        logger.critical(f"Failed to initialize ChromaDB: {e}")
        raise

    # Placeholder for outbox initialization (Go's outbox.InitModelProvider, outbox.Init)
    # In Python, this would involve setting up a client for the model provider.
    # For now, we'll assume `generate_weighted_embedding` handles this by calling the configured model provider.
    logger.info("Outbox initialization placeholder.")

    # 初始化 outbox 相关的内容

# --- Embedding Generation ---

def generate_embedding_from_ollama_nomic(text: str) -> list[float]:
    """Generates embedding using the configured model provider (Ollama only)."""
    if not config.OllamaURL:
        raise ValueError("OllamaURL is not configured for embedding generation.")

    url = f"{config.OllamaURL}"
    model_name = "nomic-embed-text"

    payload = {
        "model": model_name,
        "prompt": text
    }
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
        data = response.json()
        if "embedding" in data:
            return data["embedding"]
        else:
            raise ValueError(f"Model provider response missing 'embedding': {data}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling Ollama for embedding ({url}): {e}")
        raise

def generate_weighted_embedding(texts: list[WeightedText]) -> list[float]:
    """Generates a single weighted embedding from multiple texts.
    
    This implementation calculates a weighted average of individual text embeddings.
    """
    if not texts:
        raise ValueError("No texts provided for embedding generation.")

    all_embeddings = []
    total_weight = 0.0

    for wt in texts:
        if not wt.Text.strip():
            continue # Skip empty texts

        try:
            embedding = generate_embedding_from_ollama_nomic(wt.Text)
            all_embeddings.append(np.array(embedding) * wt.Weight)
            total_weight += wt.Weight
        except Exception as e:
            logger.warning(f"Could not generate embedding for text '{wt.Text}': {e}")
            # Continue processing other texts, but log the warning.

    if not all_embeddings:
        raise ValueError("Could not generate any embeddings from provided texts.")

    # Sum weighted embeddings and normalize
    combined_embedding = np.sum(all_embeddings, axis=0)
    if total_weight > 0:
        combined_embedding /= total_weight
    else:
        # This case implies all valid texts had a weight of 0, or no valid texts.
        # If all_embeddings is not empty but total_weight is 0, it means all weights were 0.
        # In this scenario, we can return the unweighted average of the embeddings,
        # or raise an error. For now, let's return the average if weights sum to zero.
        logger.warning("Total weight of texts is zero. Returning unweighted average of embeddings.")
        combined_embedding = np.mean(all_embeddings, axis=0)


    return combined_embedding.tolist() # Convert numpy array back to list

# --- ChromaDB Operations (using chromadb client) ---

def add_to_chroma_db(id: str, embedding: list[float], texts: list[WeightedText]) -> str:
    """Adds a document to ChromaDB."""
    # The Go code concatenates texts with a specific format for content metadata.
    content = ""
    for text in texts:
        content += f"{text.Text}-(weight-assign:{text.Weight})-$-$"

    try:
        chroma_collection.add(
            documents=[content],
            embeddings=[embedding],
            metadatas=[{"content": content}],
            ids=[id]
        )
        logger.info(f"Added document with ID: {id}")
        return id
    except Exception as e:
        logger.error(f"Failed to add to ChromaDB: {e}")
        raise

def generate_and_store(texts: list[WeightedText]) -> str:
    """Generates embedding for texts and stores it in ChromaDB."""
    embedding = generate_weighted_embedding(texts)
    doc_id = str(uuid.uuid4()).replace("-", "") # UUIDv4 without hyphens
    return add_to_chroma_db(doc_id, embedding, texts)

def delete_record(record_id: str) -> str:
    """Deletes a record from ChromaDB by ID."""
    try:
        chroma_collection.delete(ids=[record_id])
        logger.info(f"Deleted document with ID: {record_id}")
        return record_id
    except Exception as e:
        logger.error(f"Failed to delete record {record_id}: {e}")
        raise

def vector_search(query_vector: list[float]) -> list[dict]:
    """Performs a vector similarity search in ChromaDB."""
    try:
        results = chroma_collection.query(
            query_embeddings=[query_vector],
            n_results=5, # Hardcoded n_results as in Go code
            include=['metadatas', 'distances'] # Include distances as per Go's VectorSearchResponse
        )
        logger.info(f"Vector search results IDs: {results.get('ids')}")

        all_results = []
        # results['ids'] is a list of lists (one list per query_embedding, typically one)
        if results and results.get('ids') and results['ids'][0]:
            for i in range(len(results['ids'][0])):
                result_item = {
                    "id": results['ids'][0][i],
                    "metadata": results['metadatas'][0][i],
                    # "distance": results['distances'][0][i] # Uncomment if distance is needed in return
                }
                all_results.append(result_item)
        return all_results
    except Exception as e:
        logger.error(f"Failed to perform vector search: {e}")
        raise

def vector_compare(texts: list[WeightedText], id: str) -> bool:
    """Compares a newly generated vector with an existing vector in ChromaDB."""
    new_embedding = generate_weighted_embedding(texts)

    existing_doc = chroma_collection.get(ids=[id], include=['embeddings'])
    try:
        if not existing_doc or len(existing_doc.get('embeddings', [])) == 0:
            raise ValueError(f"No embedding found for ID: {id}")

        existing_embedding = existing_doc['embeddings'][0]

        # Perform comparison using cosine similarity, mirroring Go's `vector.BatchCompare`
        # Assuming `BatchCompare` performs cosine similarity with a threshold.
        vec1 = np.array(new_embedding)
        vec2 = np.array(existing_embedding)

        # Handle zero vectors to avoid division by zero in cosine similarity
        norm_vec1 = np.linalg.norm(vec1)
        norm_vec2 = np.linalg.norm(vec2)

        if norm_vec1 == 0 or norm_vec2 == 0:
            logger.warning(f"One or both vectors are zero for comparison with ID {id}. Returning False.")
            return False

        similarity = np.dot(vec1, vec2) / (norm_vec1 * norm_vec2)
        threshold = 0.99 # Threshold from Go code

        logger.info(f"Comparison result for ID {id}: Similarity={similarity:.4f}, Threshold={threshold}")
        return bool(similarity >= threshold)
    except Exception as e:
        logger.error(f"Failed to compare vectors: {e}")
        raise

def list_documents(limit: int, offset: int) -> dict:
    """Lists documents from ChromaDB with pagination."""
    try:
        results = chroma_collection.get(
            limit=limit,
            offset=offset,
            include=['metadatas'] # Go code includes metadatas
        )
        return results
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise

def export_all_data():
    """Exports all document data from ChromaDB to a Markdown file."""
    try:
        all_documents = []
        limit = 100 # Batch size for fetching documents
        offset = 0
        while True:
            batch = list_documents(limit, offset)
            if not batch or not batch.get('ids'):
                break # No more documents

            for i in range(len(batch['ids'])):
                all_documents.append({
                    "id": batch['ids'][i],
                    "metadata": batch['metadatas'][i]
                })
            offset += limit
            if len(batch['ids']) < limit: # If the last batch is smaller than limit
                break

        if not all_documents:
            logger.info("No data to export.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"export_{timestamp}.md"
        export_dir = "./exports"
        os.makedirs(export_dir, exist_ok=True)
        filepath = os.path.join(export_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("# Exported ChromaDB Documents\n\n")
            f.write(f"Export Date: {datetime.now().isoformat()}\n\n")
            for doc in all_documents:
                doc_id = doc.get("id", "N/A")
                metadata = doc.get("metadata", {})
                content = metadata.get("content", "No content")

                f.write(f"## Document ID: `{doc_id}`\n")
                f.write("```\n")
                f.write(content)
                f.write("\n```\n\n")
                f.write("### Metadata:\n")
                for key, value in metadata.items():
                    f.write(f"- **{key}**: {value}\n")
                f.write("\n---\n\n")

        logger.info(f"Data exported successfully to {filepath}")
    except Exception as e:
        logger.error(f"Error during data export: {e}")
        raise

# --- HTTP Handlers (Flask) ---

app = Flask(__name__)
CORS(app) # Enable CORS for all routes, equivalent to Go's enableCORS middleware

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

# --- LangGraph Integration ---
# from langgraph import LangGraphPH, HTTPResponse, Logger # Remove these, they are not standard LangGraph imports
class MessageType(TypedDict):
    Type: str
    Payload: Dict[str, Any]
    ActionID: Optional[str]

# LangGraph State Definition
class GraphState(TypedDict):
    user_input: str
    chat_history: List[AnyMessage] # To store messages for the LLM
    sse_messages: List[Dict[str, Any]] # To store messages to send via SSE
    model_response_content: str
    tool_call_name: Optional[str]
    tool_call_arguments: Optional[str]
    current_outer_loop: int
    current_inner_loop: int
    break_task: bool # Renamed from break_done
    task_completion_message: str # Renamed from done_message
    action_id_waiting_for_answer: Optional[str] # For ask_user tool
    sse_id_counter: int # For SSE 'id' field
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
        

global_session = Session()
# logger = Logger("outbox.log") # Use the existing logger

# Constants from Go code (placeholders)
InteractivePlanningSystemPrompt = """
You are an AI assistant designed to help users with various tasks by planning and executing actions.
You have access to a set of tools to interact with the user and complete tasks.
Your primary goal is to break down complex requests into smaller, manageable steps and use the available tools effectively.

Available tools:
1. `ask_user`: Use this tool when you need more information from the user to proceed with the task. Provide a clear and concise question.
2. `task_complete`: Use this tool when you have successfully completed the user's request or determined that no further action is possible/necessary. Provide a summary of the task completion.

Always prioritize using tools to achieve the task. If you need information, ask the user. If the task is done, complete it.
"""

Tool_Use_Case_Prompt = {
    "tools": [
        {
            "type": "function",
            "function": {
                "name":        "ask_user",
                "description": "Ask the user a question to get more information or clarification. The question should be clear and concise.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "The question to ask the user."
                        }
                    },
                    "required": ["question"]
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name":        "task_complete",
                "description": "Indicate that the task is complete and provide a summary of the outcome.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "summary": {
                            "type": "string",
                            "description": "A summary of the completed task."
                        }
                    },
                    "required": ["summary"]
                },
            },
        },
    ],
    "tool_choice": "auto",
}

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

# Nodes for the LangGraph
def initial_setup_node(state: GraphState) -> GraphState:
    logger.info("LangGraph: Initializing task state.")
    state["current_outer_loop"] = 0
    state["current_inner_loop"] = 0
    state["break_task"] = False
    state["task_completion_message"] = ""
    state["model_response_content"] = ""
    state["tool_call_name"] = None
    state["tool_call_arguments"] = None
    state["action_id_waiting_for_answer"] = None
    state["sse_messages"] = [] # Clear SSE messages for new task
    state["sse_id_counter"] = 0 # Reset SSE ID counter

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
        state["task_completion_message"] = "任务中断: 最大循环数"
        state = _add_sse_message(state, "text", {"type": "statusText", "payload": state["task_completion_message"], "actionID": ""})
        return state

    state["current_outer_loop"] += 1
    logger.info(f"Current outer loop: {state['current_outer_loop']}")
    return state

def call_model(state: GraphState) -> GraphState:
    if state["break_task"]:
        return state

    # Limit inner loop
    if state["current_inner_loop"] >= max_inner_loop:
        logger.info(f"Inner loop count reached maximum: {state['current_inner_loop']} / {max_inner_loop}")
        state["break_task"] = True
        state["task_completion_message"] = "任务中断: 最大内层循环数"
        state = _add_sse_message(state, "text", {"type": "statusText", "payload": state["task_completion_message"], "actionID": ""})
        return state

    state["current_inner_loop"] += 1

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
                        "tool_calls": [{
                            "id": GenerateUUID(), # Model might expect an ID
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc["args"])
                            }
                        }]
                    })
        elif isinstance(msg, ToolMessage):
            model_messages.append({"role": "tool", "tool_call_id": msg.tool_call_id, "content": msg.content})


    model_request_body = {
        "model": config.ModelProviderModel,
        "messages": model_messages,
        "stream": True,
        "temperature": 0,
        "tools": Tool_Use_Case_Prompt["tools"],
        "tool_choice": Tool_Use_Case_Prompt["tool_choice"],
    }

    # logger.info(f"🌍 Model request body: {json.dumps(model_request_body, indent=2)}")
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

            # Add the AI's response to chat history
            if state["tool_call_name"]:
                # If a tool was called, add an AIMessage with tool_calls
                try:
                    tool_args_dict = json.loads(state["tool_call_arguments"])
                    tool_call_id = GenerateUUID()
                    state["chat_history"].append(AIMessage(
                        content=accumulated_content, # Content might be empty if only tool call
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
                    # Fallback to just content if args are malformed
                    state["chat_history"].append(AIMessage(content=accumulated_content))
            else:
                state["chat_history"].append(AIMessage(content=accumulated_content))

            if not tool_call_detected:
                logger.warning(f"No tool call detected! Current inner loop: {state['current_inner_loop']} / {max_inner_loop}")
                # This will trigger a retry in the next step if not already broken
                state["tool_call_name"] = "no_tool_detected" # Custom signal for routing
                state["tool_call_arguments"] = "" # Clear arguments

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
max_inner_loop = 5

# Build the LangGraph
workflow = StateGraph(GraphState)

# Define nodes
workflow.add_node("initial_setup", initial_setup_node)
workflow.add_node("check_interrupt", check_interrupt_node)
workflow.add_node("check_loop_limits", check_loop_limits)
workflow.add_node("call_model", call_model)
workflow.add_node("handle_tool_call", handle_tool_call)

# Define edges
workflow.set_entry_point("initial_setup")
# 直连 initial_setup 到 check_interrupt
workflow.add_edge("initial_setup", "check_interrupt")
# 条件连接 check_interrupt 到 break_task 或 continue
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
    lambda state: "handle_tool" if state["tool_call_name"] else "no_tool",
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
        "call_model": "check_interrupt",
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
            "current_inner_loop": 0,
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
            "current_inner_loop": 0,
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
    answer = data.get("answer", "")
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


# --- Main Execution ---

if __name__ == "__main__":
    try:
        init_app() # Initialize configuration and ChromaDB
        logger.info("✅ Server running on :8080")
        # Run Flask app. host="0.0.0.0" makes it accessible externally.
        # debug=False for production, set to True for development for auto-reloading and detailed errors.
        app.run(host="0.0.0.0", port=8080, debug=False)
    except Exception as e:
        logger.critical(f"Application failed to start: {e}")
        exit(1)