"""
Async SQLAlchemy database engine and session management.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from sqlalchemy.pool import NullPool

from app.core.config import get_settings

settings = get_settings()

# ---------------------------------------------------------------------------
# Engine Configuration
# ---------------------------------------------------------------------------
connect_args: dict = {}
engine_kwargs: dict = {
    "echo": settings.debug,
}

if "sqlite" in settings.database_url:
    connect_args["check_same_thread"] = False
    engine_kwargs["connect_args"] = connect_args
else:
    # Disable asyncpg statement cache for PgBouncer / Supavisor poolers
    connect_args["statement_cache_size"] = 0
    connect_args["prepared_statement_cache_size"] = 0

    # Set PostgreSQL search_path to user-configured schema
    schema = getattr(settings, "supabase_schema", None)
    if schema:
        connect_args["server_settings"] = {
            "search_path": f"{schema},public"
        }

    engine_kwargs["connect_args"] = connect_args
    engine_kwargs["pool_pre_ping"] = True

    # NullPool for transaction pooler (port 6543) avoids client-side connection hoarding
    if ":6543" in settings.database_url or "pooler.supabase.com" in settings.database_url:
        engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs["pool_size"] = 10
        engine_kwargs["max_overflow"] = 20

engine = create_async_engine(
    settings.database_url,
    **engine_kwargs,
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ---------------------------------------------------------------------------
# Base model for all ORM models
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """Declarative base for all SQLAlchemy models."""
    pass


# ---------------------------------------------------------------------------
# Dependency for FastAPI route handlers
# ---------------------------------------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a database session.

    Usage::

        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database sessions outside of FastAPI route handlers.
    Use this in background tasks or service-layer code that does not have
    access to the FastAPI DI system.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
