from fastapi import Depends, APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from bson import ObjectId

import io
import logging

from api.embed import embed, save_embedding, get_embeddings, get_openai_callback
from api.database import agents_db, knowledge_db, minio_client
from api.auth import verify_token, oauth2_scheme
from api.schemas.context import (
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_table_from_excel,
    extract_table_from_csv,
)

router = APIRouter(tags=["Context Management"])

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_context_embedding(
    agent_id: str,
    user_org_id,
    file_content: bytes,
    file_key: str,
    file_name: str,
    content_type: str,
    logger,
):
    try:
        logger.info(f"Background task: processing file for agent_id={agent_id}, filename={file_name}")
        is_tabular = False
        context_id = None
        token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        with get_openai_callback() as cb:
            if content_type == "application/pdf":
                text = extract_text_from_pdf(file_content)
                if not text.strip():
                    logger.error("No extractable text in PDF.")
                    return
                chunks_with_embeddings = embed(text)
                logger.info(f"Generated embeddings for PDF: {len(chunks_with_embeddings)} chunks")
                if not chunks_with_embeddings:
                    logger.error("Failed to generate embeddings for PDF.")
                    return
                context_id = save_embedding(chunks_with_embeddings, user_org_id)
                logger.info(f"Saved PDF embeddings to DB with context_id={context_id}")
                knowledge_db.update_one(
                    {"_id": context_id},
                    {"$set": {"file_key": file_key, "is_tabular": False}}
                )
                logger.info(f"Updated knowledge_db for PDF context {context_id}")
            elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                text = extract_text_from_docx(file_content)
                if not text.strip():
                    logger.error("No extractable text in DOCX.")
                    return
                chunks_with_embeddings = embed(text)
                logger.info(f"Generated embeddings for DOCX: {len(chunks_with_embeddings)} chunks")
                if not chunks_with_embeddings:
                    logger.error("Failed to generate embeddings for DOCX.")
                    return
                context_id = save_embedding(chunks_with_embeddings, user_org_id)
                logger.info(f"Saved DOCX embeddings to DB with context_id={context_id}")
                knowledge_db.update_one(
                    {"_id": context_id},
                    {"$set": {"file_key": file_key, "is_tabular": False}}
                )
                logger.info(f"Updated knowledge_db for DOCX context {context_id}")
            elif content_type == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
                logger.error("PowerPoint upload not supported.")
                return
            elif content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" or content_type == "text/csv":
                if content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                    table_data = extract_table_from_excel(file_content)
                else:
                    table_data = extract_table_from_csv(file_content)

                if table_data.get("shape", (0, 0))[0] > 300:
                    logger.error("Spreadsheet exceeds 300-row limit.")
                    raise HTTPException(status_code=400, detail="Spreadsheet exceeds limit of 300 rows.")

                if not table_data:
                    logger.error("No extractable table data in spreadsheet.")
                    raise HTTPException(status_code=400, detail="Unrecognizable spreadsheet format.")

                schema = table_data.get("schema", {})
                sample = table_data.get("sample", [])[:10]
                shape = table_data.get("shape", ())
                dataframe = table_data.get("dataframe")
                if dataframe is not None:
                    try:
                        data_json = dataframe.to_json(orient="split")
                    except Exception as e:
                        logger.error(f"Failed to serialize dataframe to JSON: {e}")
                        data_json = None
                else:
                    logger.warning("No dataframe found in table_data; cannot serialize.")
                    data_json = None
                doc = {
                    "file_key": file_key,
                    "is_tabular": True,
                    "org": user_org_id,
                    "schema": schema,
                    "sample": sample,
                    "shape": shape,
                    "data_json": data_json
                }
                result = knowledge_db.insert_one(doc)
                context_id = result.inserted_id
                logger.info(f"Inserted spreadsheet structured data to DB with context_id={context_id}")
                is_tabular = True
            else:
                logger.error(f"Unsupported file type: {content_type}")
                return
            if context_id:
                agents_db.update_one(
                    {"_id": ObjectId(agent_id)},
                    {"$push": {"context": context_id}}
                )
                logger.info(f"Updated agent {agent_id} with new context {context_id}")
            token_usage["prompt_tokens"] = cb.prompt_tokens
            token_usage["completion_tokens"] = cb.completion_tokens
            token_usage["total_tokens"] = cb.total_tokens
            logger.info(f"Token usage: prompt={cb.prompt_tokens}, completion={cb.completion_tokens}, total={cb.total_tokens}")
    except Exception as e:
        logger.exception(f"Background embedding/ingestion error for agent_id={agent_id}, filename={file_name}: {e}")

