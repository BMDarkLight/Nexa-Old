from fastapi import Depends, APIRouter, HTTPException, UploadFile, File, status
from fastapi.responses import JSONResponse
from bson import ObjectId

from api.embed import embed, save_embedding, get_embeddings, similarity
from api.database import agents_db, knowledge_db, minio_client
from api.auth import verify_token, oauth2_scheme
from api.schemas.context import Context

import PyPDF2, io
import docx

router = APIRouter(tags=["Context Management"])

def extract_text_from_pdf(file_content: bytes) -> str:
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    return text

def extract_text_from_docx(file_content: bytes) -> str:
    doc = docx.Document(io.BytesIO(file_content))
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

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
    
    context = agent["context"]

    return Context(**context)

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
    
    if ObjectId(context_id) not in agent["context"]:
        raise HTTPException(status_code=404, detail="Context entry not found in this agent.")
    
    content = get_embeddings(ObjectId(context_id))

    if not content:
        raise HTTPException(status_code=404, detail="Context entry not found or you do not have permission to view it.")
    
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
    
    if ObjectId(context_id) not in agent["context"]:
        raise HTTPException(status_code=404, detail="Context entry not found in this agent.")
    
    context_entry = knowledge_db.find_one({"_id": ObjectId(context_id), "org": ObjectId(user["organization"])})

    if not context_entry:
        raise HTTPException(status_code=404, detail="Context entry not found or you do not have permission to view it.")
    
    return {"ingested_content": context_entry.get("chunks", [])}

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

        if content_type == "application/pdf":
            text = extract_text_from_pdf(file_content)
        elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            text = extract_text_from_docx(file_content)
        elif content_type == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
            raise HTTPException(status_code=400, detail="Support for PowerPoint not implemented yet.")
        elif content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            raise HTTPException(status_code=400, detail="Support for Excel not implemented yet.")
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type.")
        
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
            {"$set": {"file_key": file_key}}
        )
        
        agents_db.update_one(
            {"_id": ObjectId(agent_id)},
            {"$push": {"context": context_id}}
        )
        
        return JSONResponse(status_code=201, content={"message": "Context uploaded and processed successfully.", "context_id": str(context_id)})
    
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

        if content_type == "application/pdf":
            text = extract_text_from_pdf(file_content)
        elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            text = extract_text_from_docx(file_content)
        elif content_type == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
            raise HTTPException(status_code=400, detail="Support for PowerPoint not implemented yet.")
        elif content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            raise HTTPException(status_code=400, detail="Support for Excel not implemented yet.")
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type.")

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
            {
                "$set": {
                    "file_key": new_file_key,
                    "chunks": [chunk for chunk in chunks_with_embeddings]
                }
            }
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Context file reuploaded and processed successfully.", "context_id": str(context_id)}
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
    
    if ObjectId(context_id) not in agent["context"]:
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
