from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://") and "+psycopg" not in url:
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def get_database_url(database_url: str | None = None) -> str:
    load_dotenv()
    url = database_url or os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not configured")
    return normalize_database_url(url)


def get_engine(database_url: str | None = None, **kwargs) -> Engine:
    return create_engine(get_database_url(database_url), **kwargs)


def init_db(database_url: str | None = None) -> Engine:
    engine = get_engine(database_url)
    schema = Path(__file__).resolve().parents[2] / "database" / "schema.sql"
    if not schema.exists():
        schema = Path(sys.prefix) / "share" / "modeltrace" / "database" / "schema.sql"
    if not schema.exists():
        raise FileNotFoundError(f"ModelTrace database schema not found: {schema}")

    with engine.begin() as connection:
        connection.exec_driver_sql(schema.read_text(encoding="utf-8"))
    return engine
