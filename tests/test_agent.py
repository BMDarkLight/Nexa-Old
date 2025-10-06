import pytest
from httpx import AsyncClient
from httpx import ASGITransport
from fastapi.testclient import TestClient
from bson import ObjectId
import uuid
import json

from api.main import app, pwd_context
from api.database import users_db, orgs_db, sessions_db
from langchain.schema import HumanMessage, AIMessage

client = TestClient(app)

def strip_metadata(text: str) -> str:
    """Strip the metadata line '[Agent: ... | Session: ...]' from the response text."""
    lines = text.splitlines()
    if lines and lines[0].startswith("[Agent:"):
        return "\n".join(lines[1:]).strip()
    return text.strip()

def auth_header(token):
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown_db():
    users_db.delete_many({})
    orgs_db.delete_many({})
    sessions_db.delete_many({})
    yield
    users_db.delete_many({})
    orgs_db.delete_many({})
    sessions_db.delete_many({})

@pytest.fixture(scope="module")
def test_user():
    org = orgs_db.insert_one({"name": "AgentTestCorp"})
    org_id = org.inserted_id
    user_doc = {
        "_id": ObjectId(),
        "username": "test_agent_user",
        "password": pwd_context.hash("testpass"),
        "permission": "orguser",
        "status": "active",
        "organization": org_id
    }
    users_db.insert_one(user_doc)
    return user_doc

@pytest.fixture(scope="module")
def test_user_token(test_user):
    resp = client.post("/signin", data={"username": test_user["username"], "password": "testpass"})
    assert resp.status_code == 200
    return resp.json()["access_token"]

@pytest.fixture(autouse=True)
def mock_agent_graph_and_chat(monkeypatch):
    # Mock ChatOpenAI
    class MockChatOpenAI:
        def __init__(self, *args, **kwargs):
            pass

        async def astream(self, messages):
            for msg in messages:
                if hasattr(msg, "content") and msg.content:
                    chunk = {"agent": {"messages": [AIMessage(content=f"Mocked {msg.content}")]}}
                    # Yield JSON bytes with a newline delimiter for streaming compatibility
                    yield (json.dumps(chunk) + "\n").encode("utf-8")

    monkeypatch.setattr("api.agent.ChatOpenAI", MockChatOpenAI)

    async def mock_get_agent_graph(*args, **kwargs):
        messages_list = [HumanMessage(content="Hello there")]
        return {
            "graph": MockChatOpenAI(),
            "messages": [],
            "final_agent_name": "Mocked Agent",
            "final_agent_id": str(ObjectId()),
            "astream_input": messages_list
        }

    monkeypatch.setattr("api.routes.agents.get_agent_graph", mock_get_agent_graph)


@pytest.mark.asyncio
async def test_ask_existing_session(test_user_token, test_user):
    session_id = str(uuid.uuid4())
    initial_history = [{"user": "Initial question", "assistant": "Initial answer"}]
    sessions_db.insert_one({
        "session_id": session_id,
        "user_id": str(test_user["_id"]),
        "chat_history": initial_history
    })

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/ask",
            headers=auth_header(test_user_token),
            json={"query": "Follow-up question", "session_id": session_id}
        )
        response_text = "".join([chunk.decode("utf-8") async for chunk in resp.aiter_bytes()])
        response_text = strip_metadata(response_text)
        assert resp.status_code == 200

        session_doc = sessions_db.find_one({"session_id": session_id})
        assert len(session_doc["chat_history"]) == 2
        assert session_doc["chat_history"][1]["user"] == "Follow-up question"
        assert session_doc["chat_history"][1]["assistant"] == response_text

def test_ask_permission_denied_for_other_user_session(test_user_token):
    session_id = str(uuid.uuid4())
    sessions_db.insert_one({
        "session_id": session_id,
        "user_id": str(ObjectId()),
        "chat_history": []
    })

    resp = client.post(
        "/ask",
        headers=auth_header(test_user_token),
        json={"query": "Trying to access", "session_id": session_id}
    )
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_regenerate_message_success(test_user_token, test_user):
    session_id = str(uuid.uuid4())
    initial_history = [
        {"user": "Question 1", "assistant": "Answer 1"},
        {"user": "Question 2", "assistant": "Bad Answer 2"}
    ]
    sessions_db.insert_one({
        "session_id": session_id,
        "user_id": str(test_user["_id"]),
        "chat_history": initial_history
    })

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/ask/regenerate/1",
            headers=auth_header(test_user_token),
            json={"session_id": session_id, "query": "Question 2"}
        )
        response_text = "".join([chunk.decode("utf-8") async for chunk in resp.aiter_bytes()])
        response_text = strip_metadata(response_text)
        assert resp.status_code == 200

        session_doc = sessions_db.find_one({"session_id": session_id})
        assert session_doc["chat_history"][1]["assistant"] in response_text

@pytest.mark.asyncio
async def test_edit_message_success(test_user_token, test_user):
    session_id = str(uuid.uuid4())
    initial_history = [
        {"user": "Original Question", "assistant": "Original Answer"},
        {"user": "Another Question", "assistant": "Another Answer"}
    ]
    sessions_db.insert_one({
        "session_id": session_id,
        "user_id": str(test_user["_id"]),
        "chat_history": initial_history
    })

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/ask/edit/0",
            headers=auth_header(test_user_token),
            json={"session_id": session_id, "query": "Edited Question"}
        )
        response_text = "".join([chunk.decode("utf-8") async for chunk in resp.aiter_bytes()])
        response_text = strip_metadata(response_text)
        assert resp.status_code == 200

        session_doc = sessions_db.find_one({"session_id": session_id})
        assert session_doc["chat_history"][0]["user"] == "Edited Question"
        assert session_doc["chat_history"][0]["assistant"] in response_text
        assert session_doc["chat_history"][1]["user"] == "Another Question"
        assert session_doc["chat_history"][1]["assistant"] == "Another Answer"