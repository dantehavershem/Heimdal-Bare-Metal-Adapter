"""Serialize initial schema creation and the v0.1 PostgreSQL size upgrade."""
from sqlalchemy import text
from app.core.db import Base, engine

def initialize_schema():
    from app.models import entities  # register metadata
    with engine.begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(72190314)"))
        Base.metadata.create_all(connection)
        kind = connection.execute(text("SELECT data_type FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='media' AND column_name='size_bytes'")).scalar_one()
        if kind == 'integer':
            connection.execute(text('ALTER TABLE media ALTER COLUMN size_bytes TYPE BIGINT'))
