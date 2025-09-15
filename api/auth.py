import string
import secrets
from datetime import datetime, timedelta
from jose import JWTError, jwt
from typing import Dict
from bson import ObjectId
from fastapi import HTTPException
from pymongo import MongoClient
import os

def generate_random_string(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

SECRET_KEY = os.environ.get("AUTH_SECRET_KEY")

if not SECRET_KEY:
    raise ValueError("FATAL ERROR: No AUTH_SECRET_KEY set in environment!")

ALGORITHM = os.environ.get("AUTH_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("AUTH_TOKEN_EXPIRE", 1440))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.environ.get("AUTH_REFRESH_TOKEN_EXPIRE", 30))

client = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/"))
db = client.nexa

users_db = db.users
prospective_users_db = db.prospective_users
orgs_db = db.organizations

def _create_token(data: dict, expires_delta: timedelta, token_type: str) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire, "type": token_type})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_access_token(user_data: dict) -> str:
    to_encode = user_data.copy()

    to_encode.pop("password", None)
    to_encode.pop("reset_token", None)
    to_encode.pop("refresh_token_hash", None)

    if '_id' in to_encode and isinstance(to_encode['_id'], ObjectId):
        to_encode['_id'] = str(to_encode['_id'])
    if 'organization' in to_encode and isinstance(to_encode.get('organization'), ObjectId):
        to_encode['organization'] = str(to_encode['organization'])

    to_encode['sub'] = user_data.get("username")

    expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return _create_token(data=to_encode, expires_delta=expires, token_type="access")

def create_refresh_token(user_data: dict) -> str:
    to_encode = {"sub": user_data.get("username")}
    expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    return _create_token(data=to_encode, expires_delta=expires, token_type="refresh")

def verify_token(token: str, expected_type: str = "access") -> Dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        token_type = payload.get("type")
        if token_type != expected_type:
            raise HTTPException(status_code=401, detail=f"Invalid token type: expected '{expected_type}'")

        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token payload: missing 'sub'")

        return payload
        
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Could not validate credentials: {e}")