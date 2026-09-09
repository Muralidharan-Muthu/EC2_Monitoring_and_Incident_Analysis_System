"""
Alembic environment script.

Reads the database URL from the environment, imports all ORM models
so Alembic can detect them for autogenerate, and runs migrations.
"""

from __future__ import annotations

import os
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from dotenv import load_dotenv

# Load .env so DATABASE_URL is available during migration runs
load_dotenv()

# Alembic Config object
config = context.config

# Override sqlalchemy.url with the environment variable
database_url = os.environ.get("DATABASE_URL", "")
if not database_url:
    try:
        from app.core.config import get_settings
        database_url = get_settings().database_url
    except Exception:
        pass

if database_url:
    # Escape % characters for ConfigParser interpolation
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

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


def do_run_migrations(connection) -> None:
    schema = os.environ.get("SUPABASE_SCHEMA") or os.environ.get("DATABASE_SCHEMA", "ec2_monitoring_working")
    kwargs = {"connection": connection, "target_metadata": target_metadata}
    if schema:
        kwargs["version_table_schema"] = schema
    context.configure(**kwargs)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using async engine (asyncpg)."""
    schema = os.environ.get("SUPABASE_SCHEMA") or os.environ.get("DATABASE_SCHEMA", "ec2_monitoring_working")
    connect_args = {"statement_cache_size": 0}
    if schema:
        connect_args["server_settings"] = {"search_path": f"{schema},public"}

    database_url = config.get_main_option("sqlalchemy.url")

    # Ensure the target schema exists before running migration DDL
    if "postgresql" in database_url and schema:
        try:
            import asyncpg
            from sqlalchemy.engine.url import make_url
            u = make_url(database_url)
            raw_conn = await asyncpg.connect(
                user=u.username,
                password=u.password,
                host=u.host,
                port=u.port or 5432,
                database=u.database,
                statement_cache_size=0,
                ssl='require' if (u.port == 6543 or 'supabase.com' in (u.host or '')) else 'prefer'
            )
            await raw_conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema};")
            await raw_conn.close()
        except Exception:
            pass

    from sqlalchemy.ext.asyncio import create_async_engine
    connectable = create_async_engine(
        database_url,
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in online mode (requires DB connection)."""
    try:
        asyncio.run(run_async_migrations())
    except (ConnectionRefusedError, OSError) as exc:
        import sys
        sys.stderr.write(
            f"\n[Alembic Warning] Could not connect to PostgreSQL database: {exc}\n"
            "Please ensure your PostgreSQL server is running (e.g., 'docker compose up -d db') "
            "or set DATABASE_URL in backend/.env to a reachable database.\n\n"
        )
        sys.exit(1)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
