from fastapi import Depends, APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from bson import ObjectId

from api.embed import embed, save_embedding, get_embeddings, similarity, knowledge_db
from api.database import connectors_db
from api.auth import verify_token, oauth2_scheme

import PyPDF2, io

router = APIRouter(tags=["Context Management"])

@router.post("/connectors/{connector_id}/upload", status_code=201)
async def upload_pdf(connector_id: str, file: UploadFile = File(...), token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    org_id = ObjectId(user["organization"])

    if not ObjectId.is_valid(connector_id):
        raise HTTPException(status_code=400, detail="Invalid connector ID format.")
    
    connector = connectors_db.find_one({"_id": ObjectId(connector_id), "org": org_id})
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found or you do not have permission to use it.")
    
    if connector.get("settings") and connector["settings"].get("document_id"):
        raise HTTPException(status_code=400, detail="This connector already has a document associated with it. Please create a new connector for this file.")

    if connector.get("connector_type") == "source_pdf":
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="Uploaded file is not a valid PDF")
        
        try:
            contents = await file.read()
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(contents))
            text = "".join(page.extract_text() or "" for page in pdf_reader.pages)
            if not text.strip():
                raise HTTPException(status_code=400, detail="No text extracted from the PDF")

            chunks_with_embeddings = embed(text, chunk_size=1000, overlap=200)
            if not chunks_with_embeddings:
                raise HTTPException(status_code=500, detail="Failed to generate text chunks or embeddings.")
            
            document_id = save_embedding(chunks_with_embeddings, org_id)
            if not document_id:
                raise HTTPException(status_code=500, detail="Failed to save document and embeddings to the database.")
            
            update_result = connectors_db.update_one(
                {"_id": ObjectId(connector_id)},
                {"$set": {"settings": {"document_id": str(document_id)}}}
            )
            
            if update_result.matched_count == 0:
                knowledge_db.delete_one({"_id": document_id})
                raise HTTPException(status_code=500, detail="Failed to link document to connector. The upload has been rolled back.")
            
            return JSONResponse(
                content={"document_id": str(document_id), "chunks_saved": len(chunks_with_embeddings)},
                status_code=201
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred during PDF upload: {str(e)}")
        
    elif connector.get("connector_type") == "source_txt":
        if file.content_type != "text/plain":
            raise HTTPException(status_code=400, detail="Uploaded file is not a valid TXT")
        
        try:
            contents = await file.read()
            text = contents.decode('utf-8')
            if not text.strip():
                raise HTTPException(status_code=400, detail="No text extracted from the TXT file")

            chunks_with_embeddings = embed(text, chunk_size=1000, overlap=200)
            if not chunks_with_embeddings:
                raise HTTPException(status_code=500, detail="Failed to generate text chunks or embeddings.")
            
            document_id = save_embedding(chunks_with_embeddings, org_id)
            if not document_id:
                raise HTTPException(status_code=500, detail="Failed to save document and embeddings to the database.")
            
            update_result = connectors_db.update_one(
                {"_id": ObjectId(connector_id)},
                {"$set": {"settings": {"document_id": str(document_id)}}}
            )
            if update_result.matched_count == 0:
                knowledge_db.delete_one({"_id": document_id})
                raise HTTPException(status_code=500, detail="Failed to link document to connector. The upload has been rolled back.")
            
            return JSONResponse(
                content={"document_id": str(document_id), "chunks_saved": len(chunks_with_embeddings)},
                status_code=201
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred during TXT upload: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail="Unsupported connector type for file upload")