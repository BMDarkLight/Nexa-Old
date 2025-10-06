from fastapi import BackgroundTasks, Depends, APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from bson import ObjectId
from typing import List
import datetime
import logging

from api.schemas.agents import QueryRequest, save_chat_history, update_chat_history_entry, replace_chat_history_from_point
from api.database import sessions_db, agents_db, connectors_db
from api.agent import get_agent_graph
from api.schemas.agents import Agent, AgentCreate, AgentUpdate, convert_messages_to_dict
from api.auth import verify_token, oauth2_scheme

def _build_astream_input(system_content, chat_history, user_query):
    messages = []
    messages.append(SystemMessage(content=system_content))
    for entry in chat_history:
        messages.append(HumanMessage(content=entry["user"]))
        messages.append(AIMessage(content=entry["assistant"]))
    messages.append(HumanMessage(content=user_query))
    return convert_messages_to_dict(messages)

router = APIRouter(tags=["Agent"])

def agent_doc_to_model(agent_doc):
    agent = dict(agent_doc)
    agent["id"] = str(agent.pop("_id"))
    if "org" in agent:
        agent["org"] = str(agent["org"])
    if "context" not in agent or agent["context"] is None:
        agent["context"] = []
    elif not isinstance(agent["context"], list):
        agent["context"] = list(agent["context"]) if agent["context"] else []
    return agent

@router.post("/ask")
async def ask(
    query: QueryRequest,
    background_tasks: BackgroundTasks,
    token: str = Depends(oauth2_scheme)
):
    logger = logging.getLogger("api.routes.agents.ask")

    if not query.query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        user = verify_token(token)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception("Token verification failed")
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

    if not user.get("organization") and user.get("permission") != "sysadmin":
        raise HTTPException(status_code=403, detail="You do not belong to an organization.")

    agent_id_to_use = None
    connectors = []
    context = []
    agent_doc = None

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
        connectors = agent_doc.get("connector_ids") or []
        context = agent_doc.get("context") or []

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
    except Exception as e:
        logger.exception("Exception in get_agent_graph")
        async def error_response(exc_msg):
            yield f"Error while generating agent graph: {exc_msg}"
        return StreamingResponse(error_response(str(e)), media_type="text/plain; charset=utf-8")

    graph = agent_graph.get("graph")
    agent_name = agent_graph.get("final_agent_name", "Unknown Agent")
    agent_id_str = agent_graph.get("final_agent_id", agent_id_to_use or "")

    async def response_generator():
        try:
            full_answer = ""
            system_content = (
                f"You are an AI agent built by user in Nexa AI platform. "
                f"Operating as the agent named {agent_name}. "
                f"Description: {agent_graph.get('description', 'No description provided')}."
            )
            astream_input = _build_astream_input(system_content, chat_history, query.query)
            if graph:
                try:
                    async for chunk in graph.astream(astream_input):
                        content = getattr(chunk, "content", None)
                        if content is None and isinstance(chunk, dict):
                            content = chunk.get("content", "")
                        elif content is None:
                            content = str(chunk)
                        full_answer += content
                        yield content
                except Exception as exc:
                    logger.exception("Exception during streaming agent response")
                    yield f"\n[Error while streaming response: {str(exc)}]\n"
                    return
            else:
                full_answer = f"[Default Agent Response] You asked: {query.query}"
                yield full_answer

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
        except Exception as exc:
            logger.exception("Exception in response_generator")
            yield f"\n[Internal error: {str(exc)}]\n"

    return StreamingResponse(response_generator(), media_type="text/plain; charset=utf-8")

