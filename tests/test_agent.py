import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock
from bson import ObjectId
import uuid

# Assuming your app and dbs are accessible for testing
from api.main import app, pwd_context
from api.auth import users_db, orgs_db
from api.agent import sessions_db

# Use the TestClient for making requests to your FastAPI app
client = TestClient(app)

def strip_metadata(text: str) -> str:
    """Strip the metadata line '[Agent: ... | Session: ...]' from the response text and strip whitespace."""
    lines = text.splitlines()
    if lines and lines[0].startswith("[Agent:"):
        return "\n".join(lines[1:]).strip()
    return text.strip()

# --- Fixtures ---

@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown_db():
    """A fixture to clean the database before and after all tests in this module."""
    users_db.delete_many({})
    orgs_db.delete_many({})
    sessions_db.delete_many({})
    yield
    users_db.delete_many({})
    orgs_db.delete_many({})
    sessions_db.delete_many({})

@pytest.fixture(scope="module")
def test_user():
    """Creates a test organization and a standard user, returning the user document."""
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
    """Signs in the test user and returns a valid auth token."""
    resp = client.post("/signin", data={"username": test_user["username"], "password": "testpass"})
    assert resp.status_code == 200
    return resp.json()["access_token"]

@pytest.fixture(autouse=True)
def mock_llm_call(monkeypatch):
    """
    Mocks the get_agent_components function to prevent real LLM calls.
    This fixture now correctly simulates an async stream.
    """
    async def mock_get_agent_components(*args, **kwargs):
        # Use a standard MagicMock for the llm object
        mock_llm = MagicMock()

        # This is an async generator that yields mock chunks
        async def async_iterator():
            yield MagicMock(content="Mocked ")
            yield MagicMock(content="Response")

        # Set the 'astream' method's return_value to be the async iterator
        mock_llm.astream.return_value = async_iterator()
        
        return mock_llm, [], "Mocked Agent", str(ObjectId())

    # Use monkeypatch to replace the function where it's used in the app's code.
    monkeypatch.setattr("api.main.get_agent_components", mock_get_agent_components)


def auth_header(token):
    """Helper function to create authorization headers."""
    return {"Authorization": f"Bearer {token}"}

# --- Test Cases ---

def test_ask_new_session(test_user_token, test_user):
    """Tests that a new session is created and history is saved on the first /ask call."""
    resp = client.post(
        "/ask",
        headers=auth_header(test_user_token),
        json={"query": "Hello there"}
    )
    
    assert resp.status_code == 200
    response_text = strip_metadata(resp.text)
    assert response_text == "Mocked Response"
    
    # Since the session ID is no longer in headers, find the session by user and chat history
    session_doc = sessions_db.find_one({"user_id": str(test_user["_id"]), "chat_history.0.user": "Hello there"})
    assert session_doc is not None
    assert len(session_doc["chat_history"]) == 1
    assert session_doc["chat_history"][0]["user"] == "Hello there"
    assert session_doc["chat_history"][0]["assistant"] == "Mocked Response"

def test_ask_existing_session(test_user_token, test_user):
    """Tests that /ask correctly appends to an existing session's chat history."""
    session_id = str(uuid.uuid4())
    initial_history = [{
        "user": "Initial question", "assistant": "Initial answer",
        "agent_id": "some_agent", "agent_name": "Some Agent"
    }]
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

def test_ask_permission_denied_for_other_user_session(test_user_token):
    """Ensures a user cannot access a session belonging to another user."""
    session_id = str(uuid.uuid4())
    sessions_db.insert_one({
        "session_id": session_id,
        "user_id": str(ObjectId()),  # A different user's ID
        "chat_history": []
    })

    resp = client.post(
        "/ask",
        headers=auth_header(test_user_token),
        json={"query": "Trying to access", "session_id": session_id}
    )
    
    assert resp.status_code == 403

def test_regenerate_message_success(test_user_token, test_user):
    """Tests that regeneration correctly replaces the last message in the history."""
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
        data={"session_id": session_id}
    )

    assert resp.status_code == 200
    
    session_doc = sessions_db.find_one({"session_id": session_id})
    assert len(session_doc["chat_history"]) == 2
    assert session_doc["chat_history"][0]["user"] == "Question 1"
    assert session_doc["chat_history"][1]["user"] == "Question 2"
    assert session_doc["chat_history"][1]["assistant"] == "Mocked Response"

def test_edit_message_success(test_user_token, test_user):
    """Tests that editing a message updates the correct entry and regenerates a response."""
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
        data={"query": "Edited Question", "session_id": session_id}
    )

    assert resp.status_code == 200
    
    session_doc = sessions_db.find_one({"session_id": session_id})
    assert len(session_doc["chat_history"]) == 2
    assert session_doc["chat_history"][0]["user"] == "Edited Question"
    assert session_doc["chat_history"][0]["assistant"] == "Mocked Response"
    assert session_doc["chat_history"][1]["user"] == "Another Question"
