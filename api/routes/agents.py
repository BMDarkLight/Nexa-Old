from fastapi import BackgroundTasks, Depends, APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from bson import ObjectId
from typing import List

import datetime

from api.schemas.agents import QueryRequest, save_chat_history, update_chat_history_entry, replace_chat_history_from_point
from api.database import sessions_db, agents_db, connectors_db
from api.agent import get_agent_graph
from api.schemas.agents import Agent, AgentCreate, AgentUpdate
from api.auth import verify_token, oauth2_scheme


router = APIRouter(tags=["Agent"])

@router.post("/ask")
async def ask(
    query: QueryRequest,
    background_tasks: BackgroundTasks,
    token: str = Depends(oauth2_scheme)
):
    try:
        user = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

    if not query.query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    if not user.get("organization") and user.get("permission") != "sysadmin":
        raise HTTPException(status_code=403, detail="You do not belong to an organization.")

    agent_id_to_use = None
    if query.agent_id:
        if not ObjectId.is_valid(query.agent_id):
            raise HTTPException(status_code=400, detail="Invalid agent ID format.")
        agent_oid = ObjectId(query.agent_id)
        agent_query = {"_id": agent_oid}
        if user.get("permission") != "sysadmin":
            agent_query["org"] = ObjectId(user["organization"])
        agent_doc = agents_db.find_one(agent_query)
        if not agent_doc:
            raise HTTPException(status_code=404, detail="Agent not found or not accessible.")
        agent_id_to_use = str(agent_oid)

    import uuid
    session_id = query.session_id or str(uuid.uuid4())
    session = sessions_db.find_one({"session_id": session_id})
    if session and session.get("user_id") != str(user["_id"]):
        raise HTTPException(status_code=403, detail="Permission denied for this session.")
    chat_history = session.get("chat_history", []) if session else []
    org_id = user.get("organization")

    try:
        agent_graph = await get_agent_graph(
            question=query.query,
            organization_id=org_id,
            chat_history=chat_history,
            agent_id=agent_id_to_use
        )
    except Exception:
        async def error_response():
            yield "Sorry, there was an error processing your request. Please try again later."
        return StreamingResponse(error_response(), media_type="text/plain")

    graph = agent_graph["graph"]
    agent_name = agent_graph["final_agent_name"]
    agent_id_str = agent_graph["final_agent_id"]

    async def response_generator():
        yield f"[Agent: {agent_name} | Session: {session_id}]\n\n"

        full_answer = ""
        astream_input = {"messages": []}
        astream_input["messages"].append({
            "role": "system",
            "content": f"You are an AI agent built by user in Nexa AI platform. "
                       f"You are now operating as the agent named {agent_name}. "
                       f"Description: {agent_graph.get('description', 'No description provided')}."
        })
        for entry in chat_history:
            astream_input["messages"].append({"role": "user", "content": entry["user"]})
            astream_input["messages"].append({"role": "assistant", "content": entry["assistant"]})
        astream_input["messages"].append({"role": "user", "content": query.query})

        async for chunk in graph.astream(astream_input):
            content = ""

            # Case 1: AIMessage object
            if hasattr(chunk, "content"):
                content = chunk.content or ""

            # Case 2: LangGraph agent dict
            elif isinstance(chunk, dict):
                try:
                    agent_messages = chunk.get("agent", {}).get("messages", [])
                    if agent_messages:
                        last_msg = agent_messages[-1]
                        content = getattr(last_msg, "content", str(last_msg))
                except Exception:
                    content = str(chunk)

            # Fallback
            else:
                content = str(chunk)

            full_answer += content
            yield content

        # Save to DB
        background_tasks.add_task(
            save_chat_history,
            session_id=session_id,
            user_id=str(user["_id"]),
            chat_history=chat_history,
            query=query.query,
            answer=full_answer,
            agent_id=agent_id_str,
            agent_name=agent_name
        )

    return StreamingResponse(response_generator(), media_type="text/plain; charset=utf-8")