@router.get("/agents/{agent_id}/context")
def list_context_entries(agent_id: str, token: str = Depends(oauth2_scheme)):
    try:
        user = verify_token(token)
        if not ObjectId.is_valid(agent_id):
            raise HTTPException(status_code=400, detail="Invalid agent ID format.")
        agent = agents_db.find_one({"_id": ObjectId(agent_id), "org": ObjectId(user["organization"])})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found or you do not have permission to view it.")
        context_ids = agent.get("context", [])
        context_entries = []
        for cid in context_ids:
            try:
                entry = knowledge_db.find_one({
                    "_id": ObjectId(cid),
                    "org": ObjectId(user["organization"])
                })
                if entry:
                    context_entries.append({
                        "context_id": str(entry["_id"]),
                        "file_key": entry.get("file_key"),
                        "is_tabular": entry.get("is_tabular", False),
                        "created_at": str(entry.get("created_at", "")),
                        "filename": "_".join(entry.get("file_key", "").split("_")[1:]) if entry.get("file_key") else "",
                    })
            except Exception as inner_e:
                logger.warning(f"Skipping invalid context ID {cid}: {inner_e}")
                continue

        logger.info(f"Listed {len(context_entries)} context entries for agent {agent_id}.")
        return context_entries
    except Exception as e:
        logger.exception(f"Failed to list context entries for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list context entries: {str(e)}")

