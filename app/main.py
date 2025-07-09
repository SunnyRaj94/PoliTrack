# app/main.py
import os
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from beanie import init_beanie
from pymongo import AsyncMongoClient

import logging

from app.configs import env, configs
from app.models.user import User
from app.models.hierarchy import (
    AdminUnit,
    # AdministrativeUnitType,
)
from app.routes import users, auth, hierarchy  # Import new routes
from fastapi.middleware.cors import CORSMiddleware


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Define paths to your static and templates directories
STATIC_DIR = os.path.join(PROJECT_ROOT, "static")
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "templates")

# Debugging checks (optional, but good practice)
if not os.path.isdir(STATIC_DIR):
    print(f"ERROR: Static directory not found at {STATIC_DIR}")
if not os.path.isdir(TEMPLATES_DIR):
    print(f"ERROR: Templates directory not found at {TEMPLATES_DIR}")

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events for the application.
    Connects to MongoDB and initializes Beanie ODM.
    """
    logger.info("Application startup initiated...")
    try:
        client = AsyncMongoClient(env.get("MONGO_URI"))
        # Ensure database name is correctly read from settings
        await init_beanie(
            database=client[env.get("MONGO_DB")], document_models=[User, AdminUnit]
        )
        logger.info("MongoDB connection and Beanie initialization successful.")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB or initialize Beanie: {e}")
        # Depending on severity, you might want to re-raise or exit here
        raise

    yield

    logger.info("Application shutdown initiated...")
    # Clean up resources if necessary
    client.close()
    logger.info("MongoDB connection closed.")


app = FastAPI(
    title=configs.get("app").get("project_name"),
    debug=configs.get("app").get("debug_mode"),
    lifespan=lifespan,  # Use the lifespan manager
)

origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # List of origins that are allowed to make requests
    allow_credentials=True,  # Allow cookies to be included in requests
    allow_methods=[
        "*"
    ],  # Allow all HTTP methods (GET, POST, PUT, DELETE, OPTIONS, etc.)
    allow_headers=["*"],  # Allow all headers in the request
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
# Include API routes
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])  # New
app.include_router(
    hierarchy.router, prefix="/hierarchy", tags=["Administrative Hierarchy"]
)  # New


@app.get("/")
async def read_index():
    index_html_path = os.path.join(TEMPLATES_DIR, "login.html")
    return FileResponse(index_html_path)
