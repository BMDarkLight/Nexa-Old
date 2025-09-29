from langchain_openai import ChatOpenAI
from langsmith import traceable
from langgraph.prebuilt import create_react_agent
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from typing import TypedDict, Literal, List, Optional, Dict, Any
from pymongo import MongoClient
from bson import ObjectId
from pydantic import BaseModel, Field, ConfigDict

import os
import re
import importlib
import logging
import unidecode

sessions_db = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/")).nexa.sessions
agents_db = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/")).nexa.agents
connectors_db = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/")).nexa.connectors

Tools = Literal["search_web"]

Connectors = Literal["google_sheet", "google_drive", "source_pdf", "source_uri"]

Models = Literal["gpt-3.5-turbo", "gpt-4", "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-5"]

def _clean_tool_name(name: str, prefix: str) -> Dict[str, str]:
    name_ascii = unidecode.unidecode(name)
    sanitized = re.sub(r'[^a-zA-Z0-9_-]+', '_', name_ascii)
    sanitized = re.sub(r'_+', '_', sanitized)
    sanitized = sanitized.strip('_')
    tool_name = f"{prefix}_{sanitized}".lower()
    llm_label = name.strip()
    return {"tool_name": tool_name, "llm_label": llm_label}

class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):
        from pydantic_core import core_schema
        def validate_object_id(v):
            if isinstance(v, ObjectId):
                return v
            if ObjectId.is_valid(v):
                return ObjectId(v)
            raise ValueError("Invalid ObjectId")

        return core_schema.json_or_python_schema(
            json_schema=core_schema.no_info_after_validator_function(validate_object_id, core_schema.str_schema()),
            python_schema=core_schema.no_info_plain_validator_function(validate_object_id),
            serialization=core_schema.plain_serializer_function_ser_schema(str),
        )

