import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from api.main import app, pwd_context
from api.auth import users_db
from api.agent import sessions_db

# The TestClient automatically handles the async nature of your app
client = TestClient(app)

# --- Fixtures ---
@pytest.fixture(autouse=True)
def cleanup_db():
    """A fixture to automatically clean the database before and after each test."""
    users_db.delete_many({})
    sessions_db.delete_many({})
    yield
    users_db.delete_many({})
    sessions_db.delete_many({})

@pytest.fixture
def authenticated_user_token():
    """
    Creates a user, saves it to the DB, and returns a valid auth token and user ID.
    """
    password = "testpassword123"
    user_doc = {
        "username": "test_session_user",
        "password": pwd_context.hash(password),
        "permission": "orguser",
        "status": "active",
        # The /ask endpoint requires an organization
        "organization": "test_org_id" 
    }
    result = users_db.insert_one(user_doc)
    user_id = result.inserted_id

    resp = client.post("/signin", data={"username": user_doc["username"], "password": password})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    
    return token, str(user_id)

def auth_header(token):
    """Helper function to create authorization headers."""
    return {"Authorization": f"Bearer {token}"}

# --- Helper for Mocking Streams ---
def create_mock_llm_stream(text_response: str):
    """Creates a mock LLM object with a fake async stream method."""
    mock_llm = MagicMock()
    
    # This async generator simulates the behavior of LangChain's astream()
    async def mock_astream_generator(*args, **kwargs):
        for char in text_response:
            # Each chunk from the stream is an object with a 'content' attribute
            yield MagicMock(content=char)
            await asyncio.sleep(0) # Yield control to the event loop

    mock_llm.astream = mock_astream_generator
    return mock_llm

def strip_metadata(text: str) -> str:
    """
    Removes the first line of metadata from the response text and strips leading/trailing whitespace.
    """
    lines = text.splitlines()
    if len(lines) > 1 and lines[0].startswith("[Agent:"):
        return "\n".join(lines[1:]).strip()
    return text.strip()

# --- Test Cases ---

@patch('api.main.get_agent_graph', new_callable=AsyncMock)
def test_ask_creates_new_session_with_stream(mock_get_agent_graph, authenticated_user_token):
    mocked_response_text = "This is a streamed response."

    class MockLLM:
        async def astream(self, messages):
            for char in mocked_response_text:
                yield type("Chunk", (), {"content": char})()
                await asyncio.sleep(0)

    mock_llm = MockLLM()
    mock_get_agent_graph.return_value = (mock_llm, [], "MockAgent", "mock-agent-id")

    token, user_id = authenticated_user_token
    query_payload = {"query": "Hello, world!"}

    with TestClient(app) as client:
        resp = client.post("/ask", headers=auth_header(token), json=query_payload)

    assert resp.status_code == 200
    stripped_text = strip_metadata(resp.text)
    assert stripped_text == mocked_response_text


@patch('api.main.get_agent_graph', new_callable=AsyncMock)
def test_ask_updates_existing_session_with_stream(mock_get_agent_graph, authenticated_user_token):
    token, user_id = authenticated_user_token
    session_id = "test-session-123"

    initial_history = [{"user": "First question", "assistant": "First answer"}]
    sessions_db.insert_one({
        "session_id": session_id,
        "user_id": user_id,
        "chat_history": initial_history
    })

    mocked_response_text = "This is the second response."

    class MockLLM:
        async def astream(self, messages):
            for char in mocked_response_text:
                yield type("Chunk", (), {"content": char})()
                await asyncio.sleep(0)

    mock_llm = MockLLM()
    mock_get_agent_graph.return_value = (mock_llm, [], "MockAgent", "mock-agent-id")

    query_payload = {"query": "Second question", "session_id": session_id}

    with TestClient(app) as client:
        resp = client.post("/ask", headers=auth_header(token), json=query_payload)

    assert resp.status_code == 200
    stripped_text = strip_metadata(resp.text)
    assert stripped_text == mocked_response_text

def test_list_sessions_for_user(authenticated_user_token):
    """
    Tests that the /sessions endpoint returns only the sessions for the authenticated user.
    """
    token, user_id = authenticated_user_token
    
    sessions_db.insert_one({"session_id": "user1-session1", "user_id": user_id, "chat_history": []})
    sessions_db.insert_one({"session_id": "user1-session2", "user_id": user_id, "chat_history": []})
    sessions_db.insert_one({"session_id": "user2-session1", "user_id": "other_user_id", "chat_history": []})
    
    resp = client.get("/sessions", headers=auth_header(token))
    
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    session_ids = {s["session_id"] for s in data}
    assert "user1-session1" in session_ids
    assert "user1-session2" in session_ids


@patch('api.main.ChatOpenAI')
def test_get_specific_session(MockChatOpenAI, authenticated_user_token):
    """
    Tests retrieving a single, specific session by its ID.
    """
    mock_instance = MockChatOpenAI.return_value
    mock_instance.invoke.return_value.content = "Mocked Session Title"

    token, user_id = authenticated_user_token
    session_id = "my-specific-session"
    chat_history = [{"user": "question", "assistant": "answer", "agent_name": "Test", "agent_id": "123"}]
    
    sessions_db.insert_one({
        "session_id": session_id,
        "user_id": user_id,
        "chat_history": chat_history
    })
    
    resp = client.get(f"/sessions/{session_id}", headers=auth_header(token))
    
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session_id
    assert data["chat_history"] == chat_history


def test_delete_session(authenticated_user_token):
    """
    Tests that a user can delete their own session.
    """
    token, user_id = authenticated_user_token
    session_id = "session-to-delete"
    
    sessions_db.insert_one({"session_id": session_id, "user_id": user_id})
    assert sessions_db.count_documents({"session_id": session_id}) == 1
    
    resp = client.delete(f"/sessions/{session_id}", headers=auth_header(token))
    
    assert resp.status_code == 200
    assert "deleted successfully" in resp.json()["message"]
    assert sessions_db.count_documents({"session_id": session_id}) == 0