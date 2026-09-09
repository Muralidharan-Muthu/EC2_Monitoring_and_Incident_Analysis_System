"""
Alembic environment script.

Reads the database URL from the environment, imports all ORM models
so Alembic can detect them for autogenerate, and runs migrations.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from dotenv import load_dotenv

# Load .env so DATABASE_URL is available during migration runs
load_dotenv()

# Alembic Config object
config = context.config

# Override sqlalchemy.url with the environment variable
database_url = os.environ.get("DATABASE_URL", "")
if database_url:
    # Alembic needs a synchronous URL; replace asyncpg driver for migrations
    sync_url = database_url.replace(
        "postgresql+asyncpg://", "postgresql+psycopg2://"
    ).replace(
        "postgresql+asyncpg:", "postgresql:"
    )
    config.set_main_option("sqlalchemy.url", sync_url)

# Set up loggers from the alembic.ini file
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models so Alembic can discover them for autogenerate
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import Base  # noqa: E402
import app.models  # noqa: E402, F401 — triggers model imports

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in offline mode (no DB connection needed)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in online mode (requires DB connection)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
