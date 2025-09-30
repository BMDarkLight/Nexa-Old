import pytest
from fastapi.testclient import TestClient
from bson import ObjectId
import uuid

from api.main import app, pwd_context
from api.agent import get_agent_graph
from api.database import users_db, orgs_db, sessions_db

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
def mock_agent_graph(monkeypatch):
    from langchain_core.prompts.chat import ChatPromptValue
    from api.agent import get_agent_graph as original_get_agent_graph

    class MockGraph:
        async def astream(self, *args, **kwargs):
            # Yield chunks as dictionaries to simulate streaming
            for chunk in [{"content": "Mocked "}, {"content": "Response"}]:
                yield chunk

    async def mock_get_agent_graph(*args, **kwargs):
        return {
            "graph": MockGraph(),
            "messages": [],
            "final_agent_name": "Mocked Agent",
            "final_agent_id": str(ObjectId()),
            "astream_input": ChatPromptValue.from_messages([
                {"role": "user", "content": "Hello"}
            ])
        }

    monkeypatch.setattr("api.agent.get_agent_graph", mock_get_agent_graph)

def test_ask_new_session(test_user_token, test_user):
    resp = client.post(
        "/ask",
        headers=auth_header(test_user_token),
        json={"query": "Hello there"}
    )
    assert resp.status_code == 200
    response_text = strip_metadata(resp.text)
    assert response_text == "Mocked Response"

    session_doc = sessions_db.find_one({"user_id": str(test_user["_id"]), "chat_history.0.user": "Hello there"})
    assert session_doc is not None
    assert len(session_doc["chat_history"]) == 1
    assert session_doc["chat_history"][0]["user"] == "Hello there"
    assert session_doc["chat_history"][0]["assistant"] == "Mocked Response"

def test_ask_existing_session(test_user_token, test_user):
    session_id = str(uuid.uuid4())
    initial_history = [{"user": "Initial question", "assistant": "Initial answer", "agent_id": "some_agent", "agent_name": "Some Agent"}]
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
    assert session_doc["chat_history"][1]["assistant"] == "Mocked Response"

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
    assert len(session_doc["chat_history"]) == 2
    assert session_doc["chat_history"][1]["assistant"] == "Mocked Response"

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
    assert len(session_doc["chat_history"]) == 2
    assert session_doc["chat_history"][0]["user"] == "Edited Question"
    assert session_doc["chat_history"][0]["assistant"] == "Mocked Response"
    assert session_doc["chat_history"][1]["user"] == "Another Question"
    assert session_doc["chat_history"][1]["assistant"] == "Another Answer"
