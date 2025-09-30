from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, Literal

from api.schemas.base import PyObjectId

Connectors = Literal["google_sheet", "google_drive", "source_pdf", "source_uri"]

class Connector(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    name: str
    connector_type: Connectors
    settings: Dict[str, Any]
    org: PyObjectId

class ConnectorCreate(BaseModel):
    name: str
    connector_type: Connectors
    settings: Dict[str, Any]

class ConnectorUpdate(BaseModel):
    name: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None