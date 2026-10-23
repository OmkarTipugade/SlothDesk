"""
SlothDesk FastAPI application.

Entry point for the backend server.  Configures CORS, exception handling,
database initialization, and route registration.
"""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import get_settings
from app.database import init_db
from app.services.ollama import OllamaError

# ── Logging ─────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("slothdesk")

# ── App ─────────────────────────────────────────────────────────

settings = get_settings()

app = FastAPI(
    title="SlothDesk API",
    description="Local-first AI file organizer",
    version="0.1.0",
)

# ── CORS ────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ── Exception handlers ──────────────────────────────────────────


@app.exception_handler(OllamaError)
async def ollama_error_handler(request: Request, exc: OllamaError) -> JSONResponse:
    """Convert Ollama errors to appropriate HTTP responses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc)},
    )


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError) -> JSONResponse:
    """Handle configuration and runtime errors."""
    logger.error("RuntimeError: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


@app.exception_handler(Exception)
async def general_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler — never leaks stack traces."""
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected internal error occurred."},
    )


# ── Startup ─────────────────────────────────────────────────────


@app.on_event("startup")
async def startup() -> None:
    """Initialize database and verify configuration on startup."""
    logger.info("SlothDesk starting up...")

    # Initialize SQLite
    init_db(settings.database_path)
    logger.info("Database initialized at %s", settings.database_path)

    # Ensure root directory exists (create the demo directory if using default)
    if not os.path.isdir(settings.slothdesk_root):
        # Only auto-create if it's the default demo directory
        default_root = os.path.join(os.path.expanduser("~"), "SlothDesk_Demo")
        if os.path.realpath(settings.slothdesk_root) == os.path.realpath(default_root):
            os.makedirs(settings.slothdesk_root, exist_ok=True)
            logger.info("Created demo directory: %s", settings.slothdesk_root)
        else:
            logger.warning(
                "SLOTHDESK_ROOT does not exist: %s — scan and plan endpoints will fail.",
                settings.slothdesk_root,
            )
    else:
        logger.info("Working directory: %s", settings.slothdesk_root)

    logger.info("Ollama endpoint: %s (model: %s)", settings.ollama_url, settings.ollama_model)
    logger.info("SlothDesk ready on %s:%d", settings.host, settings.port)


# ── Routes ──────────────────────────────────────────────────────

app.include_router(router)


# ── Root redirect ───────────────────────────────────────────────


@app.get("/")
async def root():
    """Root endpoint — quick check that the server is running."""
    return {"message": "Welcome to SlothDesk!", "docs": "/docs"}