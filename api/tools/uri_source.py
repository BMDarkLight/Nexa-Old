import os
from typing import Dict, Any, List
import numpy as np
import httpx
from bs4 import BeautifulSoup
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_text_splitters import CharacterTextSplitter
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
from functools import partial

embedding_model = OpenAIEmbeddings()

class URISourceInput(BaseModel):
    query: str = Field(description="The question or topic to search for within the web page content.")

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
    url = settings.get("url")
    if not url:
        return "Error: Connector is misconfigured. A 'url' is missing from its settings."

    try:
        response = httpx.get(url, follow_redirects=True, timeout=15.0)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text(separator=' ', strip=True)

        if not page_text.strip():
            return f"Error: No text content could be extracted from the URL: {url}"

        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_text(page_text)
        
        if not chunks:
            return f"Error: Could not split the content from the URL into chunks."

        chunk_embeddings = embedding_model.embed_documents(chunks)
        query_embedding = embedding_model.embed_query(query)

        all_chunks = []
        for i, chunk_embedding in enumerate(chunk_embeddings):
            similarity = _cosine_similarity(query_embedding, chunk_embedding)
            all_chunks.append({"text": chunks[i], "score": similarity})
        
        sorted_chunks = sorted(all_chunks, key=lambda x: x["score"], reverse=True)
        top_chunks = sorted_chunks[:3]

        if not top_chunks or top_chunks[0]["score"] < 0.7:
            return "Could not find any relevant information in the source URI for that query."

        combined_context = "\n\n---\n\n".join([chunk["text"] for chunk in top_chunks])
        return f"Found relevant information from the source URI:\n\n{combined_context}"

    except httpx.RequestError as e:
        return f"Error: Failed to fetch the content from the provided URL: {e}"
    except Exception as e:
        return f"An unexpected error occurred while processing the URI: {e}"

def get_uri_source_tool(settings: Dict[str, Any], name: str) -> StructuredTool:
    """
    Factory that creates a configured tool using a closure to ensure serialization.
    """

    def tool_func(query: str) -> str:
        return _run_tool(query, settings)

    args_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The question or topic to search for within the web page content."
            }
        },
        "required": ["query"]
    }

    return StructuredTool.from_function(
        name=name,
        func=tool_func,
        description=(
            "Use this tool to search for information within a specific web page (URI). "
            "It fetches the content live. Provide a clear question about what you are looking for."
        ),
        args_schema=args_schema
    )