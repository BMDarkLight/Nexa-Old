from pydantic import BaseModel
from typing import List

from api.schemas.base import PyObjectId

class Context(BaseModel):
    documents: List[PyObjectId] = None