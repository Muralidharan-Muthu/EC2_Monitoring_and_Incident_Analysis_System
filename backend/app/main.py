"""
FastAPI application entry point.

Assembles all routes, configures middleware, and sets up startup/shutdown hooks.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.api.routes import health, metrics, anomalies, incidents, dashboard

# Configure structured logging before anything else
configure_logging()
logger = get_logger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    logger.info(
        "application_startup",
        name=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )
    yield
    logger.info("application_shutdown")


def create_app() -> FastAPI:
    """
    Application factory.

    Returns a configured FastAPI application instance.
    Using a factory pattern makes the app easier to test.
    """
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "EC2 Monitoring and Incident Analysis System — "
            "real-time Linux system metrics, anomaly detection, "
            "incident correlation, and LangGraph-powered AI analysis."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ---- CORS ----
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---- Routes ----
    api_prefix = "/api"

    app.include_router(health.router, prefix=api_prefix)
    app.include_router(metrics.router, prefix=api_prefix)
    app.include_router(anomalies.router, prefix=api_prefix)
    app.include_router(incidents.router, prefix=api_prefix)
    app.include_router(dashboard.router, prefix=api_prefix)

    return app


app = create_app()
