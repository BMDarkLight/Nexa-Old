import os
from functools import partial
from typing import Dict, Any, List
import numpy as np
from bson import ObjectId
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.tools import Tool
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
    """
    Calculates the cosine similarity between two vectors.
    """
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)

def _read_pdf_logic(settings: Dict[str, Any], query: str) -> str:
    """
    Internal logic to find and return the most relevant text chunk from a stored PDF embedding.
    """
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

    best_chunk_text = None
    highest_similarity = -1.0

    for chunk in source_document.get("chunks", []):
        if "text" in chunk and "embedding" in chunk:
            similarity = _cosine_similarity(query_embedding, chunk["embedding"])
            if similarity > highest_similarity:
                highest_similarity = similarity
                best_chunk_text = chunk["text"]

    if best_chunk_text:
        return f"Found relevant information in the document:\n---\n{best_chunk_text}\n---"
    else:
        return "Could not find any relevant information in the document for that query."

def get_pdf_source_tool(settings: Dict[str, Any], name: str) -> Tool:
    """
    Creates a configured tool for querying PDF embeddings.
    The 'settings' (containing the document_id) are pre-filled and not exposed to the LLM.
    """
    configured_func = partial(_read_pdf_logic, settings)
    
    return Tool(
        name=name,
        func=configured_func,
        description=(
            "Use this tool to search for information within a specific, pre-loaded PDF document. "
            "Provide a clear question or query about the content you are looking for."
        ),
        args_schema=PDFSourceInput
    )