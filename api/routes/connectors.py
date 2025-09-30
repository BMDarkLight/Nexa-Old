from fastapi import Depends, APIRouter, HTTPException
from bson import ObjectId
from typing import List

import datetime

from api.schemas.connectors import Connector, ConnectorCreate, ConnectorUpdate
from api.auth import verify_token, oauth2_scheme
from api.database import connectors_db, agents_db

router = APIRouter(tags=["Connectors"])

@router.post("/connectors", response_model=Connector, status_code=201)
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

@router.get("/connectors", response_model=List[Connector])
def list_connectors(token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    org_id = ObjectId(user["organization"])
    
    connectors_cursor = connectors_db.find({"org": org_id})
    return [Connector(**c) for c in connectors_cursor]

@router.get("/connectors/{connector_id}", response_model=Connector)
def get_connector(connector_id: str, token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    org_id = ObjectId(user["organization"])
    
    if not ObjectId.is_valid(connector_id):
        raise HTTPException(status_code=400, detail="Invalid connector ID format.")
        
    connector = connectors_db.find_one({"_id": ObjectId(connector_id), "org": org_id})
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found or you do not have permission to view it.")
        
    return Connector(**connector)

@router.put("/connectors/{connector_id}", response_model=Connector)
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

@router.delete("/connectors/{connector_id}", status_code=200)
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

@router.get("/connectors/{connector_id}/settings")
def get_connector_settings(connector_id: str, token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    org_id = ObjectId(user["organization"])

    if not ObjectId.is_valid(connector_id):
        raise HTTPException(status_code=400, detail="Invalid connector ID format.")

    connector = connectors_db.find_one({"_id": ObjectId(connector_id), "org": org_id})
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found.")

    return {"settings": connector.get("settings", {})}

@router.put("/connectors/{connector_id}/settings", status_code=200)
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

@router.get("/agents/{agent_id}/connectors", status_code=200)
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

@router.get("/agents/{agent_id}/connectors/{connector_id}", status_code=200)
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

@router.post("/agents/{agent_id}/connectors/{connector_id}", status_code=200)
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

@router.delete("/agents/{agent_id}/connectors/{connector_id}", status_code=200)
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