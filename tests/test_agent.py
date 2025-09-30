import pytest
from fastapi.testclient import TestClient
from bson import ObjectId
import uuid

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
    # Mock the ChatOpenAI class
    class MockChatOpenAI:
        def __init__(self, *args, **kwargs):
            pass

        async def astream(self, messages):
            for msg in messages:
                if hasattr(msg, "content") and msg.content:
                    yield AIMessage(content=f"Mocked {msg.content}")

    # Patch ChatOpenAI where it is actually imported and used
    monkeypatch.setattr("api.agent.ChatOpenAI", MockChatOpenAI)

    # Mock get_agent_graph
    async def mock_get_agent_graph(*args, **kwargs):
        messages_list = [HumanMessage(content="Hello there")]
        return {
            "graph": MockChatOpenAI(),
            "messages": [],
            "final_agent_name": "Mocked Agent",
            "final_agent_id": str(ObjectId()),
            "astream_input": messages_list
        }

    # Patch get_agent_graph where it's actually imported in the routes
    monkeypatch.setattr("api.routes.agents.get_agent_graph", mock_get_agent_graph)


def test_ask_new_session(test_user_token, test_user):
    resp = client.post(
        "/ask",
        headers=auth_header(test_user_token),
        json={"query": "Hello there"}
    )
    assert resp.status_code == 200
    response_text = strip_metadata(resp.text)
    assert "Mocked Hello there" in response_text

    session_doc = sessions_db.find_one({"user_id": str(test_user["_id"]), "chat_history.0.user": "Hello there"})
    assert session_doc is not None
    assert session_doc["chat_history"][0]["assistant"] == response_text

def test_ask_existing_session(test_user_token, test_user):
    session_id = str(uuid.uuid4())
    initial_history = [{"user": "Initial question", "assistant": "Initial answer"}]
    sessions_db.insert_one({
        "session_id": session_id,
        "user_id": str(test_user["_id"]),
        "chat_history": initial_history
    })

    resp = client.post(
        "/ask",
        headers=auth_header(test_user_token),
        json={"query": "Follow-up question", "session_id": session_id}
    )
    assert resp.status_code == 200
    response_text = strip_metadata(resp.text)

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

def test_regenerate_message_success(test_user_token, test_user):
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

    resp = client.post(
        "/ask/regenerate/1",
        headers=auth_header(test_user_token),
        json={"session_id": session_id, "query": "Question 2"}
    )
    assert resp.status_code == 200

    session_doc = sessions_db.find_one({"session_id": session_id})
    assert session_doc["chat_history"][1]["assistant"] in resp.text

def test_edit_message_success(test_user_token, test_user):
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

    resp = client.post(
        "/ask/edit/0",
        headers=auth_header(test_user_token),
        json={"session_id": session_id, "query": "Edited Question"}
    )
    assert resp.status_code == 200

    session_doc = sessions_db.find_one({"session_id": session_id})
    assert session_doc["chat_history"][0]["user"] == "Edited Question"
    assert session_doc["chat_history"][0]["assistant"] in resp.text
    assert session_doc["chat_history"][1]["user"] == "Another Question"
    assert session_doc["chat_history"][1]["assistant"] == "Another Answer"