from pymongo import MongoClient
from minio import Minio
from dotenv import find_dotenv, load_dotenv

import os

load_dotenv(find_dotenv())

minio_client = Minio(
    endpoint=os.getenv("MINIO_ENDPOINT", "localhost:9000"),
    access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
    secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
    secure=False
)

mongo_client = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/"))

nexa_db = mongo_client.nexa

sessions_db = nexa_db.sessions
agents_db = nexa_db.agents
connectors_db = nexa_db.connectors
knowledge_db = nexa_db.embeddings
users_db = nexa_db.users
prospective_users_db = nexa_db.prospective_users
orgs_db = nexa_db.organizations