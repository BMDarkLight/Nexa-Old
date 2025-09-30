from pydantic import BaseModel

class SignupModel(BaseModel):
    username: str
    password: str
    firstname: str = ""
    lastname: str = ""
    email: str = ""
    phone: str = ""
    organization: str
    plan: str = "free"

class SigninModel(BaseModel):
    username: str
    password: str

class ForgotPasswordModel(BaseModel):
    username: str

class CheckResetTokenModel(BaseModel):
    username: str
    token: str

class ResetPasswordModel(BaseModel):
    username: str
    new_password: str
    token: str