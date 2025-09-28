import string
import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pymongo import MongoClient
import os

def generate_random_string(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

SECRET_KEY = os.environ.get("AUTH_SECRET_KEY", generate_random_string())
ALGORITHM = os.environ.get("AUTH_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("AUTH_TOKEN_EXPIRE", 1440))

users_db = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/")).nexa.users
prospective_users_db = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/")).nexa.prospective_users
orgs_db = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/")).nexa.organizations

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        user = users_db.find_one({"username": username})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")