"""FastAPI main application with CORS and route configuration."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, plans
from app.config import settings


# Create FastAPI application
app = FastAPI(
    title="Schedulr API",
    description="Backend API for Schedulr - AI-powered planning assistant",
    version="0.1.0"
)

# Configure CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_BASE_URL],  # Frontend URL
    allow_credentials=True,  # CRITICAL: Allows cookies to be sent
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(plans.router, prefix="/api/plan", tags=["Plans"])


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "Schedulr API",
        "version": "0.1.0"
    }


@app.get("/health")
async def health_check():
    """Health check for monitoring."""
    return {
        "status": "healthy",
        "environment": settings.APP_ENV
    }


# Run with: uvicorn app.main:app --reload --port 8000
