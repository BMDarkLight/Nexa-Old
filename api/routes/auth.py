from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from dotenv import load_dotenv, find_dotenv
from typing import List

import datetime
import os
import secrets

from api.auth import hash_password, verify_token, verify_password, create_access_token, oauth2_scheme
from api.database import users_db, prospective_users_db, orgs_db
from api.schemas.auth import SignupModel, ForgotPasswordModel, ResetPasswordModel, CheckResetTokenModel
from api.mail import send_email

router = APIRouter(tags=["Authentication"])

load_dotenv(dotenv_path=find_dotenv())

SERVER_URL = os.getenv("SERVER_URL", "http://localhost")
UI_PORT = os.getenv("UI_PORT", "3000")
API_PORT = os.getenv("API_PORT", "8000")

@router.post("/signup")
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

@router.post("/signin")
def signin(form_data: OAuth2PasswordRequestForm = Depends()):
    user = users_db.find_one({"username": form_data.username})
    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if user.get("status") == "pending":
        raise HTTPException(status_code=403, detail="User is pending approval")
    
    access_token = create_access_token(data={"sub": user["username"]})

    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/forgot-password")
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

@router.post("/check-reset-token")
def check_reset_token(form_data: CheckResetTokenModel):
    username = form_data.username
    token = form_data.token
    user = users_db.find_one({"username": username, "reset_token": token})
    if not user:
        return {"message": "Invalid token", "valid": False}
    else:
        return {"message": "Token is valid", "valid": True}

@router.post("/reset-password")
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

@router.post("/signup/approve/{username}")
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

@router.post("/signup/reject/{username}")
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

@router.get("/signup/prospective-users", response_model=List[dict])
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

@router.get("/signup/prospective-users/{username}", response_model=dict)
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