@router.get("/agents/{agent_id}/context/{context_id}")
def get_context_entry(agent_id: str, context_id: str, token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    if not ObjectId.is_valid(agent_id) or not ObjectId.is_valid(context_id):
        raise HTTPException(status_code=400, detail="Invalid ID format.")

    agent = agents_db.find_one({"_id": ObjectId(agent_id), "org": ObjectId(user["organization"])})
    if not agent or ObjectId(context_id) not in agent.get("context", []):
        raise HTTPException(status_code=404, detail="Context entry not found for this agent.")

    context_entry = knowledge_db.find_one({"_id": ObjectId(context_id), "org": ObjectId(user["organization"])})
    if not context_entry:
        raise HTTPException(status_code=404, detail="Context entry not found or permission denied.")

    response = {
        "context_id": str(context_entry["_id"]),
        "file_key": context_entry.get("file_key"),
        "is_tabular": context_entry.get("is_tabular", False),
        "created_at": str(context_entry.get("created_at", "")),
        "filename": "_".join(context_entry.get("file_key", "").split("_")[1:]) if context_entry.get("file_key") else "",
    }

    if context_entry.get("is_tabular") and context_entry.get("file_key"):
        try:
            file_obj = minio_client.get_object("context-files", context_entry["file_key"])
            file_content = file_obj.read()
            if context_entry["file_key"].endswith(".csv"):
                table_data = extract_table_from_csv(file_content)
            else:
                table_data = extract_table_from_excel(file_content)
            
            if table_data:
                response["structured_data"] = {
                    "schema": table_data.get("schema", {}),
                    "sample": table_data.get("sample", []),
                    "shape": table_data.get("shape", ())
                }
        except Exception as e:
            logger.warning(f"Failed to load structured data from MinIO for context {context_id}: {e}")

    return response


@router.get("/agents/{agent_id}/context/{context_id}/ingested_content")
def get_ingested_content(agent_id: str, context_id: str, token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    if not ObjectId.is_valid(agent_id) or not ObjectId.is_valid(context_id):
        raise HTTPException(status_code=400, detail="Invalid ID format.")

    agent = agents_db.find_one({"_id": ObjectId(agent_id), "org": ObjectId(user["organization"])})
    if not agent or ObjectId(context_id) not in agent.get("context", []):
        raise HTTPException(status_code=404, detail="Context entry not found for this agent.")

    context_entry = knowledge_db.find_one({"_id": ObjectId(context_id), "org": ObjectId(user["organization"])})
    if not context_entry:
        raise HTTPException(status_code=404, detail="Context entry not found or permission denied.")

    response = {
        "ingested_content": context_entry.get("chunks", []),
        "is_tabular": context_entry.get("is_tabular", False)
    }

    if context_entry.get("is_tabular") and context_entry.get("file_key"):
        try:
            file_obj = minio_client.get_object("context-files", context_entry["file_key"])
            file_content = file_obj.read()
            if context_entry["file_key"].endswith(".csv"):
                table_data = extract_table_from_csv(file_content)
            else:
                table_data = extract_table_from_excel(file_content)

            if table_data:
                response["structured_data"] = {
                    "schema": table_data.get("schema", {}),
                    "sample": table_data.get("sample", []),
                    "shape": table_data.get("shape", ())
                }
        except Exception as e:
            logger.warning(f"Failed to load structured data from MinIO for context {context_id}: {e}")

    return response

@router.post("/agents/{agent_id}/context")
async def upload_context_file(
    agent_id: str,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    token: str = Depends(oauth2_scheme),
):
    try:
        logger.info(f"Starting upload_context_file for agent_id={agent_id}, filename={file.filename}")
        user = verify_token(token)
        if not ObjectId.is_valid(agent_id):
            logger.error("Invalid agent ID format.")
            raise HTTPException(status_code=400, detail="Invalid agent ID format.")
        agent = agents_db.find_one({
            "_id": ObjectId(agent_id),
            "org": ObjectId(user["organization"])
        })
        if not agent:
            logger.error(f"Agent {agent_id} not found or permission denied.")
            raise HTTPException(status_code=404, detail="Agent not found or you do not have permission to modify it.")
        content_type = file.content_type
        logger.info(f"Processing file of type {content_type}")
        file_content = await file.read()
        logger.info(f"Read file content for {file.filename} ({len(file_content)} bytes)")
        file_key = f"context_files/{str(ObjectId())}_{file.filename}"
        minio_client.put_object(
            bucket_name="context-files",
            object_name=file_key,
            data=io.BytesIO(file_content),
            length=len(file_content),
            content_type=content_type
        )
        logger.info(f"Saved file to MinIO with key {file_key}")
        background_tasks.add_task(
            process_context_embedding,
            agent_id,
            ObjectId(user["organization"]),
            file_content,
            file_key,
            file.filename,
            content_type,
            logger
        )
        return JSONResponse(
            status_code=202,
            content={
                "message": "File uploaded. Starting background processing.",
                "file_key": file_key
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"An error occurred while uploading the file for agent_id={agent_id}, filename={file.filename}")
        raise HTTPException(status_code=500, detail=f"An error occurred while uploading the file: {str(e)}")

@router.delete("/agents/{agent_id}/context/{context_id}")
def delete_context_entry(agent_id: str, context_id: str, token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    if not ObjectId.is_valid(agent_id) or not ObjectId.is_valid(context_id):
        raise HTTPException(status_code=400, detail="Invalid ID format.")
    agent = agents_db.find_one({
        "_id": ObjectId(agent_id),
        "org": ObjectId(user["organization"])
    })
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found or you do not have permission to modify it.")
    if ObjectId(context_id) not in agent.get("context", []):
        raise HTTPException(status_code=404, detail="Context entry not found in this agent.")
    context_entry = knowledge_db.find_one({"_id": ObjectId(context_id), "org": ObjectId(user["organization"])})
    if not context_entry:
        raise HTTPException(status_code=404, detail="Context entry not found or you do not have permission to delete it.")
    file_key = context_entry.get("file_key")
    if file_key:
        try:
            minio_client.remove_object(bucket_name="context-files", object_name=file_key)
        except Exception:
            pass
    agents_db.update_one(
        {"_id": ObjectId(agent_id)},
        {"$pull": {"context": ObjectId(context_id)}}
    )
    result = knowledge_db.delete_one({"_id": ObjectId(context_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=500, detail="Failed to delete the context entry.")
    return {"message": "Context Entry Deleted successfully"}

@router.get("/agents/{agent_id}/context/{context_id}/download")
def download_context_file(agent_id: str, context_id: str, token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    if not ObjectId.is_valid(agent_id) or not ObjectId.is_valid(context_id):
        raise HTTPException(status_code=400, detail="Invalid ID format.")
    agent = agents_db.find_one({
        "_id": ObjectId(agent_id),
        "org": ObjectId(user["organization"])
    })
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found or you do not have permission to access it.")
    if ObjectId(context_id) not in agent.get("context", []):
        raise HTTPException(status_code=404, detail="Context entry not found in this agent.")
    context_entry = knowledge_db.find_one({"_id": ObjectId(context_id), "org": ObjectId(user["organization"])})
    if not context_entry:
        raise HTTPException(status_code=404, detail="Context entry not found or you do not have permission to access it.")
    file_key = context_entry.get("file_key")
    if not file_key:
        raise HTTPException(status_code=404, detail="No file associated with this context entry.")
    try:
        presigned_url = minio_client.presigned_get_object(bucket_name="context-files", object_name=file_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate download URL: {str(e)}")
    return {
        "download_url": presigned_url,
        "is_tabular": context_entry.get("is_tabular", False),
    }