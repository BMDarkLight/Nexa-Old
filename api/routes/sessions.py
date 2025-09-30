from fastapi import Depends, APIRouter, HTTPException, Request
from typing import List

from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage

from api.auth import oauth2_scheme, verify_token
from api.database import sessions_db

router = APIRouter(tags=["Sessions"])

@router.get("/sessions", response_model=List[dict])
def list_sessions(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        user = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
    sessions = list(sessions_db.find({"user_id": str(user["_id"])}, {"_id": 0}))

    for i, session in enumerate(sessions):
        if "chat_history" in session and len(session["chat_history"]) > 3: 
            title_generator = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3)

            chat_history = session["chat_history"]

            prompts = [
                SystemMessage("You are a title generator. You receive the users chat history in the chatbot and generate a short title based on it. The title should represent what is going on in the chat, the title shouldn't be flashy or trendy, just helpful and straight to the point. And generate the title in the same language as the chat history."),
            ]

            for entry in chat_history:
                prompts.append(HumanMessage(content=entry["user"]))
                prompts.append(AIMessage(content=entry["assistant"]))
            
            title = title_generator.invoke(prompts)

            sessions[i]["title"] = title.content

    return sessions

@router.get("/sessions/{session_id}", response_model=dict)
def get_session(session_id: str, token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        user = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
    session = sessions_db.find_one({"session_id": session_id, "user_id": str(user["_id"])}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if "chat_history" in session and len(session["chat_history"]) > 3: 
        title_generator = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3)

        chat_history = session["chat_history"]

        prompts = [
            SystemMessage("You are a title generator. You receive the users chat history in the chatbot and generate a short title based on it. The title should represent what is going on in the chat, the title shouldn't be flashy or trendy, just helpful and straight to the point. And generate the title in the same language as the chat history."),
        ]

        for entry in chat_history:
            prompts.append(HumanMessage(content=entry["user"]))
            prompts.append(AIMessage(content=entry["assistant"]))
        
        title = title_generator.invoke(prompts)

        session["title"] = title.content
    
    return session

@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        user = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
    result = sessions_db.delete_one({
        "session_id": session_id,
        "user_id": str(user["_id"])
    })

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"message": f"Session '{session_id}' deleted successfully"}