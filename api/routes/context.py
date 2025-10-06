from fastapi import Depends, APIRouter, HTTPException, UploadFile, File, status
from fastapi.responses import JSONResponse
from bson import ObjectId

import io
import json
import logging

from api.embed import embed, save_embedding, get_embeddings
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
            entry = knowledge_db.find_one({"_id": cid, "org": ObjectId(user["organization"])})
            if entry:
                context_entries.append({
                    "context_id": str(entry["_id"]),
                    "file_key": entry.get("file_key"),
                    "is_tabular": entry.get("is_tabular", False),
                    "structured_data": entry.get("structured_data"),
                    "created_at": str(entry.get("created_at", "")),
                    "filename": entry.get("file_key", "").split("_", 1)[-1] if entry.get("file_key") else "",
                })
        logger.info(f"Listed {len(context_entries)} context entries for agent {agent_id}.")
        return {"context_entries": context_entries}
    except Exception as e:
        logger.exception(f"Failed to list context entries for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list context entries: {str(e)}")

@router.get("/agents/{agent_id}/context/{context_id}")
def get_context_entry(agent_id: str, context_id: str, token: str = Depends(oauth2_scheme)):
    try:
        user = verify_token(token)
        if not ObjectId.is_valid(agent_id) or not ObjectId.is_valid(context_id):
            raise HTTPException(status_code=400, detail="Invalid ID format.")
        agent = agents_db.find_one({"_id": ObjectId(agent_id), "org": ObjectId(user["organization"])})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found or you do not have permission to view it.")
        if ObjectId(context_id) not in agent.get("context", []):
            raise HTTPException(status_code=404, detail="Context entry not found in this agent.")
        context_entry = knowledge_db.find_one({"_id": ObjectId(context_id), "org": ObjectId(user["organization"])})
        if not context_entry:
            raise HTTPException(status_code=404, detail="Context entry not found or you do not have permission to view it.")
        content = get_embeddings(ObjectId(context_id))
        if not content:
            raise HTTPException(status_code=404, detail="No embeddings found for context entry.")
        content['is_tabular'] = context_entry.get("is_tabular", False)
        content['structured_data'] = context_entry.get("structured_data", None)
        logger.info(f"Retrieved context entry {context_id} for agent {agent_id}.")
        return content
    except Exception as e:
        logger.exception(f"Failed to retrieve context entry {context_id} for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve context entry: {str(e)}")

@router.get("/agents/{agent_id}/context/{context_id}/ingested_content")
def get_ingested_content(agent_id: str, context_id: str, token: str = Depends(oauth2_scheme)):
    try:
        user = verify_token(token)
        if not ObjectId.is_valid(agent_id) or not ObjectId.is_valid(context_id):
            raise HTTPException(status_code=400, detail="Invalid ID format.")
        agent = agents_db.find_one({"_id": ObjectId(agent_id), "org": ObjectId(user["organization"])})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found or you do not have permission to view it.")
        if ObjectId(context_id) not in agent.get("context", []):
            raise HTTPException(status_code=404, detail="Context entry not found in this agent.")
        context_entry = knowledge_db.find_one({"_id": ObjectId(context_id), "org": ObjectId(user["organization"])})
        if not context_entry:
            raise HTTPException(status_code=404, detail="Context entry not found or you do not have permission to view it.")
        logger.info(f"Retrieved ingested content for context entry {context_id}.")
        return {
            "ingested_content": context_entry.get("chunks", []),
            "is_tabular": context_entry.get("is_tabular", False),
            "structured_data": context_entry.get("structured_data", None),
        }
    except Exception as e:
        logger.exception(f"Failed to retrieve ingested content for context entry {context_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve ingested content: {str(e)}")

