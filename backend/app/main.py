"""FastAPI main application with CORS and route configuration."""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from urllib.parse import urlparse
from app.routers import auth, conversations, planning, deploy
from app.config import settings
from app.db.init import initialize_schema


logger = logging.getLogger(__name__)


# Create FastAPI application
app = FastAPI(
    title="Schedulr API",
    description="Backend API for Schedulr - AI-powered planning assistant",
    version="0.1.0"
)


@app.on_event("startup")
async def on_startup() -> None:
    """Initialize persistent schema before serving traffic."""
    try:
        initialize_schema()
    except Exception as exc:
        logger.exception("Failed to initialize database schema during startup")
        raise RuntimeError(
            "Startup failed while initializing Snowflake schema. "
            "Verify SNOWFLAKE_* environment variables and connectivity."
        ) from exc


def _build_allowed_origins() -> list[str]:
    origins = {settings.FRONTEND_BASE_URL.rstrip("/")}

    if settings.CORS_ALLOWED_ORIGINS.strip():
        for origin in settings.CORS_ALLOWED_ORIGINS.split(","):
            cleaned = origin.strip().rstrip("/")
            if cleaned:
                origins.add(cleaned)

    parsed = urlparse(settings.FRONTEND_BASE_URL)
    if parsed.scheme and parsed.hostname and parsed.port:
        if parsed.hostname == "localhost":
            origins.add(f"{parsed.scheme}://127.0.0.1:{parsed.port}")
        elif parsed.hostname == "127.0.0.1":
            origins.add(f"{parsed.scheme}://localhost:{parsed.port}")

    return sorted(origins)

# Configure CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=_build_allowed_origins(),
    allow_credentials=True,  # CRITICAL: Allows cookies to be sent
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
# Include the /me endpoint from auth at /api level (not /api/auth)
app.add_api_route("/api/me", auth.get_current_user, methods=["GET"], tags=["Authentication"])
app.include_router(conversations.router, prefix="/api", tags=["Conversations"])
app.include_router(planning.router, prefix="/api", tags=["Planning"])
app.include_router(deploy.router, prefix="/api", tags=["Deploy"])


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


# Run with: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
