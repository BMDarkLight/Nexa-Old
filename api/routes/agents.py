from fastapi import BackgroundTasks, Depends, APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage

from bson import ObjectId
from typing import List
import datetime
import logging

from api.schemas.agents import QueryRequest, save_chat_history, update_chat_history_entry, replace_chat_history_from_point
from api.database import sessions_db, agents_db, connectors_db, knowledge_db, minio_client
from api.agent import get_agent_graph
from api.schemas.agents import Agent, AgentCreate, AgentUpdate, agent_doc_to_model
from api.embed import delete_embeddings
from api.auth import verify_token, oauth2_scheme

router = APIRouter(tags=["Agent"])

logger = logging.getLogger("agent_delete")
logger.setLevel(logging.INFO)

def _prepare_astream_input(graph, system_content, chat_history, query_text):
    """
    Prepares the input messages for agent streaming.
    For React agents:
        - Returns a list of BaseMessage objects (SystemMessage, HumanMessage, AIMessage).
        - Normalizes all message content by stripping whitespace.
        - Includes the system message as SystemMessage, chat history as HumanMessage/AIMessage, and the current query as HumanMessage.
    For non-React agents:
        - Keeps existing behavior (BaseMessage or dicts as previously).
    """
    is_react = False
    if hasattr(graph, "_is_react_agent") and getattr(graph, "_is_react_agent", False):
        is_react = True
    elif (
        hasattr(graph, "tools")
        or hasattr(graph, "_tool_names")
        or hasattr(graph, "_react_agent")
        or hasattr(graph, "react_agent")
    ):
        is_react = True
    else:
        graph_cls = type(graph).__name__.lower()
        if "react" in graph_cls:
            is_react = True

    def normalize_content(val):
        if val is None:
            return ""
        return str(val).strip()

    if is_react:
        resolved_system_content = system_content
        if not resolved_system_content:
            if hasattr(graph, "system_prompt") and getattr(graph, "system_prompt", None):
                resolved_system_content = getattr(graph, "system_prompt")
            elif hasattr(graph, "messages") and isinstance(getattr(graph, "messages", None), list):
                messages_list = getattr(graph, "messages", [])
                if messages_list and isinstance(messages_list[0], SystemMessage):
                    resolved_system_content = messages_list[0].content
            if not resolved_system_content:
                resolved_system_content = "You are an AI agent in Nexa AI platform."
        resolved_system_content = normalize_content(resolved_system_content)
        if not resolved_system_content:
            resolved_system_content = "You are an AI agent in Nexa AI platform."

        messages = []
        # Always start with a system message
        messages.append(SystemMessage(content=resolved_system_content))

        # Normalize chat history: append HumanMessage or AIMessage as appropriate
        for entry in chat_history:
            if isinstance(entry, dict):
                # user
                if "user" in entry:
                    user_content = normalize_content(entry["user"])
                    if user_content:
                        messages.append(HumanMessage(content=user_content))
                # assistant
                if "assistant" in entry:
                    assistant_content = normalize_content(entry["assistant"])
                    if assistant_content:
                        messages.append(AIMessage(content=assistant_content))
                # ai (treated as assistant)
                if "ai" in entry:
                    ai_content = normalize_content(entry["ai"])
                    if ai_content:
                        messages.append(AIMessage(content=ai_content))
            else:
                # Defensive: handle BaseMessage objects or similar
                role = getattr(entry, "role", None)
                content = getattr(entry, "content", None)
                content_str = normalize_content(content)
                if role == "user" and content_str:
                    messages.append(HumanMessage(content=content_str))
                elif role == "assistant" and content_str:
                    messages.append(AIMessage(content=content_str))
        # Add current query as HumanMessage
        user_query_content = normalize_content(query_text)
        if not user_query_content:
            user_query_content = ""
        messages.append(HumanMessage(content=user_query_content))
        return messages
    else:
        # Non-react agents: use BaseMessage objects, but normalize content to strings and strip whitespace
        messages = []
        if system_content:
            sys_content = normalize_content(system_content)
            if sys_content:
                messages.append(SystemMessage(content=sys_content))
        for entry in chat_history:
            if isinstance(entry, dict):
                if "user" in entry:
                    user_content = normalize_content(entry["user"])
                    if user_content:
                        messages.append(HumanMessage(content=user_content))
                if "assistant" in entry:
                    assistant_content = normalize_content(entry["assistant"])
                    if assistant_content:
                        messages.append(AIMessage(content=assistant_content))
                if "ai" in entry:
                    ai_content = normalize_content(entry["ai"])
                    if ai_content:
                        messages.append(AIMessage(content=ai_content))
            else:
                role = getattr(entry, "role", None)
                content = getattr(entry, "content", None)
                content_str = normalize_content(content)
                if role == "user" and content_str:
                    messages.append(HumanMessage(content=content_str))
                elif role == "assistant" and content_str:
                    messages.append(AIMessage(content=content_str))
        user_query_content = normalize_content(query_text)
        if not user_query_content:
            user_query_content = ""
        messages.append(HumanMessage(content=user_query_content))
        return messages

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
        token_usage = agent_graph
        logger.info(f"Token usage for this query: {token_usage}")
        if session:
            total_tokens = token_usage.get("total_tokens", 0)
            sessions_db.update_one(
                {"session_id": session_id},
                {
                    "$push": {"chat_history": {"user": query.query, "assistant": ""}},
                    "$inc": {"token_usage.total_tokens": total_tokens}
                },
                upsert=True
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
            input_messages = _prepare_astream_input(graph, system_content=None, chat_history=chat_history, query_text=query.query)
            if graph:
                try:
                    async for chunk in graph.astream({"messages": input_messages}):
                        # Logging for each chunk
                        logging.info(f"Chunk received: {chunk}")
                        contents = []
                        # Support React-agent-wrapped responses: dict with "agent" key containing "messages"
                        if isinstance(chunk, dict) and "agent" in chunk and isinstance(chunk["agent"], dict) and "messages" in chunk["agent"]:
                            agent_messages = chunk["agent"]["messages"]
                            for msg in agent_messages:
                                # If AIMessage, get content
                                if isinstance(msg, AIMessage):
                                    msg_content = getattr(msg, "content", None)
                                    if msg_content:
                                        contents.append(msg_content)
                        else:
                            # Previous cases: direct "content" key or BaseMessage
                            content = None
                            if isinstance(chunk, dict):
                                content = chunk.get("content", "")
                            elif isinstance(chunk, BaseMessage):
                                content = getattr(chunk, "content", None)
                            else:
                                content = str(chunk)
                            if content is None:
                                content = ""
                            if content:
                                contents.append(content)
                        for content_piece in contents:
                            if content_piece:
                                yield content_piece
                                full_answer += content_piece
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
            input_messages = _prepare_astream_input(graph, system_content=None, chat_history=truncated_history, query_text=original_query)
            if graph:
                try:
                    async for chunk in graph.astream({"messages": input_messages}):
                        # Logging for each chunk
                        logging.info(f"Chunk received: {chunk}")
                        contents = []
                        # Support React-agent-wrapped responses: dict with "agent" key containing "messages"
                        if isinstance(chunk, dict) and "agent" in chunk and isinstance(chunk["agent"], dict) and "messages" in chunk["agent"]:
                            agent_messages = chunk["agent"]["messages"]
                            for msg in agent_messages:
                                if isinstance(msg, AIMessage):
                                    msg_content = getattr(msg, "content", None)
                                    if msg_content:
                                        contents.append(msg_content)
                        else:
                            content = None
                            if isinstance(chunk, dict):
                                content = chunk.get("content", "")
                            elif isinstance(chunk, BaseMessage):
                                content = getattr(chunk, "content", None)
                            else:
                                content = str(chunk)
                            if content is None:
                                content = ""
                            if content:
                                contents.append(content)
                        for content_piece in contents:
                            if content_piece:
                                yield content_piece
                                full_answer += content_piece
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
            input_messages = _prepare_astream_input(graph, system_content=None, chat_history=truncated_history, query_text=query)
            if graph:
                try:
                    async for chunk in graph.astream({"messages": input_messages}):
                        # Logging for each chunk
                        logging.info(f"Chunk received: {chunk}")
                        contents = []
                        if isinstance(chunk, dict) and "agent" in chunk and isinstance(chunk["agent"], dict) and "messages" in chunk["agent"]:
                            agent_messages = chunk["agent"]["messages"]
                            for msg in agent_messages:
                                if isinstance(msg, AIMessage):
                                    msg_content = getattr(msg, "content", None)
                                    if msg_content:
                                        contents.append(msg_content)
                        else:
                            content = None
                            if isinstance(chunk, dict):
                                content = chunk.get("content", "")
                            elif isinstance(chunk, BaseMessage):
                                content = getattr(chunk, "content", None)
                            else:
                                content = str(chunk)
                            if content is None:
                                content = ""
                            if content:
                                contents.append(content)
                        for content_piece in contents:
                            if content_piece:
                                yield content_piece
                                full_answer += content_piece
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
    org_id = ObjectId(user["organization"])

    logger.info(f"Starting deletion of agent {agent_id} by user {user.get('_id')}")

    if user.get("permission") != "orgadmin":
        logger.warning(f"User {user.get('_id')} tried to delete agent without permission")
        raise HTTPException(status_code=403, detail="Permission denied: Only organization admins can delete agents.")

    if not ObjectId.is_valid(agent_id):
        logger.error(f"Invalid agent ID format: {agent_id}")
        raise HTTPException(status_code=400, detail="Invalid agent ID format.")

    agent = agents_db.find_one({"_id": ObjectId(agent_id), "org": org_id})
    if not agent:
        logger.warning(f"Agent not found or access denied for agent_id={agent_id}")
        raise HTTPException(status_code=404, detail="Agent not found or you do not have permission to delete it.")

    context_entries = agent.get("context", [])
    logger.info(f"Found {len(context_entries)} context entries for agent {agent_id}")
    for entry in context_entries:
        if isinstance(entry, ObjectId):
            context_id = entry
            context_doc = knowledge_db.find_one({"_id": context_id})
            if not context_doc:
                logger.warning(f"Context document with id {context_id} not found in knowledge_db.")
                continue
        elif isinstance(entry, dict):
            context_id = entry.get("_id") or entry.get("id")
            context_doc = knowledge_db.find_one({"_id": ObjectId(str(context_id))}) if context_id else entry
        else:
            logger.warning(f"Unexpected context entry type for agent {agent_id}: {type(entry)}")
            continue
        file_key = context_doc.get("file_key")
        if file_key:
            try:
                minio_client.remove_object(bucket_name="context-files", object_name=file_key)
                logger.info(f"Removed file {file_key} from Minio for context {context_id}")
            except Exception as e:
                logger.error(f"Failed to remove file {file_key} from Minio for context {context_id}: {str(e)}")
        else:
            logger.info(f"No file_key present for context {context_id}")
        try:
            delete_embeddings(context_doc, org_id)
            logger.info(f"Deleted embeddings for context {context_id}")
        except Exception as e:
            logger.error(f"Failed to delete embeddings for context {context_id}: {str(e)}")

    try:
        result = agents_db.delete_one({"_id": ObjectId(agent_id), "org": org_id})
        if result.deleted_count == 0:
            logger.error(f"Failed to delete agent {agent_id}")
            raise HTTPException(status_code=404, detail="Agent not found or you do not have permission to delete it.")
        logger.info(f"Agent {agent_id} deleted successfully")
    except Exception as e:
        logger.exception(f"Unexpected error when deleting agent {agent_id}")
        raise HTTPException(status_code=500, detail=f"Failed to delete agent: {str(e)}")

    return {"message": f"Agent '{agent_id}' deleted successfully."}