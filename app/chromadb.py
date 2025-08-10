from .config import config
import chromadb
from .logger import logger
import os
import uuid
import requests
import numpy as np
from datetime import datetime

chroma_client = None
chroma_collection = None # This will store the ChromaDB collection object

class WeightedText:
    """Represents text with an associated weight."""
    def __init__(self, text: str, weight: float):
        self.Text = text
        self.Weight = weight

def initialize_chromadb():
    global chroma_client, chroma_collection
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

def add_to_chroma_db(id: str, embedding: list[float], texts: list[WeightedText], original: str) -> str:
    """Adds a document to ChromaDB."""
    # The Go code concatenates texts with a specific format for content metadata.
    content = ""
    for text in texts:
        content += f"{text.Text}-(weight-assign:{text.Weight})-$-$"

    try:
        chroma_collection.add(
            # documents=[content],
            embeddings=[embedding],
            metadatas=[{"content": content, "original": original or ""}],
            ids=[id]
        )
        logger.info(f"Added document with ID: {id}")
        return id
    except Exception as e:
        logger.error(f"Failed to add to ChromaDB: {e}")
        raise

def generate_and_store(texts: list[WeightedText], original: str) -> str:
    """Generates embedding for texts and stores it in ChromaDB."""
    embedding = generate_weighted_embedding(texts)
    doc_id = str(uuid.uuid4()).replace("-", "") # UUIDv4 without hyphens
    return add_to_chroma_db(doc_id, embedding, texts, original or "")

def delete_record(record_id: str) -> str:
    """Deletes a record from ChromaDB by ID."""
    try:
        chroma_collection.delete(ids=[record_id])
        logger.info(f"Deleted document with ID: {record_id}")
        return record_id
    except Exception as e:
        logger.error(f"Failed to delete record {record_id}: {e}")
        raise

def vector_search(query_vector: list[float], n_results: int) -> list[dict]:
    """Performs a vector similarity search in ChromaDB."""
    try:
        results = chroma_collection.query(
            query_embeddings=[query_vector],
            n_results=n_results if n_results is not None else 10,
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