class Connector(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    name: str
    connector_type: Connectors
    settings: Dict[str, Any]
    org: PyObjectId

class ConnectorCreate(BaseModel):
    name: str
    connector_type: Connectors
    settings: Dict[str, Any]

class ConnectorUpdate(BaseModel):
    name: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None

class Agent(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    name: str
    description: str
    org: PyObjectId
    model: Models
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    tools: list[Tools]
    connector_ids: List[PyObjectId] = Field(default_factory=list)
    created_at: str
    updated_at: str

class AgentCreate(BaseModel):
    name: str
    description: str
    model: Models
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    tools: List[Tools] = []
    connector_ids: List[PyObjectId] = Field(default_factory=list)

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    model: Optional[Models] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    tools: Optional[List[Tools]] = None
    connector_ids: Optional[List[PyObjectId]] = None

class ChatHistoryEntry(TypedDict):
    user: str
    assistant: str
    agent_id: Optional[str]
    agent_name: str

class AgentState(TypedDict, total=False):
    question: str
    chat_history: List[ChatHistoryEntry]
    agent_id: Optional[str]
    agent_name: str
    answer: str

def convert_messages_to_dict(messages: List[Any]) -> List[Dict[str, str]]:
    result = []
    for m in messages:
        if isinstance(m, SystemMessage):
            result.append({"role": "system", "content": m.content})
        elif isinstance(m, HumanMessage):
            result.append({"role": "user", "content": m.content})
        elif isinstance(m, AIMessage):
            result.append({"role": "assistant", "content": m.content})
        else:
            raise ValueError(f"Cannot convert message: {m}")
    return result

@traceable
async def get_agent_graph(
    question: str,
    organization_id: ObjectId,
    chat_history: Optional[List[dict]] = None,
    agent_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Returns a dict with:
    - graph: the React agent graph
    - messages: the chat history in dict form
    - final_agent_name: the agent's name
    - final_agent_id: the agent's id (str) or None
    """
    question = question.strip()
    chat_history = chat_history or []
    selected_agent = None

    if agent_id:
        selected_agent = agents_db.find_one({"_id": ObjectId(agent_id), "org": organization_id})
    else:
        agents = list(agents_db.find({"org": organization_id}))
        if agents:
            agent_descriptions = "\n".join([f"- **{agent['name']}**: {agent['description']}" for agent in agents])
            router_prompt = [
                SystemMessage(
                    content=(
                        "You are an expert at routing a user's request to the correct agent. "
                        "Based on the user's question, select the best agent from the following list. "
                        "You must output **only the name** of the agent you choose. "
                        "If no agent seems suitable, output 'Generalist'."
                        f"\n\nAvailable Agents:\n{agent_descriptions}"
                    )
                ),
                HumanMessage(content=question),
            ]
            router_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
            selected_agent_name_response = await router_llm.ainvoke(router_prompt)
            selected_agent_name = selected_agent_name_response.content.strip()
            selected_agent = next((agent for agent in agents if agent["name"] == selected_agent_name), None)

    active_tools = []

    async def get_search_web_tool():
        from api.tools.web import get_search_web_tool
        return get_search_web_tool()

    builtin_tool_factories = {"search_web": get_search_web_tool}
    connector_tool_factory_map = {
        "google_sheet": "api.tools.google_sheet.get_google_sheet_tool",
        "google_drive": "api.tools.google_drive.get_google_drive_tool",
        "source_pdf": "api.tools.pdf_source.get_pdf_source_tool",
        "source_uri": "api.tools.uri_source.get_uri_source_tool"
    }

    if selected_agent:
        for tool_name in selected_agent.get("tools", []):
            factory = builtin_tool_factories.get(tool_name)
            if factory:
                active_tools.append(await factory())

        connector_ids = selected_agent.get("connector_ids", [])
        if connector_ids:
            agent_connectors = list(connectors_db.find({"_id": {"$in": connector_ids}}))
            for connector in agent_connectors:
                try:
                    connector_type = connector.get("connector_type")
                    tool_factory_path = connector_tool_factory_map.get(connector_type)
                    if not tool_factory_path:
                        logging.warning(f"No tool factory defined for connector type: {connector_type}")
                        continue
                    module_path, func_name = tool_factory_path.rsplit(".", 1)
                    tool_factory = getattr(importlib.import_module(module_path), func_name)
                    names = _clean_tool_name(connector["name"], connector_type)
                    tool_name = names["tool_name"]
                    llm_label = names["llm_label"]

                    if connector_type in ["source_pdf", "source_uri"]:
                        active_tools.append(tool_factory(settings=connector["settings"], name=tool_name))
                    else:
                        active_tools.append(tool_factory(settings=connector["settings"], name=tool_name, llm_label=llm_label))

                    logging.info(f"Loaded connector tool: {tool_name}")
                except Exception as e:
                    logging.error(f"Failed to create tool for connector {connector.get('name')}: {e}")

        logging.info(f"Active tools for agent '{selected_agent['name'] if selected_agent else 'Generalist'}': "
                     f"{[(getattr(t, 'name', None), getattr(t, 'llm_label', None)) for t in active_tools]}")

        for tool in active_tools:
            if hasattr(tool, "run"):
                original_run = tool.run
                if callable(original_run):
                    async def logging_run(input_text, original_run=original_run, tool=tool):
                        logging.info(f"Tool '{getattr(tool, 'name', 'unknown')}' called with input: {input_text}")
                        output = await original_run(input_text)
                        logging.info(f"Tool '{getattr(tool, 'name', 'unknown')}' output: {output}")
                        return output
                    tool.run = logging_run

        system_prompt = selected_agent["description"]
        final_agent_id = selected_agent["_id"]
        final_agent_name = selected_agent["name"]
        agent_llm = ChatOpenAI(model=selected_agent["model"], temperature=selected_agent.get("temperature", 0.7), streaming=True, max_retries=3)
        graph = create_react_agent(agent_llm, active_tools)
    else:
        system_prompt = "You are a helpful general-purpose assistant."
        final_agent_id = None
        final_agent_name = "Generalist"

        messages_list = [SystemMessage(content=system_prompt)]
        for entry in chat_history:
            messages_list.append(HumanMessage(content=entry["user"]))
            messages_list.append(AIMessage(content=entry["assistant"]))
        messages_list.append(HumanMessage(content=question))

        logging.info(f"Messages going into agent: {[m.content for m in messages_list]}")

        agent_llm = ChatOpenAI(model="gpt-4o-mini", streaming=True, temperature=0.7, max_retries=3)
        graph = agent_llm

        messages_dict = convert_messages_to_dict(messages_list)

        return {
            "graph": graph,
            "messages": messages_dict,
            "final_agent_name": final_agent_name,
            "final_agent_id": None,
        }

    messages_list = [SystemMessage(content=system_prompt)]
    for entry in chat_history:
        messages_list.append(HumanMessage(content=entry["user"]))
        messages_list.append(AIMessage(content=entry["assistant"]))
    messages_list.append(HumanMessage(content=question))

    logging.info(f"Messages going into agent: {[m.content for m in messages_list]}")

    messages_dict = convert_messages_to_dict(messages_list)


    return {
        "graph": graph,
        "messages": messages_dict,
        "final_agent_name": final_agent_name,
        "final_agent_id": str(final_agent_id) if final_agent_id else None,
    }