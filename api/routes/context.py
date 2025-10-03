from fastapi import Depends, APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from bson import ObjectId

from api.embed import embed, save_embedding, get_embeddings, similarity, knowledge_db
from api.database import agents_db
from api.auth import verify_token, oauth2_scheme
from api.schemas.context import Context

import PyPDF2, io

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
    
    context = agent["context"]

    return Context(**context)
