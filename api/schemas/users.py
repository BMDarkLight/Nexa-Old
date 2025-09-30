from pydantic import BaseModel
from typing import Optional, Literal

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