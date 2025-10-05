#!/usr/bin/env python3
"""
Simple telematics insurance app that runs locally with SQLite.
"""
import sqlite3
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import uvicorn

# Initialize FastAPI app
app = FastAPI(title="Telematics Insurance API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Database setup
def init_db():
    """Initialize SQLite database."""
    conn = sqlite3.connect('telematics.db')
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP NOT NULL,
            distance_km REAL,
            risk_score INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tokens (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Pydantic models
class UserCreate(BaseModel):
    full_name: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str

class TripCreate(BaseModel):
    start_time: datetime
    end_time: datetime
    distance_km: float

class TripResponse(BaseModel):
    id: int
    user_id: int
    start_time: datetime
    end_time: datetime
    distance_km: float
    risk_score: Optional[int] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

# Utility functions
def hash_password(password: str) -> str:
    """Hash password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    return hash_password(password) == hashed

def create_token(user_id: int) -> str:
    """Create a new access token."""
    token = secrets.token_urlsafe(32)
    conn = sqlite3.connect('telematics.db')
    cursor = conn.cursor()
    
    # Store token with 30 minute expiry
    expires_at = datetime.now() + timedelta(minutes=30)
    cursor.execute(
        'INSERT INTO tokens (token, user_id, expires_at) VALUES (?, ?, ?)',
        (token, user_id, expires_at)
    )
    conn.commit()
    conn.close()
    return token

def verify_token(token: str) -> Optional[int]:
    """Verify token and return user_id if valid."""
    conn = sqlite3.connect('telematics.db')
    cursor = conn.cursor()
    
    cursor.execute(
        'SELECT user_id FROM tokens WHERE token = ? AND expires_at > ?',
        (token, datetime.now())
    )
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else None

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    """Get current user from token."""
    token = credentials.credentials
    user_id = verify_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    return user_id

# API Routes
@app.post("/api/v1/auth/register", response_model=TokenResponse)
async def register(user: UserCreate):
    """Register a new user."""
    conn = sqlite3.connect('telematics.db')
    cursor = conn.cursor()
    
    # Check if user already exists
    cursor.execute('SELECT id FROM users WHERE email = ?', (user.email,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    password_hash = hash_password(user.password)
    cursor.execute(
        'INSERT INTO users (full_name, email, password_hash) VALUES (?, ?, ?)',
        (user.full_name, user.email, password_hash)
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # Create token
    token = create_token(user_id)
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(id=user_id, full_name=user.full_name, email=user.email)
    )

@app.post("/api/v1/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """Login user."""
    conn = sqlite3.connect('telematics.db')
    cursor = conn.cursor()
    
    # Find user
    cursor.execute(
        'SELECT id, full_name, email, password_hash FROM users WHERE email = ?',
        (credentials.email,)
    )
    user = cursor.fetchone()
    conn.close()
    
    if not user or not verify_password(credentials.password, user[3]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create token
    token = create_token(user[0])
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(id=user[0], full_name=user[1], email=user[2])
    )

@app.get("/api/v1/users/me", response_model=UserResponse)
async def get_current_user_info(user_id: int = Depends(get_current_user)):
    """Get current user info."""
    conn = sqlite3.connect('telematics.db')
    cursor = conn.cursor()
    
    cursor.execute(
        'SELECT id, full_name, email FROM users WHERE id = ?',
        (user_id,)
    )
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(id=user[0], full_name=user[1], email=user[2])

@app.post("/api/v1/telematics/trips", response_model=TripResponse)
async def create_trip(trip: TripCreate, user_id: int = Depends(get_current_user)):
    """Create a new trip."""
    conn = sqlite3.connect('telematics.db')
    cursor = conn.cursor()
    
    # Calculate a simple risk score based on distance and duration
    duration_hours = (trip.end_time - trip.start_time).total_seconds() / 3600
    avg_speed = trip.distance_km / duration_hours if duration_hours > 0 else 0
    risk_score = min(100, max(0, int(50 + (avg_speed - 50) * 2)))  # Simple scoring
    
    cursor.execute(
        'INSERT INTO trips (user_id, start_time, end_time, distance_km, risk_score) VALUES (?, ?, ?, ?, ?)',
        (user_id, trip.start_time, trip.end_time, trip.distance_km, risk_score)
    )
    trip_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return TripResponse(
        id=trip_id,
        user_id=user_id,
        start_time=trip.start_time,
        end_time=trip.end_time,
        distance_km=trip.distance_km,
        risk_score=risk_score
    )

@app.get("/api/v1/telematics/trips", response_model=List[TripResponse])
async def get_trips(user_id: int = Depends(get_current_user)):
    """Get user's trips."""
    conn = sqlite3.connect('telematics.db')
    cursor = conn.cursor()
    
    cursor.execute(
        'SELECT id, user_id, start_time, end_time, distance_km, risk_score FROM trips WHERE user_id = ? ORDER BY start_time DESC',
        (user_id,)
    )
    trips = cursor.fetchall()
    conn.close()
    
    return [
        TripResponse(
            id=trip[0],
            user_id=trip[1],
            start_time=datetime.fromisoformat(trip[2]),
            end_time=datetime.fromisoformat(trip[3]),
            distance_km=trip[4],
            risk_score=trip[5]
        )
        for trip in trips
    ]

@app.get("/api/v1/score/user/{user_id}/latest")
async def get_latest_score(user_id: int, current_user_id: int = Depends(get_current_user)):
    """Get user's latest risk score."""
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    conn = sqlite3.connect('telematics.db')
    cursor = conn.cursor()
    
    cursor.execute(
        'SELECT risk_score FROM trips WHERE user_id = ? ORDER BY start_time DESC LIMIT 1',
        (user_id,)
    )
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return {"score": 50, "band": "Medium"}
    
    score = result[0]
    if score < 30:
        band = "Low"
    elif score < 70:
        band = "Medium"
    else:
        band = "High"
    
    return {"score": score, "band": band}

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Telematics Insurance API",
        "version": "1.0.0",
        "docs": "/docs",
        "frontend": "Open simple_frontend.html in your browser"
    }

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()
    print("🚀 Telematics Insurance API started!")
    print("📖 API docs: http://localhost:8000/docs")
    print("🌐 Frontend: Open simple_frontend.html in your browser")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
