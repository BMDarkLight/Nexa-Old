from pymongo import MongoClient
from dotenv import find_dotenv, load_dotenv

import os

load_dotenv(find_dotenv())

sessions_db = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/")).nexa.sessions
agents_db = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/")).nexa.agents
connectors_db = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/")).nexa.connectors
knowledge_db = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/")).nexa.embeddings
users_db = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/")).nexa.users
prospective_users_db = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/")).nexa.prospective_users
orgs_db = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/")).nexa.organizations