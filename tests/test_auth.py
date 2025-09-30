import pytest
from fastapi.testclient import TestClient
from bson import ObjectId

from api.main import app, pwd_context
from api.database import users_db, prospective_users_db, orgs_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def cleanup_db():
    users_db.delete_many({})
    prospective_users_db.delete_many({})
    orgs_db.delete_many({})
    yield
    users_db.delete_many({})
    prospective_users_db.delete_many({})
    orgs_db.delete_many({})

def auth_header(token):
    """Helper function to create authorization headers."""
    return {"Authorization": f"Bearer {token}"}

# --- Test Functions ---
def test_public_endpoints():
    """Tests that public-facing endpoints are accessible without a token."""
    assert client.get("/").status_code == 200
    assert client.post("/signin", data={"username": "dne", "password": "dne"}).status_code == 401

def test_user_signup_creates_prospective_user():
    """Tests that the /signup endpoint correctly creates a user in the prospect list."""
    signup_payload = {
        "username": "new_prospect", "password": "password123",
        "organization": "NewOrg", "email": "prospect@neworg.com"
    }
    resp = client.post("/signup", json=signup_payload)
    
    # Assert successful response
    assert resp.status_code == 200
    assert "prospect list" in resp.json()["message"]
    
    # Assert user is in the correct database and state
    assert prospective_users_db.count_documents({"username": "new_prospect"}) == 1
    assert users_db.count_documents({"username": "new_prospect"}) == 0
    assert orgs_db.count_documents({"name": "NewOrg"}) == 1

def test_valid_user_signin():
    """Tests that a fully approved user can successfully sign in."""
    # Setup: Manually create an approved user in the database
    users_db.insert_one({
        "username": "approved_user",
        "password": pwd_context.hash("strongpassword"),
        "permission": "orguser",
        "status": "active"
    })
    
    # Action: Attempt to sign in
    resp = client.post("/signin", data={"username": "approved_user", "password": "strongpassword"})
    
    # Assert successful sign-in and token receipt
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_sysadmin_can_approve_user():
    """Tests a sysadmin's ability to approve a prospective user."""
    # Setup 1: Create a prospective user with all required fields
    prospective_users_db.insert_one({
        "username": "user_to_approve",
        "password": "some_password_hash",
        "firstname": "Test",
        "lastname": "User",
        "email": "approve@test.com",
        "phone": "0000000000",
        "permission": "orgadmin",
        "organization": ObjectId()
    })
    
    # Setup 2: Create and sign in as a sysadmin
    users_db.insert_one({
        "username": "sysadmin_test",
        "password": pwd_context.hash("syspass"),
        "permission": "sysadmin"
    })
    signin_resp = client.post("/signin", data={"username": "sysadmin_test", "password": "syspass"})
    sys_token = signin_resp.json()["access_token"]
    
    # Action: Sysadmin approves the user
    approve_resp = client.post("/signup/approve/user_to_approve", headers=auth_header(sys_token))
    
    # Assert successful approval
    assert approve_resp.status_code == 200
    
    # Assert user has been moved from prospective to main users database
    assert prospective_users_db.count_documents({"username": "user_to_approve"}) == 0
    assert users_db.count_documents({"username": "user_to_approve"}) == 1

def test_non_sysadmin_cannot_approve_user():
    """Tests that a regular user cannot approve a prospective user."""
    # Setup 1: Create a prospective user
    prospective_users_db.insert_one({"username": "another_prospect"})
    
    # Setup 2: Create and sign in as a regular user
    users_db.insert_one({
        "username": "regular_user",
        "password": pwd_context.hash("userpass"),
        "permission": "orguser" # Not a sysadmin
    })
    signin_resp = client.post("/signin", data={"username": "regular_user", "password": "userpass"})
    user_token = signin_resp.json()["access_token"]
    
    # Action: Regular user attempts to approve
    approve_resp = client.post("/signup/approve/another_prospect", headers=auth_header(user_token))
    
    # Assert permission is denied
    assert approve_resp.status_code == 403