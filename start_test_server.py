#!/usr/bin/env python3
"""
Start the API server for testing without database dependencies
"""
import os
import uvicorn
from dotenv import load_dotenv

# Set environment to use SQLite instead of PostgreSQL for testing
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["DB_DRIVER"] = "sqlite"

# Ensure all API keys are loaded from .env
load_dotenv()

if __name__ == "__main__":
    print("Starting test server with SQLite database...")
    print("API will be available at http://localhost:8000")
    print("API docs will be available at http://localhost:8000/docs")
    
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False  # Disable reload for stability
    )