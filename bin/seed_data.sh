#!/bin/bash

# Telematics UBI Data Seeder
# This script seeds the database with sample data

echo "Seeding Telematics UBI database..."

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

# Run the seeder
echo "Seeding database with sample data..."
python -m src.backend.db.seed

echo "Database seeding completed!"
