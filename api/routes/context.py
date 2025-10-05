from fastapi import Depends, APIRouter, HTTPException, UploadFile, File, status
from fastapi.responses import JSONResponse
from bson import ObjectId
import io
import json
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

@router.get("/agents/{agent_id}/context")
def list_context_entries(agent_id: str, token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    if not ObjectId.is_valid(agent_id):
        raise HTTPException(status_code=400, detail="Invalid agent ID format.")
    agent = agents_db.find_one({
        "_id": ObjectId(agent_id),
        "org": ObjectId(user["organization"])
    })
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
    return {"context_entries": context_entries}

@router.get("/agents/{agent_id}/context/{context_id}")
def get_context_entry(agent_id: str, context_id: str, token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    if not ObjectId.is_valid(agent_id) or not ObjectId.is_valid(context_id):
        raise HTTPException(status_code=400, detail="Invalid ID format.")
    agent = agents_db.find_one({
        "_id": ObjectId(agent_id),
        "org": ObjectId(user["organization"])
    })
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found or you do not have permission to view it.")
    if ObjectId(context_id) not in agent.get("context", []):
        raise HTTPException(status_code=404, detail="Context entry not found in this agent.")
    context_entry = knowledge_db.find_one({"_id": ObjectId(context_id), "org": ObjectId(user["organization"])})
    if not context_entry:
        raise HTTPException(status_code=404, detail="Context entry not found or you do not have permission to view it.")
    content = get_embeddings(ObjectId(context_id))
    if not content:
        raise HTTPException(status_code=404, detail="Context entry not found or you do not have permission to view it.")
    # Add tabular/structured data info if present
    content['is_tabular'] = context_entry.get("is_tabular", False)
    content['structured_data'] = context_entry.get("structured_data", None)
    return content

@router.get("/agents/{agent_id}/context/{context_id}/ingested_content")
def get_ingested_content(agent_id: str, context_id: str, token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    if not ObjectId.is_valid(agent_id) or not ObjectId.is_valid(context_id):
        raise HTTPException(status_code=400, detail="Invalid ID format.")
    agent = agents_db.find_one({
        "_id": ObjectId(agent_id),
        "org": ObjectId(user["organization"])
    })
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found or you do not have permission to view it.")
    if ObjectId(context_id) not in agent.get("context", []):
        raise HTTPException(status_code=404, detail="Context entry not found in this agent.")
    context_entry = knowledge_db.find_one({"_id": ObjectId(context_id), "org": ObjectId(user["organization"])})
    if not context_entry:
        raise HTTPException(status_code=404, detail="Context entry not found or you do not have permission to view it.")
    return {
        "ingested_content": context_entry.get("chunks", []),
        "is_tabular": context_entry.get("is_tabular", False),
        "structured_data": context_entry.get("structured_data", None),
    }

@router.post("/agents/{agent_id}/context")
async def upload_context_file(agent_id: str, file: UploadFile = File(...), token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    if not ObjectId.is_valid(agent_id):
        raise HTTPException(status_code=400, detail="Invalid agent ID format.")
    agent = agents_db.find_one({
        "_id": ObjectId(agent_id),
        "org": ObjectId(user["organization"])
    })
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found or you do not have permission to modify it.")
    content_type = file.content_type
    try:
        file_content = await file.read()
        is_tabular = False
        structured_data = None
        if content_type == "application/pdf":
            text = extract_text_from_pdf(file_content)
            if not text.strip():
                raise HTTPException(status_code=400, detail="The uploaded document contains no extractable text.")
            chunks_with_embeddings = embed(text)
            if not chunks_with_embeddings:
                raise HTTPException(status_code=500, detail="Failed to generate embeddings for the document.")
            file_key = f"context_files/{str(ObjectId())}_{file.filename}"
            minio_client.put_object(
                bucket_name="context-files",
                object_name=file_key,
                data=io.BytesIO(file_content),
                length=len(file_content),
                content_type=content_type
            )
            context_id = save_embedding(chunks_with_embeddings, ObjectId(user["organization"]))
            knowledge_db.update_one(
                {"_id": context_id},
                {"$set": {"file_key": file_key, "is_tabular": False, "structured_data": None}}
            )
        elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            text = extract_text_from_docx(file_content)
            if not text.strip():
                raise HTTPException(status_code=400, detail="The uploaded document contains no extractable text.")
            chunks_with_embeddings = embed(text)
            if not chunks_with_embeddings:
                raise HTTPException(status_code=500, detail="Failed to generate embeddings for the document.")
            file_key = f"context_files/{str(ObjectId())}_{file.filename}"
            minio_client.put_object(
                bucket_name="context-files",
                object_name=file_key,
                data=io.BytesIO(file_content),
                length=len(file_content),
                content_type=content_type
            )
            context_id = save_embedding(chunks_with_embeddings, ObjectId(user["organization"]))
            knowledge_db.update_one(
                {"_id": context_id},
                {"$set": {"file_key": file_key, "is_tabular": False, "structured_data": None}}
            )
        elif content_type == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
            raise HTTPException(status_code=400, detail="Support for PowerPoint not implemented yet.")
        elif content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            table_data = extract_table_from_excel(file_content)
            if not table_data:
                raise HTTPException(status_code=400, detail="The uploaded Excel document contains no extractable table data.")
            summary_text = f"Table with schema: {json.dumps(table_data.get('schema', {}))}, shape: {table_data.get('shape', '')}"
            chunks_with_embeddings = embed(summary_text)
            if not chunks_with_embeddings:
                raise HTTPException(status_code=500, detail="Failed to generate embeddings for the document summary.")
            file_key = f"context_files/{str(ObjectId())}_{file.filename}"
            minio_client.put_object(
                bucket_name="context-files",
                object_name=file_key,
                data=io.BytesIO(file_content),
                length=len(file_content),
                content_type=content_type
            )
            context_id = save_embedding(chunks_with_embeddings, ObjectId(user["organization"]))
            is_tabular = True
            structured_data = table_data
            knowledge_db.update_one(
                {"_id": context_id},
                {"$set": {"file_key": file_key, "is_tabular": True, "structured_data": table_data}}
            )
        elif content_type == "text/csv":
            table_data = extract_table_from_csv(file_content)
            if not table_data:
                raise HTTPException(status_code=400, detail="The uploaded CSV document contains no extractable table data.")
            summary_text = f"Table with schema: {json.dumps(table_data.get('schema', {}))}, shape: {table_data.get('shape', '')}"
            chunks_with_embeddings = embed(summary_text)
            if not chunks_with_embeddings:
                raise HTTPException(status_code=500, detail="Failed to generate embeddings for the document summary.")
            file_key = f"context_files/{str(ObjectId())}_{file.filename}"
            minio_client.put_object(
                bucket_name="context-files",
                object_name=file_key,
                data=io.BytesIO(file_content),
                length=len(file_content),
                content_type=content_type
            )
            context_id = save_embedding(chunks_with_embeddings, ObjectId(user["organization"]))
            is_tabular = True
            structured_data = table_data
            knowledge_db.update_one(
                {"_id": context_id},
                {"$set": {"file_key": file_key, "is_tabular": True, "structured_data": table_data}}
            )
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type.")
        agents_db.update_one(
            {"_id": ObjectId(agent_id)},
            {"$push": {"context": context_id}}
        )
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
        raise HTTPException(status_code=500, detail=f"An error occurred while processing the file: {str(e)}")
    
@router.put("/agents/{agent_id}/context/{context_id}")
async def reupload_context_file(
    agent_id: str,
    context_id: str,
    file: UploadFile = File(...),
    token: str = Depends(oauth2_scheme)
):
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
        raise HTTPException(status_code=404, detail="Context entry not found or you do not have permission to modify it.")
    old_file_key = context_entry.get("file_key")
    content_type = file.content_type
    try:
        file_content = await file.read()
        is_tabular = False
        structured_data = None
        if content_type == "application/pdf":
            text = extract_text_from_pdf(file_content)
            if not text.strip():
                raise HTTPException(status_code=400, detail="The uploaded document contains no extractable text.")
            chunks_with_embeddings = embed(text)
            if not chunks_with_embeddings:
                raise HTTPException(status_code=500, detail="Failed to generate embeddings for the document.")
            if old_file_key:
                try:
                    minio_client.remove_object(bucket_name="context-files", object_name=old_file_key)
                except Exception:
                    pass
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
                {"$set": {
                    "file_key": new_file_key,
                    "chunks": [chunk for chunk in chunks_with_embeddings],
                    "is_tabular": False,
                    "structured_data": None
                }}
            )
        elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            text = extract_text_from_docx(file_content)
            if not text.strip():
                raise HTTPException(status_code=400, detail="The uploaded document contains no extractable text.")
            chunks_with_embeddings = embed(text)
            if not chunks_with_embeddings:
                raise HTTPException(status_code=500, detail="Failed to generate embeddings for the document.")
            if old_file_key:
                try:
                    minio_client.remove_object(bucket_name="context-files", object_name=old_file_key)
                except Exception:
                    pass
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
                {"$set": {
                    "file_key": new_file_key,
                    "chunks": [chunk for chunk in chunks_with_embeddings],
                    "is_tabular": False,
                    "structured_data": None
                }}
            )
        elif content_type == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
            raise HTTPException(status_code=400, detail="Support for PowerPoint not implemented yet.")
        elif content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            table_data = extract_table_from_excel(file_content)
            if not table_data:
                raise HTTPException(status_code=400, detail="The uploaded Excel document contains no extractable table data.")
            summary_text = f"Table with schema: {json.dumps(table_data.get('schema', {}))}, shape: {table_data.get('shape', '')}"
            chunks_with_embeddings = embed(summary_text)
            if not chunks_with_embeddings:
                raise HTTPException(status_code=500, detail="Failed to generate embeddings for the document summary.")
            if old_file_key:
                try:
                    minio_client.remove_object(bucket_name="context-files", object_name=old_file_key)
                except Exception:
                    pass
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
                {"$set": {
                    "file_key": new_file_key,
                    "chunks": [chunk for chunk in chunks_with_embeddings],
                    "is_tabular": True,
                    "structured_data": table_data
                }}
            )
        elif content_type == "text/csv":
            table_data = extract_table_from_csv(file_content)
            if not table_data:
                raise HTTPException(status_code=400, detail="The uploaded CSV document contains no extractable table data.")
            summary_text = f"Table with schema: {json.dumps(table_data.get('schema', {}))}, shape: {table_data.get('shape', '')}"
            chunks_with_embeddings = embed(summary_text)
            if not chunks_with_embeddings:
                raise HTTPException(status_code=500, detail="Failed to generate embeddings for the document summary.")
            if old_file_key:
                try:
                    minio_client.remove_object(bucket_name="context-files", object_name=old_file_key)
                except Exception:
                    pass
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
                {"$set": {
                    "file_key": new_file_key,
                    "chunks": [chunk for chunk in chunks_with_embeddings],
                    "is_tabular": True,
                    "structured_data": table_data
                }}
            )
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type.")
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