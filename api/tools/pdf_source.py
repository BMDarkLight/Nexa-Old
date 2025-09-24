import os
from typing import Dict, Any, List
import numpy as np
from bson import ObjectId
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
from pymongo import MongoClient

try:
    knowledge_db = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/")).nexa.embeddings
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
    knowledge_db = None

embedding_model = OpenAIEmbeddings()

class PDFSourceInput(BaseModel):
    query: str = Field(description="The question or topic to search for within the PDF document.")

def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)

def _run_tool(query: str, settings: Dict[str, Any]) -> str:
    TOP_K = 3
    SIMILARITY_THRESHOLD = 0.75

    if not knowledge_db:
        return "Error: Database connection for the knowledge base is not available."

    document_id = settings.get("document_id")
    if not document_id:
        return "Error: Connector is misconfigured. 'document_id' is missing from its settings."

    try:
        source_document = knowledge_db.find_one({"_id": ObjectId(document_id)})
    except Exception as e:
        return f"Error: The provided 'document_id' is invalid or a database error occurred: {e}"

    if not source_document or "chunks" not in source_document:
        return f"Error: No document or text chunks were found for the document ID: {document_id}."

    query_embedding = embedding_model.embed_query(query)

    all_chunks = []
    for chunk in source_document.get("chunks", []):
        if "text" in chunk and "embedding" in chunk:
            similarity = _cosine_similarity(query_embedding, chunk["embedding"])
            all_chunks.append({"text": chunk["text"], "score": similarity})

    sorted_chunks = sorted(all_chunks, key=lambda x: x["score"], reverse=True)
    top_chunks = [chunk for chunk in sorted_chunks if chunk["score"] >= SIMILARITY_THRESHOLD][:TOP_K]

    if not top_chunks:
        return "Could not find any relevant information in the document for that query."

    combined_context = "\n\n---\n\n".join([chunk["text"] for chunk in top_chunks])
    return f"Found relevant information in the document:\n\n{combined_context}"

def get_pdf_source_tool(settings: Dict[str, Any], name: str) -> StructuredTool:
    """
    Factory that creates a configured tool using a closure to ensure serialization.
    """
    args_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The question or topic to search for within the PDF document."
            }
        },
        "required": ["query"]
    }

    return StructuredTool.from_function(
        name=name,
        func=lambda query: _run_tool(query, settings),
        description=(
            "Use this tool to search for information within a specific, pre-loaded PDF document. "
            "Provide a clear question or query about the content you are looking for."
        ),
        args_schema=args_schema
    )
