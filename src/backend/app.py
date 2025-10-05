"""
Main FastAPI application.
"""
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os

from .settings import settings
from .core.security import setup_security_middleware
from .db.base import create_tables
from .api import (
    routes_telematics,
    routes_score,
    routes_pricing,
    routes_users
)


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Telematics Integration in Auto Insurance (UBI: PAYD/PHYD)",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Setup security middleware
    setup_security_middleware(app)
    
    # Include API routes
    app.include_router(
        routes_users.router,
        prefix=f"{settings.API_V1_STR}/users",
        tags=["users"]
    )
    
    app.include_router(
        routes_telematics.router,
        prefix=f"{settings.API_V1_STR}/telematics",
        tags=["telematics"]
    )
    
    app.include_router(
        routes_score.router,
        prefix=f"{settings.API_V1_STR}/score",
        tags=["scoring"]
    )
    
    app.include_router(
        routes_pricing.router,
        prefix=f"{settings.API_V1_STR}/pricing",
        tags=["pricing"]
    )
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "version": settings.VERSION,
            "environment": "development" if settings.DEBUG else "production"
        }
    
    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "message": "Telematics UBI API",
            "version": settings.VERSION,
            "docs": "/docs",
            "health": "/health"
        }
    
    # Global exception handler
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        """Handle HTTP exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "error_code": getattr(exc, "error_code", None),
                "timestamp": "2024-01-01T00:00:00Z"  # Would use datetime.utcnow().isoformat()
            }
        )
    
    # Startup event
    @app.on_event("startup")
    async def startup_event():
        """Initialize application on startup."""
        # Create database tables
        create_tables()
        
        # Initialize ML models (if available)
        try:
            from .ml.score_service import ScoreService
            score_service = ScoreService()
            await score_service.initialize()
        except Exception as e:
            print(f"Warning: Could not initialize ML models: {e}")
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
