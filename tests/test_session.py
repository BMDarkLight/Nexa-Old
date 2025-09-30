import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import asyncio

from api.main import app, pwd_context
from api.database import users_db, sessions_db
from api.agent import AIMessage

client = TestClient(app)

# --- Fixtures ---

@pytest.fixture(autouse=True)
def clear_database():
    """Clear users and sessions collections before and after each test."""
    users_db.delete_many({})
    sessions_db.delete_many({})
    yield
    users_db.delete_many({})
    sessions_db.delete_many({})

@pytest.fixture
def authenticated_user():
    """Create a test user and return auth token and user_id."""
    password = "testpassword123"
    user_doc = {
        "username": "test_user_session",
        "password": pwd_context.hash(password),
        "permission": "orguser",
        "status": "active",
        "organization": "test_org_id"
    }
    result = users_db.insert_one(user_doc)
    user_id = str(result.inserted_id)

    response = client.post("/signin", data={"username": user_doc["username"], "password": password})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return token, user_id

def auth_header(token):
    return {"Authorization": f"Bearer {token}"}

def strip_agent_metadata(text: str) -> str:
    """Remove agent metadata from streamed text responses."""
    lines = text.splitlines()
    if lines and lines[0].startswith("[Agent:"):
        return "\n".join(lines[1:]).strip()
    return text.strip()

# --- Mock helpers ---

def create_mock_llm(response_text: str):
    """Create a mock LLM that streams AIMessage objects (single yield)."""
    class MockLLM:
        async def astream(self, messages):
            yield AIMessage(content=response_text)
            await asyncio.sleep(0)
    return MockLLM()

# --- Tests ---

@patch("api.routes.agents.get_agent_graph", new_callable=AsyncMock)
def test_create_new_session(mock_get_agent_graph, authenticated_user):
    """Test that /ask creates a new session and streams response."""
    token, user_id = authenticated_user
    mocked_text = "Hello from mock agent"
    mock_get_agent_graph.return_value = {
        "graph": create_mock_llm(mocked_text),
        "messages": [],
        "final_agent_name": "MockAgent",
        "final_agent_id": "mock-agent-id"
    }

    query = {"query": "Hello world"}
    with TestClient(app) as client:
        resp = client.post("/ask", headers=auth_header(token), json=query)

    assert resp.status_code == 200
    assert strip_agent_metadata(resp.text) == mocked_text

    session = sessions_db.find_one({"user_id": user_id})
    assert session is not None
    assert session["chat_history"][0]["assistant"] == mocked_text

@patch("api.routes.agents.get_agent_graph", new_callable=AsyncMock)
def test_update_existing_session(mock_get_agent_graph, authenticated_user):
    """Test that /ask updates an existing session with a new message."""
    token, user_id = authenticated_user
    session_id = "existing-session"
    initial_history = [{"user": "First question", "assistant": "First answer"}]
    sessions_db.insert_one({"session_id": session_id, "user_id": user_id, "chat_history": initial_history})

    mocked_text = "Second answer"
    mock_get_agent_graph.return_value = {
        "graph": create_mock_llm(mocked_text),
        "messages": [],
        "final_agent_name": "MockAgent",
        "final_agent_id": "mock-agent-id"
    }

    query = {"query": "Second question", "session_id": session_id}
    with TestClient(app) as client:
        resp = client.post("/ask", headers=auth_header(token), json=query)

    assert resp.status_code == 200
    assert strip_agent_metadata(resp.text) == mocked_text

    session = sessions_db.find_one({"session_id": session_id})
    assert len(session["chat_history"]) == 2
    assert session["chat_history"][1]["assistant"] == mocked_text

def test_list_user_sessions(authenticated_user):
    """Test listing all sessions for a user."""
    token, user_id = authenticated_user
    sessions_db.insert_many([
        {"session_id": "s1", "user_id": user_id, "chat_history": []},
        {"session_id": "s2", "user_id": user_id, "chat_history": []},
        {"session_id": "other", "user_id": "other_id", "chat_history": []}
    ])

    resp = client.get("/sessions", headers=auth_header(token))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert set(session["session_id"] for session in data) == {"s1", "s2"}

@patch("api.routes.agents.get_agent_graph", new_callable=AsyncMock)
def test_get_specific_session(mock_get_agent_graph, authenticated_user):
    """Test retrieving a specific session by session_id."""
    token, user_id = authenticated_user
    session_id = "specific-session"
    chat_history = [{"user": "q", "assistant": "a", "agent_name": "AgentX", "agent_id": "123"}]
    sessions_db.insert_one({"session_id": session_id, "user_id": user_id, "chat_history": chat_history})

    # Patch LLM for completeness
    mock_get_agent_graph.return_value = {
        "graph": create_mock_llm("ignored"),
        "messages": [],
        "final_agent_name": "MockAgent",
        "final_agent_id": "mock-agent-id"
    }

    resp = client.get(f"/sessions/{session_id}", headers=auth_header(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session_id
    assert data["chat_history"] == chat_history

def test_delete_user_session(authenticated_user):
    """Test deleting a specific session by session_id."""
    token, user_id = authenticated_user
    session_id = "delete-session"
    sessions_db.insert_one({"session_id": session_id, "user_id": user_id})
    assert sessions_db.count_documents({"session_id": session_id}) == 1

    resp = client.delete(f"/sessions/{session_id}", headers=auth_header(token))
    assert resp.status_code == 200
    assert "deleted successfully" in resp.json()["message"]
    assert sessions_db.count_documents({"session_id": session_id}) == 0