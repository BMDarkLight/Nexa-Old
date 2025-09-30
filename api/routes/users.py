from fastapi import APIRouter, Depends, HTTPException
from typing import List
from bson import ObjectId

import datetime

from api.schemas.users import UserCreateModel, UserUpdateModel
from api.auth import verify_token, hash_password, oauth2_scheme
from api.database import users_db, prospective_users_db, orgs_db


router = APIRouter(tags=["User Management"])

@router.get("/users", response_model=List[dict])
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

@router.post("/users")
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

@router.get("/users/{username}")
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


@router.put("/users/{username}")
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

@router.delete("/users/{username}", status_code=200)
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