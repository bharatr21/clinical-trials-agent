"""FastAPI application for the clinical trials agent."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request

from clinical_trials_agent.agent import close_checkpointer, init_checkpointer
from clinical_trials_agent.api.rate_limit import limiter
from clinical_trials_agent.api.routes import conversations_router, query_router
from clinical_trials_agent.config import get_settings
from clinical_trials_agent.database import close_app_database, init_app_database

# Configure logging (set LOG_LEVEL=DEBUG for verbose output)
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,  # Override any existing configuration
)
# Set log level for our package specifically
logging.getLogger("clinical_trials_agent").setLevel(
    getattr(logging, log_level, logging.INFO)
)
# Reduce noise from httpx
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
logger.info(f"Log level set to: {log_level}")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    """Application lifespan manager for startup and shutdown."""
    # Startup
    logger.info("Starting application...")
    await init_app_database()
    await init_checkpointer()
    logger.info("Application started successfully")

    yield

    # Shutdown
    logger.info("Shutting down application...")
    await close_checkpointer()
    await close_app_database()
    logger.info("Application shutdown complete")


app = FastAPI(
    title="Clinical Trials Agent API",
    description="Text-to-SQL agent for querying the AACT clinical trials database",
    version="0.1.0",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Return 429 in the same JSON format the frontend expects."""
    logger.warning(f"Rate limit exceeded: {request.url.path} {exc.detail}")
    return JSONResponse(
        status_code=429,
        content={"detail": "rate_limit"},
    )


app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Client-ID"],  # Allow frontend to read client ID header
)

# Include routers
app.include_router(query_router)
app.include_router(conversations_router)


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}


@app.get("/")
async def root() -> dict:
    """Root endpoint with API information."""
    return {
        "name": "Clinical Trials Agent API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }
