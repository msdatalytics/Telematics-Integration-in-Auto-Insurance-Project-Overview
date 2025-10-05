"""
Security utilities and middleware.
"""
import os
from typing import List
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import time

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# CORS configuration
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")


def setup_security_middleware(app: FastAPI):
    """Setup security middleware for the FastAPI app."""
    
    # Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Trusted hosts
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*.localhost"]
    )
    
    # Request timing middleware
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response


def validate_gps_precision(lat: float, lon: float) -> tuple[float, float]:
    """Validate and bucketize GPS coordinates for privacy."""
    precision_decimals = int(os.getenv("GPS_PRECISION_DECIMALS", "5"))
    
    # Round to specified precision
    lat_bucketized = round(lat, precision_decimals)
    lon_bucketized = round(lon, precision_decimals)
    
    return lat_bucketized, lon_bucketized


def validate_data_retention(data_date: str) -> bool:
    """Check if data is within retention period."""
    from datetime import datetime, timedelta
    
    retention_days = int(os.getenv("DATA_RETENTION_DAYS", "365"))
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
    
    try:
        data_datetime = datetime.fromisoformat(data_date.replace('Z', '+00:00'))
        return data_datetime >= cutoff_date
    except ValueError:
        return False


def sanitize_user_data(user_data: dict) -> dict:
    """Sanitize user data for API responses."""
    # Remove sensitive fields
    sensitive_fields = ["hashed_password", "internal_notes", "admin_notes"]
    
    sanitized = {k: v for k, v in user_data.items() if k not in sensitive_fields}
    return sanitized


def validate_api_key(api_key: str) -> bool:
    """Validate API key for external integrations."""
    # In production, this would check against a database or external service
    valid_keys = os.getenv("VALID_API_KEYS", "").split(",")
    return api_key in valid_keys


def log_security_event(event_type: str, user_id: int, details: dict):
    """Log security events for monitoring."""
    # In production, this would write to a security log or SIEM system
    print(f"SECURITY_EVENT: {event_type} - User {user_id} - {details}")


def check_rate_limit(request: Request, limit: str = "100/minute"):
    """Check rate limit for a request."""
    return limiter.check_rate_limit(request, limit)


def get_client_ip(request: Request) -> str:
    """Get client IP address from request."""
    # Check for forwarded headers
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    return request.client.host if request.client else "unknown"


def validate_file_upload(file_content: bytes, max_size: int = 10 * 1024 * 1024) -> bool:
    """Validate file upload size and content."""
    if len(file_content) > max_size:
        return False
    
    # Add more validation as needed (file type, content scanning, etc.)
    return True


def generate_secure_filename(original_filename: str) -> str:
    """Generate a secure filename for uploads."""
    import uuid
    import os
    
    # Get file extension
    _, ext = os.path.splitext(original_filename)
    
    # Generate secure filename
    secure_name = f"{uuid.uuid4().hex}{ext}"
    
    return secure_name


def encrypt_sensitive_data(data: str) -> str:
    """Encrypt sensitive data for storage."""
    # In production, use proper encryption (AES, etc.)
    import base64
    
    encoded = base64.b64encode(data.encode()).decode()
    return encoded


def decrypt_sensitive_data(encrypted_data: str) -> str:
    """Decrypt sensitive data."""
    # In production, use proper decryption
    import base64
    
    decoded = base64.b64decode(encrypted_data.encode()).decode()
    return decoded
