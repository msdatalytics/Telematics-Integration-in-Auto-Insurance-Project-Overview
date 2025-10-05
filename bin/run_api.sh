#!/bin/bash

# Telematics UBI API Runner
# This script starts the FastAPI backend server

echo "Starting Telematics UBI API..."

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export PYTHONUNBUFFERED=1

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Start the API server
echo "Starting API server on http://localhost:8000"
uvicorn src.backend.app:app --host 0.0.0.0 --port 8000 --reload
