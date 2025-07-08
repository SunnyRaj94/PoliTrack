# Load environment variables
export $(grep -v '^#' .env | xargs)

# Run FastAPI app with uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000