@router.post("/ask/regenerate/{message_num}")
async def regenerate(
    message_num: int,
    background_tasks: BackgroundTasks,
    request: Request,
    token: str = Depends(oauth2_scheme)
):
    logger = logging.getLogger("api.routes.agents.regenerate")
    try:
        data = await request.json()
        session_id = data.get("session_id")
        agent_id = data.get("agent_id")
        user = verify_token(token)
    except Exception as e:
        logger.exception("Failed to parse request or verify token")
        raise HTTPException(status_code=400, detail="Invalid request or authentication.")
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

    agent_doc = None
    if agent_id:
        if ObjectId.is_valid(agent_id):
            agent_doc = agents_db.find_one({"_id": ObjectId(agent_id)})

    try:
        agent_graph = await get_agent_graph(
            question=original_query,
            organization_id=org_id,
            chat_history=truncated_history,
            agent_id=agent_id
        )
    except Exception as e:
        logger.exception("Exception in /ask/regenerate endpoint")
        async def error_response(exc_msg):
            yield f"Sorry, there was an error processing your request. Please try again later. Details: {exc_msg}"
        return StreamingResponse(error_response(str(e)), media_type="text/plain")

    graph = agent_graph.get("graph")
    agent_name = agent_graph.get("final_agent_name", "Unknown Agent")
    agent_id_str = agent_graph.get("final_agent_id", agent_id or "")

    async def response_generator():
        try:
            full_answer = ""
            system_content = (
                f"You are an AI agent built by user in Nexa AI platform. You are now operating as the agent named {agent_name}. Description: {agent_graph.get('description', 'No description provided')}."
            )
            astream_input = _build_astream_input(system_content, truncated_history, original_query)
            if graph:
                try:
                    async for chunk in graph.astream(astream_input):
                        content = getattr(chunk, "content", None)
                        if content is None and isinstance(chunk, dict):
                            content = chunk.get("content", "")
                        elif content is None:
                            content = str(chunk)
                        full_answer += content
                        yield content
                except Exception as exc:
                    logger.exception("Exception during streaming agent response (regenerate)")
                    yield f"\n[Error: An error occurred while generating the response. Details: {str(exc)}]\n"
                    return
            else:
                full_answer = f"[Default Agent Response] You asked: {original_query}"
                yield full_answer
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
        except Exception as exc:
            logger.exception("Exception in response_generator (regenerate)")
            yield f"\n[Internal error: {str(exc)}]\n"
    return StreamingResponse(response_generator(), media_type="text/plain")

@router.post("/ask/edit/{message_num}")
async def edit_message(
    message_num: int,
    background_tasks: BackgroundTasks,
    request: Request,
    token: str = Depends(oauth2_scheme)
):
    logger = logging.getLogger("api.routes.agents.edit_message")
    try:
        data = await request.json()
        query = data.get("query")
        session_id = data.get("session_id")
        agent_id = data.get("agent_id")
        user = verify_token(token)
    except Exception as e:
        logger.exception("Failed to parse request or verify token")
        raise HTTPException(status_code=400, detail="Invalid request or authentication.")
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

    agent_doc = None
    if agent_id:
        if ObjectId.is_valid(agent_id):
            agent_doc = agents_db.find_one({"_id": ObjectId(agent_id)})

    try:
        agent_graph = await get_agent_graph(
            question=query,
            organization_id=org_id,
            chat_history=truncated_history,
            agent_id=agent_id
        )
    except Exception as e:
        logger.exception("Exception in /ask/edit endpoint")
        async def error_response(exc_msg):
            yield f"Sorry, there was an error processing your request. Please try again later. Details: {exc_msg}"
        return StreamingResponse(error_response(str(e)), media_type="text/plain")

    graph = agent_graph.get("graph")
    agent_name = agent_graph.get("final_agent_name", "Unknown Agent")
    agent_id_str = agent_graph.get("final_agent_id", agent_id or "")

    async def response_generator():
        try:
            full_answer = ""
            system_content = (
                f"You are an AI agent built by user in Nexa AI platform. You are now operating as the agent named {agent_name}. Description: {agent_graph.get('description', 'No description provided')}."
            )
            astream_input = _build_astream_input(system_content, truncated_history, query)
            if graph:
                try:
                    async for chunk in graph.astream(astream_input):
                        content = getattr(chunk, "content", None)
                        if content is None and isinstance(chunk, dict):
                            content = chunk.get("content", "")
                        elif content is None:
                            content = str(chunk)
                        full_answer += content
                        yield content
                except Exception as exc:
                    logger.exception("Exception during streaming agent response (edit)")
                    yield f"\n[Error: An error occurred while generating the response. Details: {str(exc)}]\n"
                    return
            else:
                full_answer = f"[Default Agent Response] You asked: {query}"
                yield full_answer
            background_tasks.add_task(
                update_chat_history_entry,
                session_id=session_id,
                message_num=message_num,
                new_query=query,
                new_answer=full_answer
            )
        except Exception as exc:
            logger.exception("Exception in response_generator (edit)")
            yield f"\n[Internal error: {str(exc)}]\n"
    return StreamingResponse(response_generator(), media_type="text/plain")

@router.get("/agents", response_model=List[Agent])
def list_agents(token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    if not user.get("organization"):
        return []
    agents_cursor = agents_db.find({"org": ObjectId(user["organization"])})
    agents_list = []
    for agent in agents_cursor:
        agent_model = agent_doc_to_model(agent)
        agents_list.append(Agent(**agent_model))
    return agents_list


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
    agent_model = agent_doc_to_model(created_agent)
    return Agent(**agent_model)


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
    agent_model = agent_doc_to_model(agent)
    return Agent(**agent_model)


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
    agent_model = agent_doc_to_model(updated_agent)
    return Agent(**agent_model)


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