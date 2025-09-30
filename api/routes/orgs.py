from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from bson import ObjectId

import datetime
import secrets

from api.schemas.orgs import TransferOwnershipModel, InviteSignupModel
from api.auth import verify_token, hash_password, oauth2_scheme
from api.database import orgs_db, users_db, prospective_users_db
from api.mail import send_email

router = APIRouter(tags=["Organizations"])

@router.get("/organizations", response_model=dict)
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

@router.get("/organizations/{name}", response_model=dict)
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

@router.put("/organizations/{name}/transfer", status_code=200)
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
@router.post("/invite/{username}")
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


@router.post("/invite/signup/{username}")
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