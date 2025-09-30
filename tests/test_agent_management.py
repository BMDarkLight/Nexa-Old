import pytest
from fastapi.testclient import TestClient
from bson import ObjectId

from api.main import app, pwd_context
from api.database import users_db, orgs_db, agents_db, connectors_db

client = TestClient(app)

# --- FIX: Changed scope to "function" for complete test isolation ---
@pytest.fixture(scope="function", autouse=True)
def setup_and_teardown_db():
    users_db.delete_many({})
    orgs_db.delete_many({})
    agents_db.delete_many({})
    connectors_db.delete_many({})
    yield
    users_db.delete_many({})
    orgs_db.delete_many({})
    agents_db.delete_many({})
    connectors_db.delete_many({})

# --- FIX: Changed scope to "function" to match the database fixture ---
@pytest.fixture(scope="function")
def org_admin_token():
    org = orgs_db.insert_one({"name": "AgentManagementTestCorp"})
    org_id = org.inserted_id
    
    user_doc = {
        "_id": ObjectId(),
        "username": "test_agent_admin",
        "password": pwd_context.hash("agentadminpass"),
        "permission": "orgadmin",
        "status": "active",
        "organization": org_id
    }
    users_db.insert_one(user_doc)
    orgs_db.update_one({"_id": org_id}, {"$set": {"owner": user_doc["_id"]}})

    resp = client.post("/signin", data={"username": "test_agent_admin", "password": "agentadminpass"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    
    return token, org_id

# --- FIX: Changed scope to "function" ---
@pytest.fixture(scope="function")
def regular_user_token(org_admin_token):
    _, org_id = org_admin_token
    
    user_doc = {
        "username": "test_agent_user",
        "password": pwd_context.hash("agentuserpass"),
        "permission": "orguser",
        "status": "active",
        "organization": org_id
    }
    users_db.insert_one(user_doc)

    resp = client.post("/signin", data={"username": "test_agent_user", "password": "agentuserpass"})
    assert resp.status_code == 200
    return resp.json()["access_token"]

@pytest.fixture
def sample_connector(org_admin_token):
    _, org_id = org_admin_token
    connector_doc = {
        "name": "Sample Connector for Agent Test",
        "org": org_id,
        "connector_type": "google_sheet",
        "settings": {"id": "123"}
    }
    result = connectors_db.insert_one(connector_doc)
    return str(result.inserted_id)

def auth_header(token):
    return {"Authorization": f"Bearer {token}"}

def test_create_agent_without_connectors(org_admin_token):
    token, _ = org_admin_token
    agent_payload = {
        "name": "Sales Assistant",
        "description": "Helps with sales inquiries.",
        "model": "gpt-4o",
        "tools": ["search_web"]
    }
    
    resp = client.post("/agents", headers=auth_header(token), json=agent_payload)
    
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Sales Assistant"
    assert "search_web" in data["tools"]
    assert data["connector_ids"] == []

def test_create_agent_with_valid_connector(org_admin_token, sample_connector):
    token, _ = org_admin_token
    agent_payload = {
        "name": "Connector Agent",
        "description": "Agent that uses a connector.",
        "model": "gpt-4",
        "connector_ids": [sample_connector]
    }
    
    resp = client.post("/agents", headers=auth_header(token), json=agent_payload)
    
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Connector Agent"
    assert data["connector_ids"] == [sample_connector]

def test_create_agent_with_invalid_connector(org_admin_token):
    token, _ = org_admin_token
    invalid_id = str(ObjectId())
    agent_payload = {
        "name": "Invalid Agent",
        "description": "Should fail creation.",
        "model": "gpt-4",
        "connector_ids": [invalid_id]
    }
    
    resp = client.post("/agents", headers=auth_header(token), json=agent_payload)
    
    assert resp.status_code == 404
    assert f"Connector with ID {invalid_id} not found" in resp.json()["detail"]

def test_regular_user_cannot_create_agent(regular_user_token):
    agent_payload = {"name": "Unauthorized Agent", "description": "No create.", "model": "gpt-3.5-turbo"}
    resp = client.post("/agents", headers=auth_header(regular_user_token), json=agent_payload)
    assert resp.status_code == 403