@router.post("/agents/{agent_id}/context")
async def upload_context_file(agent_id: str, file: UploadFile = File(...), token: str = Depends(oauth2_scheme)):
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
        is_tabular = False
        structured_data = None
        if content_type == "application/pdf":
            text = extract_text_from_pdf(file_content)
            if not text.strip():
                logger.error("No extractable text in PDF.")
                raise HTTPException(status_code=400, detail="The uploaded document contains no extractable text.")
            chunks_with_embeddings = embed(text)
            logger.info(f"Generated embeddings for PDF: {len(chunks_with_embeddings)} chunks")
            if not chunks_with_embeddings:
                logger.error("Failed to generate embeddings for PDF.")
                raise HTTPException(status_code=500, detail="Failed to generate embeddings for the document.")
            file_key = f"context_files/{str(ObjectId())}_{file.filename}"
            minio_client.put_object(
                bucket_name="context-files",
                object_name=file_key,
                data=io.BytesIO(file_content),
                length=len(file_content),
                content_type=content_type
            )
            logger.info(f"Saved PDF to MinIO with key {file_key}")
            context_id = save_embedding(chunks_with_embeddings, ObjectId(user["organization"]))
            logger.info(f"Saved PDF embeddings to DB with context_id={context_id}")
            knowledge_db.update_one(
                {"_id": context_id},
                {"$set": {"file_key": file_key, "is_tabular": False, "structured_data": None}}
            )
            logger.info(f"Updated knowledge_db for PDF context {context_id}")
        elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            text = extract_text_from_docx(file_content)
            if not text.strip():
                logger.error("No extractable text in DOCX.")
                raise HTTPException(status_code=400, detail="The uploaded document contains no extractable text.")
            chunks_with_embeddings = embed(text)
            logger.info(f"Generated embeddings for DOCX: {len(chunks_with_embeddings)} chunks")
            if not chunks_with_embeddings:
                logger.error("Failed to generate embeddings for DOCX.")
                raise HTTPException(status_code=500, detail="Failed to generate embeddings for the document.")
            file_key = f"context_files/{str(ObjectId())}_{file.filename}"
            minio_client.put_object(
                bucket_name="context-files",
                object_name=file_key,
                data=io.BytesIO(file_content),
                length=len(file_content),
                content_type=content_type
            )
            logger.info(f"Saved DOCX to MinIO with key {file_key}")
            context_id = save_embedding(chunks_with_embeddings, ObjectId(user["organization"]))
            logger.info(f"Saved DOCX embeddings to DB with context_id={context_id}")
            knowledge_db.update_one(
                {"_id": context_id},
                {"$set": {"file_key": file_key, "is_tabular": False, "structured_data": None}}
            )
            logger.info(f"Updated knowledge_db for DOCX context {context_id}")
        elif content_type == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
            logger.error("PowerPoint upload not supported.")
            raise HTTPException(status_code=400, detail="Support for PowerPoint not implemented yet.")
        elif content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            table_data = extract_table_from_excel(file_content)
            if not table_data:
                logger.error("No extractable table data in Excel.")
                raise HTTPException(status_code=400, detail="The uploaded Excel document contains no extractable table data.")
            summary_text = f"Table with schema: {json.dumps(table_data.get('schema', {}))}, shape: {table_data.get('shape', '')}"
            chunks_with_embeddings = embed(summary_text)
            logger.info(f"Generated embeddings for Excel summary: {len(chunks_with_embeddings)} chunks")
            if not chunks_with_embeddings:
                logger.error("Failed to generate embeddings for Excel summary.")
                raise HTTPException(status_code=500, detail="Failed to generate embeddings for the document summary.")
            file_key = f"context_files/{str(ObjectId())}_{file.filename}"
            minio_client.put_object(
                bucket_name="context-files",
                object_name=file_key,
                data=io.BytesIO(file_content),
                length=len(file_content),
                content_type=content_type
            )
            logger.info(f"Saved Excel to MinIO with key {file_key}")
            context_id = save_embedding(chunks_with_embeddings, ObjectId(user["organization"]))
            logger.info(f"Saved Excel embeddings to DB with context_id={context_id}")
            is_tabular = True
            structured_data = table_data
            knowledge_db.update_one(
                {"_id": context_id},
                {"$set": {"file_key": file_key, "is_tabular": True, "structured_data": table_data}}
            )
            logger.info(f"Updated knowledge_db for Excel context {context_id}")
        elif content_type == "text/csv":
            table_data = extract_table_from_csv(file_content)
            if not table_data:
                logger.error("No extractable table data in CSV.")
                raise HTTPException(status_code=400, detail="The uploaded CSV document contains no extractable table data.")
            summary_text = f"Table with schema: {json.dumps(table_data.get('schema', {}))}, shape: {table_data.get('shape', '')}"
            chunks_with_embeddings = embed(summary_text)
            logger.info(f"Generated embeddings for CSV summary: {len(chunks_with_embeddings)} chunks")
            if not chunks_with_embeddings:
                logger.error("Failed to generate embeddings for CSV summary.")
                raise HTTPException(status_code=500, detail="Failed to generate embeddings for the document summary.")
            file_key = f"context_files/{str(ObjectId())}_{file.filename}"
            minio_client.put_object(
                bucket_name="context-files",
                object_name=file_key,
                data=io.BytesIO(file_content),
                length=len(file_content),
                content_type=content_type
            )
            logger.info(f"Saved CSV to MinIO with key {file_key}")
            context_id = save_embedding(chunks_with_embeddings, ObjectId(user["organization"]))
            logger.info(f"Saved CSV embeddings to DB with context_id={context_id}")
            is_tabular = True
            structured_data = table_data
            knowledge_db.update_one(
                {"_id": context_id},
                {"$set": {"file_key": file_key, "is_tabular": True, "structured_data": table_data}}
            )
            logger.info(f"Updated knowledge_db for CSV context {context_id}")
        else:
            logger.error(f"Unsupported file type: {content_type}")
            raise HTTPException(status_code=400, detail="Unsupported file type.")
        agents_db.update_one(
            {"_id": ObjectId(agent_id)},
            {"$push": {"context": context_id}}
        )
        logger.info(f"Updated agent {agent_id} with new context {context_id}")
        logger.info(f"Returning success response for context_id={context_id}")
        return JSONResponse(
            status_code=201,
            content={
                "message": "Context uploaded and processed successfully.",
                "context_id": str(context_id),
                "is_tabular": is_tabular,
                "structured_data": structured_data,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"An error occurred while processing the file for agent_id={agent_id}, filename={file.filename}")
        raise HTTPException(status_code=500, detail=f"An error occurred while processing the file: {str(e)}")
    
@router.put("/agents/{agent_id}/context/{context_id}")
async def reupload_context_file(
    agent_id: str,
    context_id: str,
    file: UploadFile = File(...),
    token: str = Depends(oauth2_scheme)
):
    try:
        logger.info(f"Starting reupload_context_file for agent_id={agent_id}, context_id={context_id}, filename={file.filename}")
        user = verify_token(token)
        if not ObjectId.is_valid(agent_id) or not ObjectId.is_valid(context_id):
            logger.error("Invalid agent ID or context ID format.")
            raise HTTPException(status_code=400, detail="Invalid ID format.")

        agent = agents_db.find_one({
            "_id": ObjectId(agent_id),
            "org": ObjectId(user["organization"])
        })
        if not agent:
            logger.error(f"Agent {agent_id} not found or permission denied.")
            raise HTTPException(status_code=404, detail="Agent not found or you do not have permission to modify it.")

        if ObjectId(context_id) not in agent.get("context", []):
            logger.error(f"Context entry {context_id} not found in agent {agent_id}.")
            raise HTTPException(status_code=404, detail="Context entry not found in this agent.")

        context_entry = knowledge_db.find_one({"_id": ObjectId(context_id), "org": ObjectId(user["organization"])})
        if not context_entry:
            logger.error(f"Context entry {context_id} not found in DB or permission denied.")
            raise HTTPException(status_code=404, detail="Context entry not found or you do not have permission to modify it.")

        old_file_key = context_entry.get("file_key")
        content_type = file.content_type
        file_content = await file.read()
        logger.info(f"Read file content for {file.filename} ({len(file_content)} bytes)")

        is_tabular = False
        structured_data = None

        if content_type == "application/pdf":
            text = extract_text_from_pdf(file_content)
            if not text.strip():
                logger.error("No extractable text in PDF.")
                raise HTTPException(status_code=400, detail="The uploaded document contains no extractable text.")
            chunks_with_embeddings = embed(text)
            logger.info(f"Generated {len(chunks_with_embeddings)} embeddings for PDF")
            if old_file_key:
                try:
                    minio_client.remove_object(bucket_name="context-files", object_name=old_file_key)
                    logger.info(f"Removed old PDF file from MinIO: {old_file_key}")
                except Exception as e:
                    logger.warning(f"Failed to remove old file {old_file_key}: {e}")
            new_file_key = f"context_files/{str(ObjectId())}_{file.filename}"
            minio_client.put_object(
                bucket_name="context-files",
                object_name=new_file_key,
                data=io.BytesIO(file_content),
                length=len(file_content),
                content_type=content_type
            )
            knowledge_db.update_one(
                {"_id": ObjectId(context_id)},
                {"$set": {"file_key": new_file_key, "chunks": [chunk for chunk in chunks_with_embeddings], "is_tabular": False, "structured_data": None}}
            )
            logger.info(f"Reuploaded PDF context {context_id} and updated DB")

        elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            text = extract_text_from_docx(file_content)
            if not text.strip():
                logger.error("No extractable text in DOCX.")
                raise HTTPException(status_code=400, detail="The uploaded document contains no extractable text.")
            chunks_with_embeddings = embed(text)
            logger.info(f"Generated {len(chunks_with_embeddings)} embeddings for DOCX")
            if old_file_key:
                try:
                    minio_client.remove_object(bucket_name="context-files", object_name=old_file_key)
                    logger.info(f"Removed old DOCX file from MinIO: {old_file_key}")
                except Exception as e:
                    logger.warning(f"Failed to remove old file {old_file_key}: {e}")
            new_file_key = f"context_files/{str(ObjectId())}_{file.filename}"
            minio_client.put_object(
                bucket_name="context-files",
                object_name=new_file_key,
                data=io.BytesIO(file_content),
                length=len(file_content),
                content_type=content_type
            )
            knowledge_db.update_one(
                {"_id": ObjectId(context_id)},
                {"$set": {"file_key": new_file_key, "chunks": [chunk for chunk in chunks_with_embeddings], "is_tabular": False, "structured_data": None}}
            )
            logger.info(f"Reuploaded DOCX context {context_id} and updated DB")

        elif content_type == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
            logger.error("PowerPoint upload not supported.")
            raise HTTPException(status_code=400, detail="Support for PowerPoint not implemented yet.")

        elif content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            table_data = extract_table_from_excel(file_content)
            if not table_data:
                logger.error("No extractable table data in Excel.")
                raise HTTPException(status_code=400, detail="The uploaded Excel document contains no extractable table data.")
            summary_text = f"Table with schema: {json.dumps(table_data.get('schema', {}))}, shape: {table_data.get('shape', '')}"
            chunks_with_embeddings = embed(summary_text)
            logger.info(f"Generated {len(chunks_with_embeddings)} embeddings for Excel summary")
            if old_file_key:
                try:
                    minio_client.remove_object(bucket_name="context-files", object_name=old_file_key)
                    logger.info(f"Removed old Excel file from MinIO: {old_file_key}")
                except Exception as e:
                    logger.warning(f"Failed to remove old file {old_file_key}: {e}")
            new_file_key = f"context_files/{str(ObjectId())}_{file.filename}"
            minio_client.put_object(
                bucket_name="context-files",
                object_name=new_file_key,
                data=io.BytesIO(file_content),
                length=len(file_content),
                content_type=content_type
            )
            is_tabular = True
            structured_data = table_data
            knowledge_db.update_one(
                {"_id": ObjectId(context_id)},
                {"$set": {"file_key": new_file_key, "chunks": [chunk for chunk in chunks_with_embeddings], "is_tabular": True, "structured_data": table_data}}
            )
            logger.info(f"Reuploaded Excel context {context_id} and updated DB")

        elif content_type == "text/csv":
            table_data = extract_table_from_csv(file_content)
            if not table_data:
                logger.error("No extractable table data in CSV.")
                raise HTTPException(status_code=400, detail="The uploaded CSV document contains no extractable table data.")
            summary_text = f"Table with schema: {json.dumps(table_data.get('schema', {}))}, shape: {table_data.get('shape', '')}"
            chunks_with_embeddings = embed(summary_text)
            logger.info(f"Generated {len(chunks_with_embeddings)} embeddings for CSV summary")
            if old_file_key:
                try:
                    minio_client.remove_object(bucket_name="context-files", object_name=old_file_key)
                    logger.info(f"Removed old CSV file from MinIO: {old_file_key}")
                except Exception as e:
                    logger.warning(f"Failed to remove old file {old_file_key}: {e}")
            new_file_key = f"context_files/{str(ObjectId())}_{file.filename}"
            minio_client.put_object(
                bucket_name="context-files",
                object_name=new_file_key,
                data=io.BytesIO(file_content),
                length=len(file_content),
                content_type=content_type
            )
            is_tabular = True
            structured_data = table_data
            knowledge_db.update_one(
                {"_id": ObjectId(context_id)},
                {"$set": {"file_key": new_file_key, "chunks": [chunk for chunk in chunks_with_embeddings], "is_tabular": True, "structured_data": table_data}}
            )
            logger.info(f"Reuploaded CSV context {context_id} and updated DB")

        else:
            logger.error(f"Unsupported file type: {content_type}")
            raise HTTPException(status_code=400, detail="Unsupported file type.")

        logger.info(f"Returning success response for reuploaded context {context_id}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Context file reuploaded and processed successfully.",
                "context_id": str(context_id),
                "is_tabular": is_tabular,
                "structured_data": structured_data,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"An error occurred while reuploading the file for agent_id={agent_id}, context_id={context_id}, filename={file.filename}")
        raise HTTPException(status_code=500, detail=f"An error occurred while processing the file: {str(e)}")
    
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
        "structured_data": context_entry.get("structured_data", None),
    }