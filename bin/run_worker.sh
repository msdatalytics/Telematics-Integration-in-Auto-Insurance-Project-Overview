#!/bin/bash

# Telematics UBI Worker Runner
# This script starts the Redis Stream consumer worker

echo "Starting Telematics UBI Worker..."

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

# Start the worker
echo "Starting Redis Stream consumer..."
python -m src.backend.stream.consumer
