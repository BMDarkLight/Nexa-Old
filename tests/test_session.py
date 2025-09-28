import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import asyncio

from api.main import app, pwd_context
from api.auth import users_db
from api.agent import sessions_db

client = TestClient(app)

# --- Fixtures ---
@pytest.fixture(autouse=True)
def cleanup_db():
    """Clean database before and after each test."""
    users_db.delete_many({})
    sessions_db.delete_many({})
    yield
    users_db.delete_many({})
    sessions_db.delete_many({})

@pytest.fixture
def authenticated_user_token():
    """Create a test user and return auth token and user_id."""
    password = "testpassword123"
    user_doc = {
        "username": "test_session_user",
        "password": pwd_context.hash(password),
        "permission": "orguser",
        "status": "active",
        "organization": "test_org_id"
    }
    result = users_db.insert_one(user_doc)
    user_id = result.inserted_id

    resp = client.post("/signin", data={"username": user_doc["username"], "password": password})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    
    return token, str(user_id)

def auth_header(token):
    return {"Authorization": f"Bearer {token}"}

def strip_metadata(text: str) -> str:
    lines = text.splitlines()
    if len(lines) > 1 and lines[0].startswith("[Agent:"):
        return "\n".join(lines[1:]).strip()
    return text.strip()

def create_mock_llm_stream(text_response: str):
    """Creates a mock LLM that streams dictionary content."""
    mock_llm = AsyncMock()
    
    async def mock_astream(*args, **kwargs):
        # Yield a single chunk containing the whole response
        yield {"content": text_response}
        await asyncio.sleep(0)
    
    mock_llm.astream = mock_astream
    return mock_llm

# --- Tests ---

@patch('api.main.get_agent_graph', new_callable=AsyncMock)
def test_ask_creates_new_session_with_stream(mock_get_agent_graph, authenticated_user_token):
    mocked_response_text = "Streamed response"
    mock_llm = create_mock_llm_stream(mocked_response_text)
    mock_get_agent_graph.return_value = {
        "graph": mock_llm,
        "messages": [],
        "final_agent_name": "MockAgent",
        "final_agent_id": "mock-agent-id"
    }

    token, user_id = authenticated_user_token
    query_payload = {"query": "Hello, world!"}

    with TestClient(app) as client:
        resp = client.post("/ask", headers=auth_header(token), json=query_payload)

    assert resp.status_code == 200
    assert strip_metadata(resp.text) == mocked_response_text
    session_doc = sessions_db.find_one({"user_id": user_id})
    assert session_doc is not None
    assert session_doc["chat_history"][0]["assistant"] == mocked_response_text

@patch('api.main.get_agent_graph', new_callable=AsyncMock)
def test_ask_updates_existing_session_with_stream(mock_get_agent_graph, authenticated_user_token):
    token, user_id = authenticated_user_token
    session_id = "test-session-123"
    initial_history = [{"user": "First question", "assistant": "First answer"}]
    sessions_db.insert_one({"session_id": session_id, "user_id": user_id, "chat_history": initial_history})

    mocked_response_text = "Second response"
    mock_llm = create_mock_llm_stream(mocked_response_text)
    mock_get_agent_graph.return_value = {
        "graph": mock_llm,
        "messages": [],
        "final_agent_name": "MockAgent",
        "final_agent_id": "mock-agent-id"
    }

    query_payload = {"query": "Second question", "session_id": session_id}
    with TestClient(app) as client:
        resp = client.post("/ask", headers=auth_header(token), json=query_payload)

    assert resp.status_code == 200
    assert strip_metadata(resp.text) == mocked_response_text
    session_doc = sessions_db.find_one({"session_id": session_id})
    assert len(session_doc["chat_history"]) == 2
    assert session_doc["chat_history"][1]["assistant"] == mocked_response_text

def test_list_sessions_for_user(authenticated_user_token):
    token, user_id = authenticated_user_token
    sessions_db.insert_many([
        {"session_id": "s1", "user_id": user_id, "chat_history": []},
        {"session_id": "s2", "user_id": user_id, "chat_history": []},
        {"session_id": "other", "user_id": "other_id", "chat_history": []}
    ])
    resp = client.get("/sessions", headers=auth_header(token))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert set(s["session_id"] for s in data) == {"s1", "s2"}

@patch('api.main.ChatOpenAI')
def test_get_specific_session(MockChatOpenAI, authenticated_user_token):
    mock_instance = MockChatOpenAI.return_value
    mock_instance.invoke.return_value.content = "Mocked Title"

    token, user_id = authenticated_user_token
    session_id = "my-session"
    chat_history = [{"user": "q", "assistant": "a", "agent_name": "Test", "agent_id": "123"}]
    sessions_db.insert_one({"session_id": session_id, "user_id": user_id, "chat_history": chat_history})

    resp = client.get(f"/sessions/{session_id}", headers=auth_header(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session_id
    assert data["chat_history"] == chat_history

def test_delete_session(authenticated_user_token):
    token, user_id = authenticated_user_token
    session_id = "del-session"
    sessions_db.insert_one({"session_id": session_id, "user_id": user_id})
    assert sessions_db.count_documents({"session_id": session_id}) == 1

    resp = client.delete(f"/sessions/{session_id}", headers=auth_header(token))
    assert resp.status_code == 200
    assert "deleted successfully" in resp.json()["message"]
    assert sessions_db.count_documents({"session_id": session_id}) == 0