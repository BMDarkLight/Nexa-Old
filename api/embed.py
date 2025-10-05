from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import CharacterTextSplitter
from bson import ObjectId

import datetime
import numpy as np
import pandas as pd

from api.database import knowledge_db

embedding_model = OpenAIEmbeddings()

def embed(text: str, chunk_size: int = 1000, overlap: int = 200) -> list:
    text_splitter = CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=overlap)
    chunks = text_splitter.split_text(text)
    
    if not chunks:
        return []

    embeddings = embedding_model.embed_documents(chunks)
    
    return [{"text": chunk, "embedding": emb} for chunk, emb in zip(chunks, embeddings)]

def embed_tabular(df: pd.DataFrame, org_id: ObjectId) -> ObjectId:
    columns = df.columns.tolist()
    sample_rows = df.head(3).to_dict(orient='records')

    summary_lines = []
    for col in columns:
        col_data = df[col]
        dtype = str(col_data.dtype)
        unique_vals = col_data.dropna().unique()[:5]
        unique_vals_str = ', '.join(map(str, unique_vals))
        summary_lines.append(f"Column: {col} (Type: {dtype}), Sample values: {unique_vals_str}")

    summary_text = "\n".join(summary_lines)

    chunks_with_embeddings = embed(summary_text)

    metadata = {
        "is_tabular": True,
        "columns": columns,
        "sample_rows": sample_rows
    }

    return save_embedding(chunks_with_embeddings, org_id, metadata=metadata)

def similarity(vec1, vec2):
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    similarity = dot_product / (norm1 * norm2)
    return similarity

def save_embedding(chunks_with_embeddings: list, org_id: ObjectId, metadata: dict = None) -> ObjectId:
    document = {
        "org_id": org_id,
        "chunks": chunks_with_embeddings,
        "created_at": datetime.utcnow()
    }
    if metadata:
        document.update(metadata)
    result = knowledge_db.insert_one(document)
    return result.inserted_id

def get_embeddings(document_id: ObjectId) -> list:
    result = knowledge_db.find_one({"_id": document_id})
    if result and "chunks" in result:
        return result["chunks"]
    return []