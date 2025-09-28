from fastapi import FastAPI, HTTPException, Request, Depends, BackgroundTasks, File, UploadFile
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from passlib.context import CryptContext
from dotenv import load_dotenv, find_dotenv
from typing import List, Optional, Literal
from pydantic import BaseModel
from bson import ObjectId

from api.auth import create_access_token, verify_token, prospective_users_db, users_db, orgs_db
from api.mail import send_email

import datetime
import secrets

app = FastAPI(title="Nexa API")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/signin")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv(dotenv_path=find_dotenv())

# --- Authorization Compatible Swagger UI ---
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Nexa API",
        version="1.0.0",
        description="Gen-AI for Organizations. Streamline all workflows across messenger, workspaces and organizational system in one place, and make them smart using AI.",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "OAuth2Password": {
            "type": "oauth2",
            "flows": {
                "password": {
                    "tokenUrl": "/signin",
                    "scopes": {}
                }
            }
        },
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    public_paths = {"/signin", "/signup", "/test-cors", "/", "/forgot-password", "/reset-password", "/check-reset-token", "/invite/signup/{username}"}
    for path_name, path in openapi_schema["paths"].items():
        if path_name in public_paths:
            continue
        for operation in path.values():
            operation["security"] = [{"OAuth2Password": []}, {"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# --- Database Initialization ---
import os
import secrets
import datetime

def hash_password(password: str) -> str:
    pw_bytes = password.encode("utf-8")[:72]
    return pwd_context.hash(pw_bytes)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    pw_bytes = plain_password.encode("utf-8")[:72]
    try:
        return pwd_context.verify(pw_bytes, hashed_password)
    except Exception:
        return False

def create_initial_sysadmin():
    if users_db.count_documents({"permission": "sysadmin"}) < 1:
        username = os.getenv("SYSADMIN_USERNAME")
        password = os.getenv("SYSADMIN_PASSWORD")
        firstname = os.getenv("SYSADMIN_FIRSTNAME", "")
        lastname = os.getenv("SYSADMIN_LASTNAME", "")
        email = os.getenv("SYSADMIN_EMAIL", "")
        phone = os.getenv("SYSADMIN_PHONE", "")
        if not username or not password:
            print("SYSADMIN_USERNAME or SYSADMIN_PASSWORD not set in env; skipping sysadmin creation")
            return
        hashed_password = hash_password(password)
        now = datetime.datetime.now(datetime.timezone.utc)
        user = {
            "username": username,
            "password": hashed_password,
            "firstname": firstname,
            "lastname": lastname,
            "email": email,
            "phone": phone,
            "created_at": now,
            "updated_at": now,
            "permission": "sysadmin",
        }
        user_result = users_db.insert_one(user)
        if user_result.acknowledged:
            print(f"Created initial sysadmin user: {username}")
        else:
            print("Failed to create initial sysadmin user")

create_initial_sysadmin()

SERVER_URL = os.getenv("SERVER_URL", "http://localhost")
UI_PORT = os.getenv("UI_PORT", "3000")
API_PORT = os.getenv("API_PORT", "8000")

# --- Home Page ---
@app.get("/", response_class=HTMLResponse)
async def main_page():
    with open("api/static/home.html", "r", encoding="utf-8") as f:
        html_content = f.read()

    return HTMLResponse(content=html_content)


# --- Authentication Routes ---
class SignupModel(BaseModel):
    username: str
    password: str
    firstname: str = ""
    lastname: str = ""
    email: str = ""
    phone: str = ""
    organization: str
    plan: str = "free"

@app.post("/signup")
def signup(form_data: SignupModel):
    if users_db.find_one({"username":form_data.username}) or prospective_users_db.find_one({"username": form_data.username}):
        raise HTTPException(status_code=400, detail="User already exists")
    hashed_password = hash_password(form_data.password)
    if orgs_db.find_one({"name": form_data.organization}):
        raise HTTPException(status_code=400, detail="Organization already exists")
    now = datetime.datetime.now(datetime.timezone.utc)
    result = prospective_users_db.insert_one({
        "username": form_data.username,
        "password": hashed_password,
        "firstname": form_data.firstname,
        "lastname": form_data.lastname,
        "email": form_data.email,
        "phone": form_data.phone or "",
        "organization": None,
        "created_at": now,
        "updated_at": now,
        "permission": "orgadmin"
    })
    user_id = result.inserted_id
    result_org = orgs_db.insert_one({
        "name": form_data.organization,
        "owner": user_id,
        "users": [user_id],
        "description": "",
        "plan": form_data.plan or "free",
        "settings": {},
        "created_at": now,
        "updated_at": now
    })
    org_id = result_org.inserted_id
    prospective_users_db.update_one(
        {"_id": user_id},
        {"$set": {"organization": org_id}}
    )
    if not result.acknowledged:
        raise HTTPException(status_code=500, detail="User creation failed")
    if not result_org.acknowledged:
        raise HTTPException(status_code=500, detail="Organization creation failed")
    return {"message": "User successfully registered in prospect list", "_id": str(user_id)}

class SigninModel(BaseModel):
    username: str
    password: str

@app.post("/signin")
def signin(form_data: OAuth2PasswordRequestForm = Depends()):
    user = users_db.find_one({"username": form_data.username})
    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if user.get("status") == "pending":
        raise HTTPException(status_code=403, detail="User is pending approval")
    
    access_token = create_access_token(data={"sub": user["username"]})

    return {"access_token": access_token, "token_type": "bearer"}

class ForgotPasswordModel(BaseModel):
    username: str

class CheckResetTokenModel(BaseModel):
    username: str
    token: str

class ResetPasswordModel(BaseModel):
    username: str
    new_password: str
    token: str

@app.post("/forgot-password")
def forgot_password(form_data: ForgotPasswordModel, background_tasks: BackgroundTasks):
    username = form_data.username
    user = users_db.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    reset_token = secrets.token_urlsafe(16)
    users_db.update_one({"username": username}, {"$set": {"reset_token": reset_token}})
    
    reset_link = f"{SERVER_URL}:{UI_PORT}/reset-password?token={reset_token}&username={username}"
    
    if user["email"]:
        background_tasks.add_task(
            send_email,
            to_email=user["email"],
            subject="Password Reset Request",
            html_body=f"Click the link to reset your password: {reset_link}"
        )
    else:
        raise HTTPException(status_code=400, detail="User does not have an email set")
    
    return {"message": "Password reset link sent to your email"}

@app.post("/check-reset-token")
def check_reset_token(form_data: CheckResetTokenModel):
    username = form_data.username
    token = form_data.token
    user = users_db.find_one({"username": username, "reset_token": token})
    if not user:
        return {"message": "Invalid token", "valid": False}
    else:
        return {"message": "Token is valid", "valid": True}

@app.post("/reset-password")
def reset_password(form_data: ResetPasswordModel):
    username = form_data.username
    new_password = form_data.new_password
    token = form_data.token
    user = users_db.find_one({"username": username, "reset_token": token})
    if not user:
        raise HTTPException(status_code=404, detail="Invalid credentials")
    
    hashed_password = hash_password(new_password)
    now = datetime.datetime.now(datetime.timezone.utc)
    users_db.update_one(
        {"username": username},
        {
            "$set": {
                "password": hashed_password,
                "reset_token": None,
                "updated_at": now
            }
        }
    )
    return {"message": "Password reset successfully"}

# --- Prospective Users Routes ---
@app.post("/signup/approve/{username}")
def approve_signup(username: str, token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
    if user.get("permission") != "sysadmin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    prospective_user = prospective_users_db.find_one({"username": username})
    if not prospective_user:
        raise HTTPException(status_code=404, detail="Prospective user not found")
    
    if users_db.find_one({"username": username}):
        raise HTTPException(status_code=400, detail="User already exists")
    
    hashed_password = prospective_user["password"]
    now = datetime.datetime.now(datetime.timezone.utc)
    result = users_db.insert_one({
        "username": prospective_user["username"],
        "password": hashed_password,
        "firstname": prospective_user["firstname"],
        "lastname": prospective_user["lastname"],
        "email": prospective_user["email"],
        "phone": prospective_user["phone"],
        "organization": prospective_user["organization"],
        "created_at": now,
        "updated_at": now,
        "permission": prospective_user["permission"]
    })
    user_id = result.inserted_id
    orgs_db.update_one(
        {"_id": prospective_user["organization"]},
        {
            "$set": {"owner": user_id},
            "$addToSet": {"users": user_id}
        }
    )
    if not result.acknowledged:
        raise HTTPException(status_code=500, detail="User creation failed")
    
    prospective_users_db.delete_one({"username": username})

    return {"message": "User approved and created successfully", "_id": str(user_id)}

@app.post("/signup/reject/{username}")
def reject_signup(username: str, token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
    if user.get("permission") != "sysadmin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    prospective_user = prospective_users_db.find_one({"username": username})
    if not prospective_user:
        raise HTTPException(status_code=404, detail="Prospective user not found")
    
    org_result = orgs_db.delete_one({"_id": prospective_user["organization"]})
    result = prospective_users_db.delete_one({"username": username})
    if result.deleted_count == 0 or org_result.deleted_count == 0:
        raise HTTPException(status_code=500, detail="Failed to reject user")
    
    return {"message": "User rejected successfully"}

@app.get("/signup/prospective-users", response_model=List[dict])
def list_prospective_users(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
    if user.get("permission") != "sysadmin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    prospective_users = list(prospective_users_db.find({}, {"_id": 0, "password": 0}))
    return prospective_users

@app.get("/signup/prospective-users/{username}", response_model=dict)
def get_prospective_user(username: str, token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
    if user.get("permission") != "sysadmin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    prospective_user = prospective_users_db.find_one({"username": username}, {"_id": 0, "password": 0})

    if not prospective_user:
        raise HTTPException(status_code=404, detail="Prospective user not found")
    
    return prospective_user

# --- Organization Management Routes ---
class TransferOwnershipModel(BaseModel):
    new_owner_username: str

@app.get("/organizations", response_model=dict)
def organization(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
    if user.get("permission") != "sysadmin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    return orgs_db.find({}, {"_id": 0})

@app.get("/organizations/{name}", response_model=dict)
def get_organization(name: str, token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
    if user.get("permission") != "sysadmin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    organization = orgs_db.find_one({"name": name}, {"_id": 0})
    
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    return organization

@app.put("/organizations/{name}/transfer", status_code=200)
def transfer_organization_ownership(
    name: str,
    data: TransferOwnershipModel,
    token: str = Depends(oauth2_scheme)
):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        requester = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

    org_to_transfer = orgs_db.find_one({"name": name})
    if not org_to_transfer:
        raise HTTPException(status_code=404, detail=f"Organization '{name}' not found.")

    new_owner_doc = users_db.find_one({"username": data.new_owner_username})

    if not new_owner_doc:
        raise HTTPException(status_code=404, detail=f"User '{data.new_owner_username}' not found.")
    
    new_owner_id = new_owner_doc.get("_id")
    current_owner_id = org_to_transfer.get("owner")

    if current_owner_id == new_owner_id:
        raise HTTPException(status_code=400, detail="This user is already the owner of the organization.")

    if new_owner_id not in org_to_transfer.get("users", []):
        raise HTTPException(status_code=400, detail="The new owner must be an existing member of the organization.")
    
    is_sysadmin = requester.get("permission") == "sysadmin"
    is_current_owner = requester.get("_id") == str(current_owner_id)

    if not (is_sysadmin or is_current_owner):
        raise HTTPException(
            status_code=403,
            detail="Permission denied. Only the current owner or a sysadmin can transfer ownership."
        )

    try:
        orgs_db.update_one({"_id": org_to_transfer.get("_id")}, {"$set": {"owner": new_owner_id}})
        users_db.update_one({"_id": new_owner_id}, {"$set": {"permission": "orgadmin"}})
        users_db.update_one({"_id": current_owner_id}, {"$set": {"permission": "orgadmin"}})

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database Error: {e}"
        )

    return {
        "message": f"Ownership of organization '{name}' has been successfully transferred to '{data.new_owner_username}'."
    }

# --- Organization User Routes ---
@app.post("/invite/{username}")
def invite_user(username: str, email: str,  background_tasks: BackgroundTasks = None, token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
    if users_db.find_one({"username":username}) or prospective_users_db.find_one({"username": username}):
        raise HTTPException(status_code=400, detail="User already exists")

    if user.get("permission") != "orgadmin":
        raise HTTPException(status_code=403, detail="Permission denied")

    organization = orgs_db.find_one({"owner": ObjectId(user["_id"])})
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    invite_code = secrets.token_urlsafe(16)

    now = datetime.datetime.now(datetime.timezone.utc)
    users_db.insert_one({
        "username": username,
        "email": email,
        "organization": organization["_id"],
        "permission": "orguser",
        "invite_code": invite_code,
        "status": "pending",
        "created_at": now,
        "updated_at": now
    })

    background_tasks.add_task(
        send_email,
        to_email=email,
        subject="Invitation to Join Organization",
        html_body=(
            f"You have been invited to join the organization '{organization['name']}'. "
            f"Use the following invitation code to complete your signup:\n\n{invite_code}"
        )
    )

    return {"message": f"User '{username}' invited successfully"}

class InviteSignupModel(BaseModel):
    invite_code: str
    password: str
    firstname: str = ""
    lastname: str = ""
    phone: str = ""


@app.post("/invite/signup/{username}")
def invite_signin(
    form_data: InviteSignupModel,
    background_tasks: BackgroundTasks
):
    user = users_db.find_one({"invite_code": form_data.invite_code})
    if not user:
        raise HTTPException(status_code=404, detail="Invite not found")

    if user.get("password"):
        raise HTTPException(status_code=400, detail="User already has a password set")

    if user.get("status") != "pending":
        raise HTTPException(status_code=403, detail="User is not in pending status")

    username = user["username"]
    hashed_password = hash_password(form_data.password)
    now = datetime.datetime.now(datetime.timezone.utc)
    result = users_db.update_one(
        {"username": username},
        {
            "$set": {
                "password": hashed_password,
                "firstname": form_data.firstname,
                "lastname": form_data.lastname,
                "phone": form_data.phone or "",
                "status": "active",
                "updated_at": now
            },
            "$unset": {"invite_code": ""}
        }
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Failed to register invited user")

    orgadmin = users_db.find_one({
        "organization": user["organization"],
        "permission": "orgadmin"
    })
    organization = orgs_db.find_one({"_id": user["organization"]}) if user.get("organization") else None
    org_name = organization["name"] if organization and "name" in organization else "your organization"

    if orgadmin and orgadmin.get("email"):
        background_tasks.add_task(
            send_email,
            to_email=orgadmin["email"],
            subject=f"Invited user {user['username']} has signed up.",
            html_body=f"The user '{user['username']}' has completed their signup for the organization '{org_name}'."
        )

    if user.get("email"):
        background_tasks.add_task(
            send_email,
            to_email=user["email"],
            subject=f"Welcome to {org_name}",
            html_body=f"Your account has been successfully created, {form_data.firstname}!"
        )

    return {"message": "Invited user signed up successfully."}

# --- User Management Routes ---
class UserCreateModel(BaseModel):
    username : str
    password : str
    email : str
    permission: Literal['sysadmin', 'orgadmin', 'orguser'] = 'sysadmin'
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    phone: Optional[str] = None
    organization: Optional[str] = None
    plan: Optional[str] = "free"


class UserUpdateModel(BaseModel):
    username : str
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    organization: Optional[str] = None
    permission: Optional[str] = None

@app.get("/users", response_model=List[dict])
def list_users(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
    if user.get("permission") == "sysadmin":
        query = {}
    elif user.get("permission") == "orgadmin":
        query = {"organization": user.get("organization")}
    else:
        raise HTTPException(status_code=403, detail="Permission denied")

    users = list(users_db.find(query, {"_id": 0, "password": 0}))

    for user in users:
        if "organization" in user and isinstance(user.get("organization"), ObjectId):
            user["organization"] = str(user["organization"])

    return users

@app.post("/users")
def create_user(user: UserCreateModel, token: str = Depends(oauth2_scheme)):
    requester = verify_token(token)
    
    if requester.get("permission") != "sysadmin":
        raise HTTPException(status_code=403, detail="Permission denied. Sysadmin role required.")

    if users_db.find_one({"username": user.username}) or prospective_users_db.find_one({"username": user.username}):
        raise HTTPException(status_code=409, detail="User already exists.")
    
    now = datetime.datetime.now(datetime.timezone.utc)
    base_user_doc = {
        "username": user.username,
        "password": hash_password(user.password),
        "email": user.email,
        "firstname": user.firstname or "",
        "lastname": user.lastname or "",
        "phone": user.phone or "",
        "created_at": now,
        "updated_at": now
    }
    
    if user.permission == "sysadmin":
        user_doc = base_user_doc | {"permission": "sysadmin"}
        result = users_db.insert_one(user_doc)

        if not result.acknowledged:
            raise HTTPException(status_code=500, detail="Failed to create system admin user.")

    elif user.permission == "orgadmin":
        if not user.organization:
            raise HTTPException(status_code=400, detail="Organization name is required for an org admin.")
        
        if orgs_db.find_one({"name": user.organization}):
            raise HTTPException(status_code=409, detail="Organization already exists.")
        
        user_doc = base_user_doc | {"permission": "orgadmin"}
        user_result = users_db.insert_one(user_doc)
        
        if not user_result.acknowledged:
            raise HTTPException(status_code=500, detail="User creation phase failed for org admin.")
        
        user_id = user_result.inserted_id
        
        org_doc = {
            "name": user.organization,
            "owner": user_id, "users": [user_id], "description": "",
            "plan": user.plan or "free", "settings": {},
            "created_at": now, "updated_at": now
        }

        org_result = orgs_db.insert_one(org_doc)
        
        if not org_result.acknowledged:
            users_db.delete_one({"_id": user_id}) 
            raise HTTPException(status_code=500, detail="Organization creation failed. User creation has been rolled back.")

        org_id = org_result.inserted_id

        update_result = users_db.update_one({"_id": user_id}, {"$set": {"organization": org_id}})
        
        if update_result.modified_count != 1:
            users_db.delete_one({"_id": user_id})
            orgs_db.delete_one({"_id": org_id})
            raise HTTPException(status_code=500, detail="Failed to link user to organization. All changes have been rolled back.")

    elif user.permission == "orguser":
        if not user.organization:
            raise HTTPException(status_code=400, detail="Organization name is required for an org user.")
        
        org = orgs_db.find_one({"name": user.organization})

        if not org:
            raise HTTPException(status_code=404, detail=f"Organization '{user.organization}' not found.")
        
        user_doc = base_user_doc | {
            "permission": "orguser",
            "organization": org.get("_id")
        }
        result = users_db.insert_one(user_doc)
        if not result.acknowledged:
            raise HTTPException(status_code=500, detail="Failed to create organization user.")
    
    else:
        raise HTTPException(status_code=400, detail=f"Invalid user permission '{user.permission}' provided.")

    return {"status": "success", "message": f"User '{user.username}' created successfully."}

@app.get("/users/{username}")
def get_user(username: str, token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        user = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
    if not (user.get("permission") == "sysadmin" or user["username"] == username):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    user_data = users_db.find_one({"username": username}, {"_id": 0, "password": 0})

    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.get("permission") != "sysadmin" and user_data.get("organization") != user.get("organization"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    return user_data


@app.put("/users/{username}")
def update_user(
    update: UserUpdateModel,
    token: str = Depends(oauth2_scheme)
):
    username = update.username

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        current_user = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

    user_in_db = users_db.find_one({"username": username})
    if not user_in_db:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user.get("permission") == "sysadmin":
        allowed_fields = {"firstname", "lastname", "email", "phone", "organization", "permission"}
    elif current_user["username"] == username:
        allowed_fields = {"firstname", "lastname", "email", "phone"}
    else:
        raise HTTPException(status_code=403, detail="Permission denied")

    update_data = update.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if k in allowed_fields}
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid update fields provided")

    if "organization" in update_data:
        org_val = update_data["organization"]
        if org_val is not None:
            try:
                org_obj = ObjectId(org_val)
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid organization id format")
            
            if not orgs_db.find_one({"_id": org_obj}):
                raise HTTPException(status_code=404, detail="Organization not found")
            
            update_data["organization"] = org_obj

    if "permission" in update_data:
        if update_data["permission"] not in ["sysadmin", "orgadmin", "orguser"]:
            raise HTTPException(status_code=400, detail="Invalid permission value")

    update_data["updated_at"] = datetime.datetime.now(datetime.timezone.utc)
    result = users_db.update_one({"username": username}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    updated_user = users_db.find_one({"username": username}, {"_id": 0, "password": 0})
    if updated_user and "organization" in updated_user and isinstance(updated_user["organization"], ObjectId):
        updated_user["organization"] = str(updated_user["organization"])
    return {
        "message": f"User '{username}' updated successfully",
        "updated_user": updated_user
    }

@app.delete("/users/{username}", status_code=200)
def delete_user(username: str, token: str = Depends(oauth2_scheme)):
    try:
        current_user = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

    user_to_delete = users_db.find_one({"username": username})

    if not user_to_delete:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found.")

    is_sysadmin = current_user.get("permission") == "sysadmin"
    is_self_delete = current_user.get("username") == user_to_delete.get("username")
    is_orgadmin_deleting_member = (current_user.get("permission") == "orgadmin" and current_user.get("organization") == user_to_delete.get("organization"))

    if not (is_sysadmin or is_self_delete or is_orgadmin_deleting_member):
        raise HTTPException(status_code=403, detail="You do not have permission to delete this user.")

    if user_to_delete.get("permission") == "orgadmin":
        org = orgs_db.find_one({"owner": user_to_delete.get("_id")})
        if org:
            raise HTTPException(
                status_code=409,
                detail="This user owns an organization and cannot be deleted. Please transfer ownership first."
            )
    
    user_org_id = user_to_delete.get("organization")
    if user_org_id:
        orgs_db.update_one(
            {"_id": user_org_id},
            {"$pull": {"users": user_to_delete.get("_id")}}
        )

    result = users_db.delete_one({"_id": user_to_delete.get("_id")})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found, may have been deleted by another process.")

    return {"message": f"User '{username}' deleted."}

# --- Agent Routes ---
from api.agent import get_agent_graph, sessions_db, agents_db, connectors_db
import uuid
from fastapi import BackgroundTasks, Depends, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from bson import ObjectId
from api.auth import verify_token, oauth2_scheme

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    agent_id: Optional[str] = None

def save_chat_history(session_id: str, user_id: str, chat_history: list, query: str, answer: str, agent_id: str, agent_name: str):
    new_history_entry = {
        "user": query,
        "assistant": answer,
        "agent_id": agent_id,
        "agent_name": agent_name
    }
    updated_chat_history = chat_history + [new_history_entry]
    sessions_db.update_one(
        {"session_id": session_id},
        {"$set": {"chat_history": updated_chat_history, "user_id": user_id}},
        upsert=True
    )

def update_chat_history_entry(session_id: str, message_num: int, new_query: str, new_answer: str):
    sessions_db.update_one(
        {"session_id": session_id},
        {
            "$set": {
                f"chat_history.{message_num}.user": new_query,
                f"chat_history.{message_num}.assistant": new_answer,
            }
        }
    )

def replace_chat_history_from_point(session_id: str, user_id: str, truncated_history: list, query: str, new_answer: str, agent_id: str, agent_name: str):
    new_entry = {
        "user": query,
        "assistant": new_answer,
        "agent_id": agent_id,
        "agent_name": agent_name
    }
    final_history = truncated_history + [new_entry]
    sessions_db.update_one(
        {"session_id": session_id},
        {"$set": {"chat_history": final_history, "user_id": user_id}}
    )

@app.post("/ask")
async def ask(
    query: QueryRequest,
    background_tasks: BackgroundTasks,
    token: str = Depends(oauth2_scheme)
):
    user = verify_token(token)
    if not query.query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    agent_id_to_use = query.agent_id
    session_id = query.session_id or str(uuid.uuid4())
    session = sessions_db.find_one({"session_id": session_id})
    if session and session.get("user_id") != str(user["_id"]):
        raise HTTPException(status_code=403, detail="Permission denied for this session.")
    chat_history = session.get("chat_history", []) if session else []
    org_id = user.get("organization")

    try:
        agent_graph = await get_agent_graph(
            question=query.query,
            organization_id=org_id,
            chat_history=chat_history,
            agent_id=agent_id_to_use
        )
    except Exception:
        async def error_response():
            yield f"[Agent: Unknown | Session: {session_id}]\n\n"
            yield "Sorry, there was an error processing your request. Please try again later."
        return StreamingResponse(error_response(), media_type="text/plain; charset=utf-8")

    graph = agent_graph["graph"]
    messages = agent_graph["messages"]
    agent_name = agent_graph["final_agent_name"]
    agent_id = agent_graph["final_agent_id"]

    def map_type_to_role(msg_type):
        if msg_type is None:
            return "user"
        t = msg_type.lower()
        if t == "system":
            return "system"
        elif t == "assistant":
            return "assistant"
        elif t == "human":
            return "user"
        else:
            return t

    async def response_generator():
        yield f"[Agent: {agent_name} | Session: {session_id}]\n\n"
        full_answer = ""

        history_context = ""
        for entry in chat_history:
            user_msg = entry.get("user", "")
            assistant_msg = entry.get("assistant", "")
            if user_msg:
                history_context += f"User: {user_msg}\n"
            if assistant_msg:
                history_context += f"Assistant: {assistant_msg}\n"

        latest_message = None
        for msg in messages[::-1]:
            msg_type = msg.get("type") or msg.get("role")
            if msg_type and str(msg_type).lower() in ("user", "human"):
                latest_message = msg
                break
        if latest_message is None and messages:
            latest_message = messages[-1]

        if latest_message:
            role = map_type_to_role(latest_message.get("type") or latest_message.get("role"))
            content = (history_context + latest_message.get("content", "")).strip()
            astream_input = {"role": role, "content": content}
        else:
            astream_input = {"role": "user", "content": (history_context + query.query).strip()}

        async for chunk in graph.astream(astream_input):
            content = chunk.get("content", "")
            full_answer += content
            yield content

        background_tasks.add_task(
            save_chat_history,
            session_id=session_id,
            user_id=str(user["_id"]),
            chat_history=chat_history,
            query=query.query,
            answer=full_answer,
            agent_id=agent_id,
            agent_name=agent_name
        )

    return StreamingResponse(response_generator(), media_type="text/plain; charset=utf-8")

@app.post("/ask/regenerate/{message_num}")
async def regenerate(
    message_num: int,
    background_tasks: BackgroundTasks,
    request: Request,
    token: str = Depends(oauth2_scheme)
):
    data = await request.json()
    session_id = data.get("session_id")
    agent_id = data.get("agent_id")
    user = verify_token(token)
    session = sessions_db.find_one({"session_id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.get("user_id") != str(user["_id"]):
        raise HTTPException(status_code=403, detail="Permission denied for this session.")

    chat_history = session.get("chat_history", [])
    if message_num < 0 or message_num >= len(chat_history):
        raise HTTPException(status_code=400, detail="Invalid message number.")

    truncated_history = chat_history[:message_num]
    original_query = chat_history[message_num]['user']
    org_id = user.get("organization")

    try:
        agent_graph = await get_agent_graph(
            question=original_query,
            organization_id=org_id,
            chat_history=truncated_history,
            agent_id=agent_id
        )
    except Exception:
        async def error_response():
            yield f"[Agent: Unknown | Session: {session_id}]\n\n"
            yield "Sorry, there was an error processing your request. Please try again later."
        return StreamingResponse(error_response(), media_type="text/plain; charset=utf-8")

    graph = agent_graph["graph"]
    messages = agent_graph["messages"]
    agent_name = agent_graph["final_agent_name"]
    agent_id_str = agent_graph["final_agent_id"]

    def map_type_to_role(msg_type):
        if msg_type is None:
            return "user"
        t = msg_type.lower()
        if t == "system":
            return "system"
        elif t == "assistant":
            return "assistant"
        elif t == "human":
            return "user"
        else:
            return t

    async def response_generator():
        yield f"[Agent: {agent_name} | Session: {session_id}]\n\n"
        full_answer = ""

        history_context = ""
        for entry in truncated_history:
            user_msg = entry.get("user", "")
            assistant_msg = entry.get("assistant", "")
            if user_msg:
                history_context += f"User: {user_msg}\n"
            if assistant_msg:
                history_context += f"Assistant: {assistant_msg}\n"
        latest_message = None
        for msg in messages[::-1]:
            msg_type = msg.get("type") or msg.get("role")
            if msg_type and str(msg_type).lower() in ("user", "human"):
                latest_message = msg
                break
        if latest_message is None and messages:
            latest_message = messages[-1]
        if latest_message:
            role = map_type_to_role(latest_message.get("type") or latest_message.get("role"))
            content = (history_context + latest_message.get("content", "")).strip()
            astream_input = {"role": role, "content": content}
        else:
            astream_input = {"role": "user", "content": (history_context + original_query).strip()}

        async for chunk in graph.astream(astream_input):
            content = chunk.get("content", "")
            full_answer += content
            yield content

        background_tasks.add_task(
            replace_chat_history_from_point,
            session_id=session_id,
            user_id=str(user["_id"]),
            truncated_history=truncated_history,
            query=original_query,
            new_answer=full_answer,
            agent_id=agent_id_str,
            agent_name=agent_name
        )

    return StreamingResponse(response_generator(), media_type="text/plain; charset=utf-8")

@app.post("/ask/edit/{message_num}")
async def edit_message(
    message_num: int,
    background_tasks: BackgroundTasks,
    request: Request,
    token: str = Depends(oauth2_scheme)
):
    data = await request.json()
    query = data.get("query")
    session_id = data.get("session_id")
    agent_id = data.get("agent_id")
    user = verify_token(token)
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    session = sessions_db.find_one({"session_id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.get("user_id") != str(user["_id"]):
        raise HTTPException(status_code=403, detail="Permission denied for this session.")

    chat_history = session.get("chat_history", [])
    if message_num < 0 or message_num >= len(chat_history):
        raise HTTPException(status_code=400, detail="Invalid message number.")

    truncated_history = chat_history[:message_num]
    org_id = user.get("organization")

    try:
        agent_graph = await get_agent_graph(
            question=query,
            organization_id=org_id,
            chat_history=truncated_history,
            agent_id=agent_id
        )
    except Exception:
        async def error_response():
            yield f"[Agent: Unknown | Session: {session_id}]\n\n"
            yield "Sorry, there was an error processing your request. Please try again later."
        return StreamingResponse(error_response(), media_type="text/plain; charset=utf-8")

    graph = agent_graph["graph"]
    messages = agent_graph["messages"]
    agent_name = agent_graph["final_agent_name"]
    agent_id_str = agent_graph["final_agent_id"]

    def map_type_to_role(msg_type):
        if msg_type is None:
            return "user"
        t = msg_type.lower()
        if t == "system":
            return "system"
        elif t == "assistant":
            return "assistant"
        elif t == "human":
            return "user"
        else:
            return t

    async def response_generator():
        yield f"[Agent: {agent_name} | Session: {session_id}]\n\n"
        full_answer = ""

        history_context = ""
        for entry in truncated_history:
            user_msg = entry.get("user", "")
            assistant_msg = entry.get("assistant", "")
            if user_msg:
                history_context += f"User: {user_msg}\n"
            if assistant_msg:
                history_context += f"Assistant: {assistant_msg}\n"
        latest_message = None
        for msg in messages[::-1]:
            msg_type = msg.get("type") or msg.get("role")
            if msg_type and str(msg_type).lower() in ("user", "human"):
                latest_message = msg
                break
        if latest_message is None and messages:
            latest_message = messages[-1]
        if latest_message:
            role = map_type_to_role(latest_message.get("type") or latest_message.get("role"))
            content = (history_context + latest_message.get("content", "")).strip()
            astream_input = {"role": role, "content": content}
        else:
            astream_input = {"role": "user", "content": (history_context + query).strip()}

        async for chunk in graph.astream(astream_input):
            content = chunk.get("content", "")
            full_answer += content
            yield content

        background_tasks.add_task(
            update_chat_history_entry,
            session_id=session_id,
            message_num=message_num,
            new_query=query,
            new_answer=full_answer
        )

    return StreamingResponse(response_generator(), media_type="text/plain; charset=utf-8")

# --- Session Management Routes ---
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage

@app.get("/sessions", response_model=List[dict])
def list_sessions(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        user = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
    sessions = list(sessions_db.find({"user_id": str(user["_id"])}, {"_id": 0}))

    for i, session in enumerate(sessions):
        if "chat_history" in session and len(session["chat_history"]) > 3: 
            title_generator = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3)

            chat_history = session["chat_history"]

            prompts = [
                SystemMessage("You are a title generator. You receive the users chat history in the chatbot and generate a short title based on it. The title should represent what is going on in the chat, the title shouldn't be flashy or trendy, just helpful and straight to the point. And generate the title in the same language as the chat history."),
            ]

            for entry in chat_history:
                prompts.append(HumanMessage(content=entry["user"]))
                prompts.append(AIMessage(content=entry["assistant"]))
            
            title = title_generator.invoke(prompts)

            sessions[i]["title"] = title.content

    return sessions

@app.get("/sessions/{session_id}", response_model=dict)
def get_session(session_id: str, token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        user = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
    session = sessions_db.find_one({"session_id": session_id, "user_id": str(user["_id"])}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if "chat_history" in session and len(session["chat_history"]) > 3: 
        title_generator = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3)

        chat_history = session["chat_history"]

        prompts = [
            SystemMessage("You are a title generator. You receive the users chat history in the chatbot and generate a short title based on it. The title should represent what is going on in the chat, the title shouldn't be flashy or trendy, just helpful and straight to the point. And generate the title in the same language as the chat history."),
        ]

        for entry in chat_history:
            prompts.append(HumanMessage(content=entry["user"]))
            prompts.append(AIMessage(content=entry["assistant"]))
        
        title = title_generator.invoke(prompts)

        session["title"] = title.content
    
    return session

@app.delete("/sessions/{session_id}")
def delete_session(session_id: str, token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        user = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
    result = sessions_db.delete_one({
        "session_id": session_id,
        "user_id": str(user["_id"])
    })

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"message": f"Session '{session_id}' deleted successfully"}

# --- Agent Management Routes ---
from api.agent import Agent, AgentCreate, AgentUpdate, Connector, ConnectorCreate, ConnectorUpdate

@app.get("/agents", response_model=List[Agent])
def list_agents(token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    if not user.get("organization"):
        return []
    
    agents_cursor = agents_db.find({"org": ObjectId(user["organization"])})
    return [Agent(**agent) for agent in agents_cursor]


@app.post("/agents", response_model=Agent)
def create_agent(agent: AgentCreate, token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    org_id = ObjectId(user["organization"])

    if user.get("permission") != "orgadmin":
        raise HTTPException(status_code=403, detail="Permission denied: Only organization admins can create agents.")

    if agent.connector_ids:
        for c_id in agent.connector_ids:
            if not connectors_db.find_one({"_id": c_id, "org": org_id}):
                raise HTTPException(status_code=404, detail=f"Connector with ID {c_id} not found in your organization.")

    agent_data = agent.model_dump(by_alias=True, exclude={"id"}) 
    
    agent_data["org"] = org_id
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    agent_data["created_at"] = now
    agent_data["updated_at"] = now

    result = agents_db.insert_one(agent_data)
    
    created_agent = agents_db.find_one({"_id": result.inserted_id})
    if not created_agent:
        raise HTTPException(status_code=500, detail="Failed to create and retrieve the agent.")
        
    return Agent(**created_agent)


@app.get("/agents/{agent_id}", response_model=Agent)
def get_agent(agent_id: str, token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    
    if not ObjectId.is_valid(agent_id):
        raise HTTPException(status_code=400, detail="Invalid agent ID format.")
    
    agent = agents_db.find_one({
        "_id": ObjectId(agent_id), 
        "org": ObjectId(user["organization"])
    })

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found or you do not have permission to view it.")
    
    return Agent(**agent)


@app.put("/agents/{agent_id}", response_model=Agent)
def update_agent(agent_id: str, agent_update: AgentUpdate, token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    org_id = ObjectId(user["organization"])
    
    if user.get("permission") != "orgadmin":
        raise HTTPException(status_code=403, detail="Permission denied: Only organization admins can update agents.")

    if not ObjectId.is_valid(agent_id):
        raise HTTPException(status_code=400, detail="Invalid agent ID format.")

    if not agents_db.find_one({"_id": ObjectId(agent_id), "org": org_id}):
        raise HTTPException(status_code=404, detail="Agent not found.")
    
    update_data = agent_update.model_dump(exclude_unset=True, exclude_none=True)

    if "connector_ids" in update_data and update_data["connector_ids"] is not None:
        for c_id in update_data["connector_ids"]:
            if not connectors_db.find_one({"_id": c_id, "org": org_id}):
                raise HTTPException(status_code=404, detail=f"Connector with ID {c_id} not found in your organization.")
    
    for field in ["id", "_id", "org", "created_at"]:
        update_data.pop(field, None)

    if not update_data:
        raise HTTPException(status_code=400, detail="No valid update data provided.")

    update_data["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    agents_db.update_one(
        {"_id": ObjectId(agent_id)},
        {"$set": update_data}
    )

    updated_agent = agents_db.find_one({"_id": ObjectId(agent_id)})
    return Agent(**updated_agent)


@app.delete("/agents/{agent_id}")
def delete_agent(agent_id: str, token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    
    if user.get("permission") != "orgadmin":
        raise HTTPException(status_code=403, detail="Permission denied: Only organization admins can delete agents.")

    if not ObjectId.is_valid(agent_id):
        raise HTTPException(status_code=400, detail="Invalid agent ID format.")
    
    result = agents_db.delete_one({
        "_id": ObjectId(agent_id), 
        "org": ObjectId(user["organization"])
    })

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Agent not found or you do not have permission to delete it.")
    
    return {"message": f"Agent '{agent_id}' deleted successfully."}

# --- Connector Routes ---
@app.post("/connectors", response_model=Connector, status_code=201)
def create_connector(connector_data: ConnectorCreate, token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    org_id = ObjectId(user["organization"])
    if user.get("permission") != "orgadmin":
        raise HTTPException(status_code=403, detail="Permission denied: Only organization admins can create connectors.")

    if connectors_db.find_one({"org": org_id, "name": connector_data.name}):
        raise HTTPException(status_code=400, detail=f"A connector named '{connector_data.name}' already exists in your organization.")

    new_connector_data = connector_data.model_dump()
    new_connector_data["org"] = org_id
    
    result = connectors_db.insert_one(new_connector_data)
    created_connector = connectors_db.find_one({"_id": result.inserted_id})
    if not created_connector:
        raise HTTPException(status_code=500, detail="Failed to create and retrieve the connector.")
        
    return Connector(**created_connector)

@app.get("/connectors", response_model=List[Connector])
def list_connectors(token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    org_id = ObjectId(user["organization"])
    
    connectors_cursor = connectors_db.find({"org": org_id})
    return [Connector(**c) for c in connectors_cursor]

@app.get("/connectors/{connector_id}", response_model=Connector)
def get_connector(connector_id: str, token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    org_id = ObjectId(user["organization"])
    
    if not ObjectId.is_valid(connector_id):
        raise HTTPException(status_code=400, detail="Invalid connector ID format.")
        
    connector = connectors_db.find_one({"_id": ObjectId(connector_id), "org": org_id})
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found or you do not have permission to view it.")
        
    return Connector(**connector)

@app.put("/connectors/{connector_id}", response_model=Connector)
def update_connector(connector_id: str, connector_update: ConnectorUpdate, token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    org_id = ObjectId(user["organization"])

    if user.get("permission") != "orgadmin":
        raise HTTPException(status_code=403, detail="Permission denied: Only organization admins can update connectors.")

    if not ObjectId.is_valid(connector_id):
        raise HTTPException(status_code=400, detail="Invalid connector ID format.")

    update_data = connector_update.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided.")
    
    if "name" in update_data:
        if connectors_db.find_one({"_id": {"$ne": ObjectId(connector_id)}, "org": org_id, "name": update_data["name"]}):
            raise HTTPException(status_code=400, detail=f"A connector named '{update_data['name']}' already exists.")

    result = connectors_db.update_one(
        {"_id": ObjectId(connector_id), "org": org_id},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Connector not found.")

    updated_connector = connectors_db.find_one({"_id": ObjectId(connector_id)})
    return Connector(**updated_connector)

@app.delete("/connectors/{connector_id}", status_code=200)
def delete_connector(connector_id: str, token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    org_id = ObjectId(user["organization"])

    if user.get("permission") != "orgadmin":
        raise HTTPException(status_code=403, detail="Permission denied: Only organization admins can delete connectors.")

    if not ObjectId.is_valid(connector_id):
        raise HTTPException(status_code=400, detail="Invalid connector ID format.")

    delete_result = connectors_db.delete_one({"_id": ObjectId(connector_id), "org": org_id})

    if delete_result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Connector not found.")

    agents_db.update_many(
        {"org": org_id},
        {"$pull": {"connector_ids": ObjectId(connector_id)}}
    )

    return {"message": f"Connector '{connector_id}' deleted successfully."}

@app.get("/connectors/{connector_id}/settings")
def get_connector_settings(connector_id: str, token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    org_id = ObjectId(user["organization"])

    if not ObjectId.is_valid(connector_id):
        raise HTTPException(status_code=400, detail="Invalid connector ID format.")

    connector = connectors_db.find_one({"_id": ObjectId(connector_id), "org": org_id})
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found.")

    return {"settings": connector.get("settings", {})}

@app.put("/connectors/{connector_id}/settings", status_code=200)
def update_connector_settings(connector_id: str, settings: dict, token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    org_id = ObjectId(user["organization"])

    if not ObjectId.is_valid(connector_id):
        raise HTTPException(status_code=400, detail="Invalid connector ID format.")

    
    result = connectors_db.update_one(
        {"_id": ObjectId(connector_id)},
        {"$set": {"settings": settings}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Connector not found.")
    
    return {"message": f"Settings for connector '{connector_id}' updated successfully."}

@app.get("/agents/{agent_id}/connectors", status_code=200)
def list_agent_connectors(agent_id: str, token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    org_id = ObjectId(user["organization"])

    if not ObjectId.is_valid(agent_id):
        raise HTTPException(status_code=400, detail="Invalid agent ID format.")

    agent = agents_db.find_one({"_id": ObjectId(agent_id), "org": org_id})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found.")

    connector_ids = agent.get("connector_ids", [])
    connectors = list(connectors_db.find({"_id": {"$in": connector_ids}, "org": org_id}))

    return {"connectors": [Connector(**c) for c in connectors]}

@app.get("/agents/{agent_id}/connectors/{connector_id}", status_code=200)
def get_connector_of_agent(agent_id: str, connector_id: str, token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    org_id = ObjectId(user["organization"])

    if not ObjectId.is_valid(agent_id) or not ObjectId.is_valid(connector_id):
        raise HTTPException(status_code=400, detail="Invalid agent or connector ID format.")

    agent = agents_db.find_one({"_id": ObjectId(agent_id), "org": org_id})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found.")

    if "connector_ids" not in agent or ObjectId(connector_id) not in agent["connector_ids"]:
        raise HTTPException(status_code=404, detail="Connector not associated with the agent.")

    connector = connectors_db.find_one({"_id": ObjectId(connector_id), "org": org_id})
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found.")

    return Connector(**connector)

@app.post("/agents/{agent_id}/connectors/{connector_id}", status_code=200)
def add_connector_to_agent(agent_id: str, connector_id: str, token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    org_id = ObjectId(user["organization"])

    if user.get("permission") != "orgadmin":
        raise HTTPException(status_code=403, detail="Permission denied: Only organization admins can modify agents.")

    if not ObjectId.is_valid(agent_id) or not ObjectId.is_valid(connector_id):
        raise HTTPException(status_code=400, detail="Invalid agent or connector ID format.")

    agent = agents_db.find_one({"_id": ObjectId(agent_id), "org": org_id})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found.")

    connector = connectors_db.find_one({"_id": ObjectId(connector_id), "org": org_id})
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found.")

    if "connector_ids" in agent and ObjectId(connector_id) in agent["connector_ids"]:
        raise HTTPException(status_code=400, detail="Connector already associated with the agent.")

    update_result = agents_db.update_one(
        {"_id": ObjectId(agent_id)},
        {"$addToSet": {"connector_ids": ObjectId(connector_id)}, "$set": {"updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}}
    )

    if update_result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Agent not found during update.")

    return {"message": f"Connector '{connector_id}' added to agent '{agent_id}' successfully."}

@app.delete("/agents/{agent_id}/connectors/{connector_id}", status_code=200)
def delete_connector_from_agent(agent_id: str, connector_id: str, token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    org_id = ObjectId(user["organization"])

    if user.get("permission") != "orgadmin":
        raise HTTPException(status_code=403, detail="Permission denied: Only organization admins can modify agents.")
    
    agent = agents_db.find_one({"_id": ObjectId(agent_id), "org": org_id})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found.")

    connector = connectors_db.find_one({"_id": ObjectId(connector_id), "org": org_id})
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found.")
    
    if not "connector_ids" in agent or not ObjectId(connector_id) in agent["connector_ids"]:
        raise HTTPException(status_code=400, detail="Connector isn't associated with the agent.")
    
    update_result = agents_db.update_one(
        {"_id": ObjectId(agent_id)},
        {"$pull": {"connector_ids": ObjectId(connector_id)}, "$set": {"updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}}
    )

    if update_result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Agent not found during update.")
    
    return {"message": f"Connector '{connector_id}' removed from agent '{agent_id}' successfully."}

# --- Document Management ---
from api.embed import embed, save_embedding, get_embeddings, similarity, knowledge_db

import PyPDF2, io

@app.post("/connectors/{connector_id}/upload", status_code=201)
async def upload_pdf(connector_id: str, file: UploadFile = File(...), token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    org_id = ObjectId(user["organization"])

    if not ObjectId.is_valid(connector_id):
        raise HTTPException(status_code=400, detail="Invalid connector ID format.")
    
    connector = connectors_db.find_one({"_id": ObjectId(connector_id), "org": org_id})
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found or you do not have permission to use it.")
    
    if connector.get("settings") and connector["settings"].get("document_id"):
        raise HTTPException(status_code=400, detail="This connector already has a document associated with it. Please create a new connector for this file.")

    if connector.get("connector_type") == "source_pdf":
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="Uploaded file is not a valid PDF")
        
        try:
            contents = await file.read()
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(contents))
            text = "".join(page.extract_text() or "" for page in pdf_reader.pages)
            if not text.strip():
                raise HTTPException(status_code=400, detail="No text extracted from the PDF")

            chunks_with_embeddings = embed(text, chunk_size=1000, overlap=200)
            if not chunks_with_embeddings:
                raise HTTPException(status_code=500, detail="Failed to generate text chunks or embeddings.")
            
            document_id = save_embedding(chunks_with_embeddings, org_id)
            if not document_id:
                raise HTTPException(status_code=500, detail="Failed to save document and embeddings to the database.")
            
            update_result = connectors_db.update_one(
                {"_id": ObjectId(connector_id)},
                {"$set": {"settings": {"document_id": str(document_id)}}}
            )
            
            if update_result.matched_count == 0:
                knowledge_db.delete_one({"_id": document_id})
                raise HTTPException(status_code=500, detail="Failed to link document to connector. The upload has been rolled back.")
            
            return JSONResponse(
                content={"document_id": str(document_id), "chunks_saved": len(chunks_with_embeddings)},
                status_code=201
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred during PDF upload: {str(e)}")
        
    elif connector.get("connector_type") == "source_txt":
        if file.content_type != "text/plain":
            raise HTTPException(status_code=400, detail="Uploaded file is not a valid TXT")
        
        try:
            contents = await file.read()
            text = contents.decode('utf-8')
            if not text.strip():
                raise HTTPException(status_code=400, detail="No text extracted from the TXT file")

            chunks_with_embeddings = embed(text, chunk_size=1000, overlap=200)
            if not chunks_with_embeddings:
                raise HTTPException(status_code=500, detail="Failed to generate text chunks or embeddings.")
            
            document_id = save_embedding(chunks_with_embeddings, org_id)
            if not document_id:
                raise HTTPException(status_code=500, detail="Failed to save document and embeddings to the database.")
            
            update_result = connectors_db.update_one(
                {"_id": ObjectId(connector_id)},
                {"$set": {"settings": {"document_id": str(document_id)}}}
            )
            if update_result.matched_count == 0:
                knowledge_db.delete_one({"_id": document_id})
                raise HTTPException(status_code=500, detail="Failed to link document to connector. The upload has been rolled back.")
            
            return JSONResponse(
                content={"document_id": str(document_id), "chunks_saved": len(chunks_with_embeddings)},
                status_code=201
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred during TXT upload: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail="Unsupported connector type for file upload")