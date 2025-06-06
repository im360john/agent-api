#!/bin/bash

# Fix the session.py import issue by replacing it at runtime
if [ -f "/app/db/session_fixed.py" ]; then
    cp /app/db/session_fixed.py /app/db/session.py
fi

# Start the application
exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}
