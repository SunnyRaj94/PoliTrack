import json
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from configs import env

# Load environment variables
print(json.dumps(env, indent=2))

app = FastAPI(title="PoliTrack")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure Jinja2Templates
templates = Jinja2Templates(directory="templates")


# Placeholder for DB connection (actual logic will be in services/db.py)
async def connect_to_mongodb():
    print("Connecting to MongoDB...")
    # Placeholder: Actual Motor/Beanie connection will go here
    # For now, just simulate connection
    app.state.mongo_client = None  # Will be motor.motor_asyncio.AsyncIOMotorClient
    app.state.database = None  # Will be motor.motor_asyncio.AsyncIOMotorDatabase
    print("MongoDB connection placeholder set.")


async def close_mongodb_connection():
    print("Closing MongoDB connection...")
    if app.state.mongo_client:
        # app.state.mongo_client.close() # Actual close method
        print("MongoDB connection closed.")


@app.on_event("startup")
async def startup_event():
    await connect_to_mongodb()


@app.on_event("shutdown")
async def shutdown_event():
    await close_mongodb_connection()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html", {"request": request, "title": "PoliTrack Home"}
    )
