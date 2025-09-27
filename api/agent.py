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

sessions_db = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/")).nexa.sessions
agents_db = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/")).nexa.agents
connectors_db = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/")).nexa.connectors

Tools = Literal[
    "search_web",
]

Connectors = Literal[
    "google_sheet",
    "google_drive",
    "source_pdf",
    "source_uri"
]

Models = Literal[
    "gpt-3.5-turbo",
    "gpt-4",
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-5"
]

def _clean_tool_name(name: str, prefix: str) -> str:
    s = re.sub(r'\W+', '_', name)
    return f"{prefix}_{s}".lower()

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
            json_schema=core_schema.no_info_after_validator_function(
                validate_object_id, core_schema.str_schema()
            ),
            python_schema=core_schema.no_info_plain_validator_function(
                validate_object_id
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(str),
        )

class Connector(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    name: str = Field(...)
    connector_type: Connectors = Field(..., alias="connector_type")
    settings: Dict[str, Any]
    org: PyObjectId

class ConnectorCreate(BaseModel):
    name: str = Field(...)
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
    agent_id: str | None
    agent_name: str

class AgentState(TypedDict, total=False):
    question: str
    chat_history: list[ChatHistoryEntry]
    agent_id: str | None
    agent_name: str
    answer: str

@traceable
async def get_agent_components(
    question: str,
    organization_id: ObjectId,
    chat_history: list | None = None,
    agent_id: str | None = None,
) -> tuple:
    question = question.strip()
    chat_history = chat_history or []
    selected_agent = None

    if agent_id:
        selected_agent = agents_db.find_one(
            {"_id": ObjectId(agent_id), "org": organization_id}
        )
    else:
        agents = list(agents_db.find({"org": organization_id}))
        if agents:
            agent_descriptions = "\n".join(
                [f"- **{agent['name']}**: {agent['description']}" for agent in agents]
            )
            router_prompt = [
                SystemMessage(
                    content=(
                        "You are an expert at routing a user's request to the correct agent. "
                        "Based on the user's question, select the best agent from the following list. "
                        "You must output **only the name** of the agent you choose. "
                        "If no agent seems suitable for the request, you must output 'Generalist'."
                        f"\n\nAvailable Agents:\n{agent_descriptions}"
                    )
                ),
                HumanMessage(content=question),
            ]
            router_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
            selected_agent_name_response = await router_llm.ainvoke(router_prompt)
            selected_agent_name = selected_agent_name_response.content.strip()
            selected_agent = next(
                (agent for agent in agents if agent["name"] == selected_agent_name),
                None,
            )

    def pre_model_hook(messages: list, config: dict):
        trimmed = []
        system_added = False
        for m in messages:
            if isinstance(m, SystemMessage):
                if not system_added:
                    trimmed.append(m)
                    system_added = True
            else:
                trimmed.append(m)

        return trimmed[-20:]

    if selected_agent:
        active_tools = []
        for tool_name in selected_agent.get("tools", []):
            if tool_name == "search_web":
                from api.tools.web import search_web
                active_tools.append(search_web)
        tool_factory_map = {
            "google_sheet": "api.tools.google_sheet.get_google_sheet_tool",
            "google_drive": "api.tools.google_drive.get_google_drive_tool",
            "source_pdf": "api.tools.pdf_source.get_pdf_source_tool",
            "source_uri": "api.tools.uri_source.get_uri_source_tool"
        }
        connector_ids = selected_agent.get("connector_ids", [])
        if connector_ids:
            agent_connectors = list(connectors_db.find({"_id": {"$in": connector_ids}}))
            for connector in agent_connectors:
                connector_type = connector.get("connector_type")
                tool_factory_path = tool_factory_map.get(connector_type)
                if not tool_factory_path:
                    continue

                module_path, func_name = tool_factory_path.rsplit(".", 1)
                import importlib
                tool_factory = getattr(importlib.import_module(module_path), func_name)
                tool_name = _clean_tool_name(connector["name"], connector_type)
                new_tool = tool_factory(
                    settings=connector["settings"],
                    name=tool_name
                )
                active_tools.append(new_tool)

        system_prompt = selected_agent["description"]
        final_agent_id = selected_agent["_id"]
        final_agent_name = selected_agent["name"]
        agent_llm = ChatOpenAI(
            model=selected_agent["model"],
            temperature=selected_agent.get("temperature", 0.7),
            streaming=True,
            max_retries=3
        ).with_config(system_message=system_prompt)
        agent = create_react_agent(agent_llm, active_tools, pre_model_hook=pre_model_hook)
    else:
        system_prompt = "You are a helpful general-purpose assistant."
        final_agent_id = None
        final_agent_name = "Generalist"
        agent_llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            max_retries=3
        ).with_config(system_message=system_prompt)
        agent = create_react_agent(agent_llm, [], pre_model_hook=pre_model_hook)

    messages = [SystemMessage(content=system_prompt)]
    for entry in chat_history:
        messages.append(HumanMessage(content=entry["user"]))
        messages.append(AIMessage(content=entry["assistant"]))
    messages.append(HumanMessage(content=question))

    return (
        agent,
        messages,
        final_agent_name,
        str(final_agent_id) if final_agent_id else None,
    )