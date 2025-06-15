#!/usr/bin/env python3
"""
Test the API without database dependencies
"""
import os
import sys
import types
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Mock the database session to avoid connection errors
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Create a mock db module
mock_db = types.ModuleType('db')
mock_session = types.ModuleType('session')
mock_session.db_url = "sqlite:///./test.db"
mock_session.get_db = lambda: None
mock_db.session = mock_session
sys.modules['db'] = mock_db
sys.modules['db.session'] = mock_session

if __name__ == "__main__":
    print("\n" + "="*60)
    print("Starting Agent API Test Server")
    print("="*60)
    print("\nNote: This is a test server with limited functionality.")
    print("Some agents may not work without a proper database setup.")
    print("\nAPI will be available at: http://localhost:8000")
    print("API documentation at: http://localhost:8000/docs")
    print("\nPress CTRL+C to stop the server")
    print("="*60 + "\n")
    
    try:
        uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=False)
    except KeyboardInterrupt:
        print("\nServer stopped.")