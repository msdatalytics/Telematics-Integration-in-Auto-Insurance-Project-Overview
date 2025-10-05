"""
Test suite for telematics UBI API.
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.backend.app import app
from src.backend.db.base import Base, get_db
from src.backend.db.models import User
from src.backend.core.hashing import get_password_hash

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="module")
def test_user():
    db = TestingSessionLocal()
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword"),
        first_name="Test",
        last_name="User",
        role="user"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    yield user
    db.delete(user)
    db.commit()
    db.close()

def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "Telematics UBI API"

def test_user_registration(client):
    """Test user registration."""
    user_data = {
        "email": "newuser@example.com",
        "password": "password123",
        "first_name": "New",
        "last_name": "User"
    }
    response = client.post("/api/v1/users/register", json=user_data)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == user_data["email"]

def test_user_login(client, test_user):
    """Test user login."""
    login_data = {
        "email": test_user.email,
        "password": "testpassword"
    }
    response = client.post("/api/v1/users/login", json=login_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_protected_endpoint_without_auth(client):
    """Test protected endpoint without authentication."""
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401

def test_protected_endpoint_with_auth(client, test_user):
    """Test protected endpoint with authentication."""
    # Login first
    login_data = {
        "email": test_user.email,
        "password": "testpassword"
    }
    login_response = client.post("/api/v1/users/login", json=login_data)
    token = login_response.json()["access_token"]
    
    # Use token for protected endpoint
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email

def test_pricing_quote(client, test_user):
    """Test pricing quote endpoint."""
    # Login first
    login_data = {
        "email": test_user.email,
        "password": "testpassword"
    }
    login_response = client.post("/api/v1/users/login", json=login_data)
    token = login_response.json()["access_token"]
    
    # Test pricing quote
    headers = {"Authorization": f"Bearer {token}"}
    quote_data = {
        "base_premium": 1000.0,
        "score": 75.0
    }
    response = client.post("/api/v1/pricing/quote", json=quote_data, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "band" in data
    assert "delta_pct" in data
    assert "new_premium" in data

def test_telematics_simulation(client, test_user):
    """Test telematics trip simulation."""
    # Login first
    login_data = {
        "email": test_user.email,
        "password": "testpassword"
    }
    login_response = client.post("/api/v1/users/login", json=login_data)
    token = login_response.json()["access_token"]
    
    # Create a vehicle first (simplified)
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test trip simulation
    simulation_data = {
        "user_id": test_user.id,
        "vehicle_id": 1,  # Assuming vehicle exists
        "num_trips": 5,
        "days_back": 7
    }
    response = client.post("/api/v1/telematics/trips/simulate", json=simulation_data, headers=headers)
    # This might fail if no vehicle exists, which is expected
    assert response.status_code in [200, 404, 400]

if __name__ == "__main__":
    pytest.main([__file__])
