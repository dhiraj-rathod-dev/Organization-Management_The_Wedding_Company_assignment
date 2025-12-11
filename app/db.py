from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MASTER_DB = os.getenv("MASTER_DB", "master_db")

client = MongoClient(MONGO_URI)
master_db = client[MASTER_DB]

# Collections inside master_db
orgs_collection = master_db["organizations"]
admins_collection = master_db["admins"]
