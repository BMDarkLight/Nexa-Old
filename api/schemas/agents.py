from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, TypedDict, Literal

from api.schemas.base import PyObjectId
from api.database import sessions_db

Tools = Literal["search_web"]

Models = Literal["gpt-3.5-turbo", "gpt-4", "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-5"]

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    agent_id: Optional[str] = None

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

def save_chat_history(session_id: str, user_id: str, chat_history: list, query: str, answer: str, agent_id: str, agent_name: str):
    new_history_entry = {
        "user": query,
        "assistant": answer,
        "agent_id": agent_id,
        "agent_name": agent_name
    }
    updated_chat_history = chat_history + [new_history_entry]
    sessions_db.update_one(
        {"session_id": session_id},
        {"$set": {"chat_history": updated_chat_history, "user_id": user_id}},
        upsert=True
    )

def update_chat_history_entry(session_id: str, message_num: int, new_query: str, new_answer: str):
    sessions_db.update_one(
        {"session_id": session_id},
        {
            "$set": {
                f"chat_history.{message_num}.user": new_query,
                f"chat_history.{message_num}.assistant": new_answer,
            }
        }
    )

def replace_chat_history_from_point(session_id: str, user_id: str, truncated_history: list, query: str, new_answer: str, agent_id: str, agent_name: str):
    new_entry = {
        "user": query,
        "assistant": new_answer,
        "agent_id": agent_id,
        "agent_name": agent_name
    }
    final_history = truncated_history + [new_entry]
    sessions_db.update_one(
        {"session_id": session_id},
        {"$set": {"chat_history": final_history, "user_id": user_id}}
    )