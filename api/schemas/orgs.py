from pydantic import BaseModel

class TransferOwnershipModel(BaseModel):
    new_owner_username: str

class InviteSignupModel(BaseModel):
    invite_code: str
    password: str
    firstname: str = ""
    lastname: str = ""
    phone: str = ""