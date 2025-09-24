import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
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

# The patch target is updated to the new async function
@patch('api.main.get_agent_components')
def test_ask_creates_new_session_with_stream(mock_get_agent_components, authenticated_user_token):
    """
    Tests that calling /ask without a session_id creates a new session
    and returns a streaming response.
    """
    mocked_response_text = "This is a streamed response."
    mock_llm = create_mock_llm_stream(mocked_response_text)
    
    # Setup: Mock the new function's return value (a tuple of components)
    mock_get_agent_components.return_value = (
        mock_llm, [], "MockAgent", "mock-agent-id"
    )
    
    token, user_id = authenticated_user_token
    query_payload = {"query": "Hello, world!"}
    
    # Action: Use a context manager to ensure background tasks are executed
    with TestClient(app) as client:
        resp = client.post("/ask", headers=auth_header(token), json=query_payload)
    
    # Assertions for the streaming response
    assert resp.status_code == 200
    # The response body includes metadata in the first line
    stripped_text = strip_metadata(resp.text)
    assert stripped_text == mocked_response_text 
    # Check for metadata in headers
    # assert resp.headers["x-agent-name"] == "MockAgent"  # Removed as per instructions

    # Verify a new session was created in the background
    assert sessions_db.count_documents({}) == 1
    session = sessions_db.find_one()
    assert session["user_id"] == user_id
    assert len(session["chat_history"]) == 1
    assert session["chat_history"][0]["user"] == "Hello, world!"
    assert session["chat_history"][0]["assistant"] == mocked_response_text


@patch('api.main.get_agent_components')
def test_ask_updates_existing_session_with_stream(mock_get_agent_components, authenticated_user_token):
    """
    Tests that calling /ask with an existing session_id correctly appends
    to the chat history after streaming.
    """
    token, user_id = authenticated_user_token
    session_id = "test-session-123"
    
    # Setup 1: Manually create an existing session for the user
    initial_history = [{"user": "First question", "assistant": "First answer"}]
    sessions_db.insert_one({
        "session_id": session_id,
        "user_id": user_id,
        "chat_history": initial_history
    })

    # Setup 2: Mock the agent components and stream
    mocked_response_text = "This is the second response."
    mock_llm = create_mock_llm_stream(mocked_response_text)
    mock_get_agent_components.return_value = (
        mock_llm, [], "MockAgent", "mock-agent-id"
    )
    
    query_payload = {"query": "Second question", "session_id": session_id}
    
    # Action: Call the endpoint within a context manager
    with TestClient(app) as client:
        resp = client.post("/ask", headers=auth_header(token), json=query_payload)
    
    # Assertions
    assert resp.status_code == 200
    stripped_text = strip_metadata(resp.text)
    assert stripped_text == mocked_response_text
    
    # assert resp.headers["x-agent-name"] == "MockAgent"  # Removed as per instructions
    
    updated_session = sessions_db.find_one({"session_id": session_id})
    assert sessions_db.count_documents({}) == 1
    assert len(updated_session["chat_history"]) == 2 
    assert updated_session["chat_history"][0] == initial_history[0]
    assert updated_session["chat_history"][1]["user"] == "Second question"
    assert updated_session["chat_history"][1]["assistant"] == mocked_response_text


# The following tests do not interact with the /ask endpoint and need no changes.

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