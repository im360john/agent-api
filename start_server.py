#!/usr/bin/env python3
"""
Start the API server with proper environment setup
"""
import os

# Set default database environment variables if not present
if not os.getenv("DB_HOST"):
    os.environ["DB_HOST"] = "localhost"
if not os.getenv("DB_PORT"):
    os.environ["DB_PORT"] = "5432"
if not os.getenv("DB_USER"):
    os.environ["DB_USER"] = "postgres"
if not os.getenv("DB_PASSWORD"):
    os.environ["DB_PASSWORD"] = ""
if not os.getenv("DB_DATABASE"):
    os.environ["DB_DATABASE"] = "agno"

# Start uvicorn
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )