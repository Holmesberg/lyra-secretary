import sys
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# Add the backend directory to sys.path so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.db.base import Base
# Import models to ensure they are attached to Base.metadata
from app.db import models

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def get_url():
    # Returns DATABASE_URL as-is. SQLAlchemy infers dialect from the URL
    # prefix (sqlite:// vs postgresql://), so both local dev and the
    # Supabase-backed lyraos.org deployment work without a code branch.
    return settings.DATABASE_URL

def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section)
    if configuration is None:
        configuration = {}
    configuration["sqlalchemy.url"] = get_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Supabase pooler enforces a default statement_timeout (~8s) that
        # was killing migration 033's CREATE TABLE during pg_type catalog
        # update (`pg_type_typname_nsp_index` insert). Disabling for the
        # migration session only — application sessions still respect
        # whatever timeout is configured upstream. This is scoped to one
        # connection (NullPool, so the timeout reset only affects this
        # one migration run).
        # Postgres-only — SQLite ignores SET commands silently, but we
        # guard with dialect check anyway.
        if connection.dialect.name == "postgresql":
            connection.exec_driver_sql("SET statement_timeout = 0")
            connection.exec_driver_sql("SET lock_timeout = 0")
            connection.exec_driver_sql("SET idle_in_transaction_session_timeout = 0")

        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
