#!/usr/bin/env python3
"""
Simple script to run the telematics insurance application locally with SQLite.
"""
import uvicorn
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from backend.db.base import create_tables
from backend.db.seed import main as seed_data

def main():
    """Run the application locally."""
    print("🚀 Starting Telematics Insurance Application...")
    
    # Create database tables
    print("📊 Creating database tables...")
    create_tables()
    print("✅ Database tables created!")
    
    # Seed initial data
    print("🌱 Seeding initial data...")
    try:
        seed_data()
        print("✅ Initial data seeded!")
    except Exception as e:
        print(f"⚠️  Warning: Could not seed data: {e}")
    
    # Start the FastAPI server
    print("🌐 Starting FastAPI server on http://localhost:8000")
    print("📖 API docs available at http://localhost:8000/docs")
    
    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["src"]
    )

if __name__ == "__main__":
    main()
