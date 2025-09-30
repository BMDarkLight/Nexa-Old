from fastapi import FastAPI
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from passlib.context import CryptContext
from dotenv import load_dotenv, find_dotenv

app = FastAPI(title="Nexa API")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/signin")
load_dotenv(dotenv_path=find_dotenv())

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Authorization Compatible Swagger UI ---
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Nexa API",
        version="1.0.0",
        description="Gen-AI for Organizations. Streamline all workflows across messenger, workspaces and organizational system in one place, and make them smart using AI.",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "OAuth2Password": {
            "type": "oauth2",
            "flows": {
                "password": {
                    "tokenUrl": "/signin",
                    "scopes": {}
                }
            }
        },
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    public_paths = {"/signin", "/signup", "/test-cors", "/", "/forgot-password", "/reset-password", "/check-reset-token", "/invite/signup/{username}"}
    for path_name, path in openapi_schema["paths"].items():
        if path_name in public_paths:
            continue
        for operation in path.values():
            operation["security"] = [{"OAuth2Password": []}, {"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# --- Database Initialization ---
import os
import datetime

from api.auth import hash_password
from api.database import users_db

def create_initial_sysadmin():
    if users_db.count_documents({"permission": "sysadmin"}) < 1:
        username = os.getenv("SYSADMIN_USERNAME")
        password = os.getenv("SYSADMIN_PASSWORD")
        firstname = os.getenv("SYSADMIN_FIRSTNAME", "")
        lastname = os.getenv("SYSADMIN_LASTNAME", "")
        email = os.getenv("SYSADMIN_EMAIL", "")
        phone = os.getenv("SYSADMIN_PHONE", "")
        if not username or not password:
            print("SYSADMIN_USERNAME or SYSADMIN_PASSWORD not set in env; skipping sysadmin creation")
            return
        hashed_password = hash_password(password)
        now = datetime.datetime.now(datetime.timezone.utc)
        user = {
            "username": username,
            "password": hashed_password,
            "firstname": firstname,
            "lastname": lastname,
            "email": email,
            "phone": phone,
            "created_at": now,
            "updated_at": now,
            "permission": "sysadmin",
        }
        user_result = users_db.insert_one(user)
        if user_result.acknowledged:
            print(f"Created initial sysadmin user: {username}")
        else:
            print("Failed to create initial sysadmin user")

create_initial_sysadmin()

SERVER_URL = os.getenv("SERVER_URL", "http://localhost")
UI_PORT = os.getenv("UI_PORT", "3000")
API_PORT = os.getenv("API_PORT", "8000")

# --- Home Page ---
from api.routes.pages import router as pages_router
app.include_router(pages_router)

# --- Authentication Routes ---
from api.routes.auth import router as auth_router
app.include_router(auth_router)

# --- Organization Management Routes ---
from api.routes.orgs import router as orgs_router
app.include_router(orgs_router)

# --- User Management Routes ---
from api.routes.users import router as users_router
app.include_router(users_router)

# --- Agent Routes ---
from api.routes.agents import router as agents_router
app.include_router(agents_router)

# --- Session Management Routes ---
from api.routes.sessions import router as sessions_router
app.include_router(sessions_router)

# --- Context Management ---
from api.routes.context import router as context_router
app.include_router(context_router)

# --- Connector Routes ---
from api.routes.connectors import router as connectors_router
app.include_router(connectors_router)