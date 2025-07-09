# app/services/db.py
# This file can be used for centralized database client access if needed
# For now, `main.py` handles Beanie initialization.
from pymongo import AsyncMongoClient
from typing import Optional
from app.configs import env

# This client can be directly imported and used for more complex queries
# that might not fit neatly into Beanie's ORM.
db_client: Optional[AsyncMongoClient] = None


async def get_database_client() -> AsyncMongoClient:
    """Returns the MongoDB async client."""
    global db_client
    if db_client is None:
        db_client = AsyncMongoClient(env.get("MONGO_URI"))
    return db_client
