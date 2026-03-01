"""Database initialization for Snowflake schema."""
from pathlib import Path

from app.db.snowflake import get_conn


SCHEMA_FILE = Path(__file__).resolve().parents[2] / "sql" / "schema.sql"


def initialize_schema() -> None:
    """Create required Snowflake tables if they do not already exist."""
    if not SCHEMA_FILE.exists():
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_FILE}")

    statements = [
        stmt.strip()
        for stmt in SCHEMA_FILE.read_text().split(";")
        if stmt.strip()
    ]

    conn = get_conn()
    try:
        cur = conn.cursor()
        try:
            for stmt in statements:
                cur.execute(stmt)
        finally:
            cur.close()
    finally:
        conn.close()