@router.post("/ask/regenerate/{message_num}")
async def regenerate(
    message_num: int,
    background_tasks: BackgroundTasks,
    request: Request,
    token: str = Depends(oauth2_scheme)
):
    data = await request.json()
    session_id = data.get("session_id")
    agent_id = data.get("agent_id")
    user = verify_token(token)
    session = sessions_db.find_one({"session_id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.get("user_id") != str(user["_id"]):
        raise HTTPException(status_code=403, detail="Permission denied for this session.")

    chat_history = session.get("chat_history", [])
    if message_num < 0 or message_num >= len(chat_history):
        raise HTTPException(status_code=400, detail="Invalid message number.")

    truncated_history = chat_history[:message_num]
    original_query = chat_history[message_num]['user']
    org_id = user.get("organization")

    try:
        agent_graph = await get_agent_graph(
            question=original_query,
            organization_id=org_id,
            chat_history=truncated_history,
            agent_id=agent_id
        )
    except Exception:
        async def error_response():
            yield "Sorry, there was an error processing your request. Please try again later."
        return StreamingResponse(error_response(), media_type="text/plain")

    graph = agent_graph["graph"]
    agent_name = agent_graph["final_agent_name"]
    agent_id_str = agent_graph["final_agent_id"]

    async def response_generator():
        yield f"[Agent: {agent_name} | Session: {session_id}]\n\n"

        full_answer = ""
        astream_input = {"messages": []}
        astream_input["messages"].append({
            "role": "system",
            "content": f"You are an AI agent built by user in Nexa AI platform. You are now operating as the agent named {agent_name}. Description: {agent_graph.get('description', 'No description provided')}."
        })
        for entry in truncated_history:
            astream_input["messages"].append({"role": "user", "content": entry["user"]})
            astream_input["messages"].append({"role": "assistant", "content": entry["assistant"]})
        astream_input["messages"].append({"role": "user", "content": original_query})
        async for chunk in graph.astream(astream_input):
            content = getattr(chunk, "content", None)
            if content is None and isinstance(chunk, dict):
                content = chunk.get("content", "")
            elif content is None:
                content = str(chunk)
            full_answer += content
            yield content

        background_tasks.add_task(
            replace_chat_history_from_point,
            session_id=session_id,
            user_id=str(user["_id"]),
            truncated_history=truncated_history,
            query=original_query,
            new_answer=full_answer,
            agent_id=agent_id_str,
            agent_name=agent_name
        )

    return StreamingResponse(response_generator(), media_type="text/plain")

@router.post("/ask/edit/{message_num}")
async def edit_message(
    message_num: int,
    background_tasks: BackgroundTasks,
    request: Request,
    token: str = Depends(oauth2_scheme)
):
    data = await request.json()
    query = data.get("query")
    session_id = data.get("session_id")
    agent_id = data.get("agent_id")
    user = verify_token(token)
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    session = sessions_db.find_one({"session_id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.get("user_id") != str(user["_id"]):
        raise HTTPException(status_code=403, detail="Permission denied for this session.")

    chat_history = session.get("chat_history", [])
    if message_num < 0 or message_num >= len(chat_history):
        raise HTTPException(status_code=400, detail="Invalid message number.")

    truncated_history = chat_history[:message_num]
    org_id = user.get("organization")

    try:
        agent_graph = await get_agent_graph(
            question=query,
            organization_id=org_id,
            chat_history=truncated_history,
            agent_id=agent_id
        )
    except Exception:
        async def error_response():
            yield "Sorry, there was an error processing your request. Please try again later."
        return StreamingResponse(error_response(), media_type="text/plain")

    graph = agent_graph["graph"]
    agent_name = agent_graph["final_agent_name"]
    agent_id_str = agent_graph["final_agent_id"]

    async def response_generator():
        yield f"[Agent: {agent_name} | Session: {session_id}]\n\n"

        full_answer = ""
        astream_input = {"messages": []}
        astream_input["messages"].append({
            "role": "system",
            "content": f"You are an AI agent built by user in Nexa AI platform. You are now operating as the agent named {agent_name}. Description: {agent_graph.get('description', 'No description provided')}."
        })
        for entry in truncated_history:
            astream_input["messages"].append({"role": "user", "content": entry["user"]})
            astream_input["messages"].append({"role": "assistant", "content": entry["assistant"]})
        astream_input["messages"].append({"role": "user", "content": query})
        async for chunk in graph.astream(astream_input):
            content = getattr(chunk, "content", None)
            if content is None and isinstance(chunk, dict):
                content = chunk.get("content", "")
            elif content is None:
                content = str(chunk)
            full_answer += content
            yield content

        background_tasks.add_task(
            update_chat_history_entry,
            session_id=session_id,
            message_num=message_num,
            new_query=query,
            new_answer=full_answer
        )

    return StreamingResponse(response_generator(), media_type="text/plain")

@router.get("/agents", response_model=List[Agent])
def list_agents(token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    if not user.get("organization"):
        return []
    
    agents_cursor = agents_db.find({"org": ObjectId(user["organization"])})
    return [Agent(**agent) for agent in agents_cursor]


@router.post("/agents", response_model=Agent)
def create_agent(agent: AgentCreate, token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    org_id = ObjectId(user["organization"])

    if user.get("permission") != "orgadmin":
        raise HTTPException(status_code=403, detail="Permission denied: Only organization admins can create agents.")

    if agent.connector_ids:
        for c_id in agent.connector_ids:
            if not connectors_db.find_one({"_id": c_id, "org": org_id}):
                raise HTTPException(status_code=404, detail=f"Connector with ID {c_id} not found in your organization.")

    agent_data = agent.model_dump(by_alias=True, exclude={"id"}) 
    
    agent_data["org"] = org_id
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    agent_data["created_at"] = now
    agent_data["updated_at"] = now

    result = agents_db.insert_one(agent_data)
    
    created_agent = agents_db.find_one({"_id": result.inserted_id})
    if not created_agent:
        raise HTTPException(status_code=500, detail="Failed to create and retrieve the agent.")
        
    return Agent(**created_agent)


@router.get("/agents/{agent_id}", response_model=Agent)
def get_agent(agent_id: str, token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    
    if not ObjectId.is_valid(agent_id):
        raise HTTPException(status_code=400, detail="Invalid agent ID format.")
    
    agent = agents_db.find_one({
        "_id": ObjectId(agent_id), 
        "org": ObjectId(user["organization"])
    })

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found or you do not have permission to view it.")
    
    return Agent(**agent)


@router.put("/agents/{agent_id}", response_model=Agent)
def update_agent(agent_id: str, agent_update: AgentUpdate, token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    org_id = ObjectId(user["organization"])
    
    if user.get("permission") != "orgadmin":
        raise HTTPException(status_code=403, detail="Permission denied: Only organization admins can update agents.")

    if not ObjectId.is_valid(agent_id):
        raise HTTPException(status_code=400, detail="Invalid agent ID format.")

    if not agents_db.find_one({"_id": ObjectId(agent_id), "org": org_id}):
        raise HTTPException(status_code=404, detail="Agent not found.")
    
    update_data = agent_update.model_dump(exclude_unset=True, exclude_none=True)

    if "connector_ids" in update_data and update_data["connector_ids"] is not None:
        for c_id in update_data["connector_ids"]:
            if not connectors_db.find_one({"_id": c_id, "org": org_id}):
                raise HTTPException(status_code=404, detail=f"Connector with ID {c_id} not found in your organization.")
    
    for field in ["id", "_id", "org", "created_at"]:
        update_data.pop(field, None)

    if not update_data:
        raise HTTPException(status_code=400, detail="No valid update data provided.")

    update_data["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    agents_db.update_one(
        {"_id": ObjectId(agent_id)},
        {"$set": update_data}
    )

    updated_agent = agents_db.find_one({"_id": ObjectId(agent_id)})
    return Agent(**updated_agent)


@router.delete("/agents/{agent_id}")
def delete_agent(agent_id: str, token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    
    if user.get("permission") != "orgadmin":
        raise HTTPException(status_code=403, detail="Permission denied: Only organization admins can delete agents.")

    if not ObjectId.is_valid(agent_id):
        raise HTTPException(status_code=400, detail="Invalid agent ID format.")
    
    result = agents_db.delete_one({
        "_id": ObjectId(agent_id), 
        "org": ObjectId(user["organization"])
    })

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Agent not found or you do not have permission to delete it.")
    
    return {"message": f"Agent '{agent_id}' deleted successfully."}