import os
from typing import Dict, Any, List
import numpy as np
from bson import ObjectId
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.tools import tool
from pydantic import BaseModel, Field
from pymongo import MongoClient

from api.embed import similarity

try:
    knowledge_db = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/")).nexa.embeddings
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
    knowledge_db = None

embedding_model = OpenAIEmbeddings()

class PDFSourceInput(BaseModel):
    query: str = Field(description="The question or topic to search for within the PDF document.")

def get_pdf_source_tool(settings: Dict[str, Any], name: str):
    """
    Pydantic v2-compliant PDF source connector using LangChain @tool pattern.
    """
    TOP_K = 3
    SIMILARITY_THRESHOLD = 0.75


    @tool
    def pdf_source(query: str) -> str:
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
                score = similarity(query_embedding, chunk["embedding"])
                all_chunks.append({"text": chunk["text"], "score": score})

        sorted_chunks = sorted(all_chunks, key=lambda x: x["score"], reverse=True)
        top_chunks = [chunk for chunk in sorted_chunks if chunk["score"] >= SIMILARITY_THRESHOLD][:TOP_K]

        if not top_chunks:
            return "Could not find any relevant information in the document for that query."

        combined_context = "\n\n---\n\n".join([chunk["text"] for chunk in top_chunks])
        return f"Found relevant information in the document:\n\n{combined_context}"

    pdf_source.name = name
    return pdf_source