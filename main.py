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
        chroma_client = chromadb.HttpClient(host=config.ChromaDBURL)
        logger.info(f"🌍 Initializing ChromaDB client at {config.ChromaDBURL}")

        # Ensure tenant exists
        logger.info("🌍 Ensuring tenant exists...")
        chroma_client.get_or_create_tenant(name=config.ChromDBTenants)
        logger.info("Tenant ensured.")

        # Ensure database exists within the tenant
        logger.info("🌍 Ensuring database exists...")
        db = chroma_client.get_or_create_database(name=config.ChromaDBDatabase, tenant=config.ChromDBTenants)
        logger.info("Database ensured.")

        # Ensure embedding collection exists within the database
        logger.info("🌍 Ensuring Embedding collection exists...")
        # The Go code sets "hnsw:space": "ip" as metadata. This is typically a collection parameter
        # that defines the distance function for HNSW indexing.
        # For chromadb.HttpClient, this is often handled by the server configuration or
        # implicitly by the embedding function if ChromaDB is generating embeddings.
        # When providing pre-computed embeddings, the space is usually set at collection creation.
        # The `metadata` parameter in `get_or_create_collection` is for user-defined metadata
        # about the collection itself, not for the HNSW space.
        # However, to mirror the Go code's intent, we pass it as metadata.
        # If this doesn't set the HNSW space correctly, it might need server-side configuration.
        chroma_collection = db.get_or_create_collection(
            name=config.Collection,
            metadata={"hnsw:space": "ip"} # This might be ignored or used differently by ChromaDB server
        )
        logger.info(f"Embedding collection ensured: {chroma_collection.name}")

    except Exception as e:
        logger.critical(f"Failed to initialize ChromaDB: {e}")
        raise

    # Placeholder for outbox initialization (Go's outbox.InitModelProvider, outbox.Init)
    # In Python, this would involve setting up a client for the model provider.
    # For now, we'll assume `generate_weighted_embedding` handles this by calling the configured model provider.
    logger.info("Outbox initialization placeholder.")

# --- Embedding Generation ---

def generate_embedding_from_model_provider(text: str) -> list[float]:
    """Generates embedding using the configured model provider (e.g., Ollama)."""
    if not config.ModelProviderURI and not config.OllamaURL:
        raise ValueError("Neither ModelProviderURI nor OllamaURL is configured for embedding generation.")

    # Prioritize ModelProviderURI if available, otherwise fall back to OllamaURL
    url = f"{config.ModelProviderURI}/embeddings" if config.ModelProviderURI else f"{config.OllamaURL}/api/embeddings"
    model_name = config.ModelProviderModel if config.ModelProviderModel else "llama2" # Default if not specified

    payload = {
        "model": model_name,
        "prompt": text
    }
    headers = {"Content-Type": "application/json"}
    if config.ModelProviderAPIKey:
        headers["Authorization"] = f"Bearer {config.ModelProviderAPIKey}"

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        data = response.json()
        if "embedding" in data:
            return data["embedding"]
        else:
            raise ValueError(f"Model provider response missing 'embedding': {data}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling model provider for embedding ({url}): {e}")
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
            embedding = generate_embedding_from_model_provider(wt.Text)
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
        content += f"{text.Text}-(weight-assign:{text.Weight})-$-"

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

    try:
        # Get the existing embedding by ID
        existing_doc = chroma_collection.get(ids=[id], include=['embeddings'])
        if not existing_doc or not existing_doc.get('embeddings') or not existing_doc['embeddings'][0]:
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
        return similarity >= threshold
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
        weighted_texts = [WeightedText(text=t["text"], weight=t["weight"]) for t in weighted_texts_raw]

        logger.info(f"Storing: {weighted_texts[0].Text if weighted_texts else 'No text provided'}")
        doc_id = generate_and_store(weighted_texts)
        return jsonify({"id": doc_id}), 200
    except Exception as e:
        logger.error(f"Error in /generate: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/search", methods=["POST"])
def search_handler():
    """Handles requests to perform vector similarity search."""
    try:
        request_data = request.json
        if not request_data or "texts" not in request_data or not request_data["texts"]:
            return jsonify({"error": "Invalid request body: 'texts' field should not be empty."}), 400

        weighted_texts_raw = request_data["texts"]
        weighted_texts = [WeightedText(text=t["text"], weight=t["weight"]) for t in weighted_texts_raw]

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
        weighted_texts = [WeightedText(text=t["text"], weight=t["weight"]) for t in weighted_texts_raw]

        result = vector_compare(weighted_texts, doc_id)
        logger.info(f"Comparison result: {result}")
        return jsonify({"result": result}), 200
    except Exception as e:
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

# Placeholder for outbox handlers (Go's outbox.NewTask, outbox.PlanningTaskAnswer, outbox.InterruptTask)
# These would typically be implemented in a separate module or class, similar to Go's outbox package.
@app.route("/task", methods=["POST"])
def new_task_handler():
    logger.info("New task endpoint hit (placeholder).")
    return jsonify({"message": "New task functionality not implemented yet."}), 200

@app.route("/planning/task/answer", methods=["POST"])
def planning_task_answer_handler():
    logger.info("Planning task answer endpoint hit (placeholder).")
    return jsonify({"message": "Planning task answer functionality not implemented yet."}), 200

@app.route("/planning/task/interrupt", methods=["POST"])
def interrupt_task_handler():
    logger.info("Interrupt task endpoint hit (placeholder).")
    return jsonify({"message": "Interrupt task functionality not implemented yet."}), 200

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

# The /import endpoint was commented out in the Go code, so it's omitted here.

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