"""Snowflake connection and query helpers with connection pooling."""
from __future__ import annotations

import logging
import queue
import threading
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Sequence

import snowflake.connector

from app.config import settings

logger = logging.getLogger(__name__)

# ── Connection pool ──────────────────────────────────────────────────
_POOL_SIZE = 5
_pool: queue.Queue[snowflake.connector.SnowflakeConnection] = queue.Queue(maxsize=_POOL_SIZE)
_pool_lock = threading.Lock()
_pool_initialized = False


def _create_conn() -> snowflake.connector.SnowflakeConnection:
    """Create a fresh Snowflake connection."""
    return snowflake.connector.connect(
        account=settings.SNOWFLAKE_ACCOUNT,
        user=settings.SNOWFLAKE_USER,
        password=settings.SNOWFLAKE_PASSWORD,
        role=settings.SNOWFLAKE_ROLE,
        warehouse=settings.SNOWFLAKE_WAREHOUSE,
        database=settings.SNOWFLAKE_DATABASE,
        schema=settings.SNOWFLAKE_SCHEMA,
        autocommit=True,
    )


def _init_pool() -> None:
    """Lazily seed the pool with connections on first use."""
    global _pool_initialized
    with _pool_lock:
        if _pool_initialized:
            return
        for _ in range(_POOL_SIZE):
            try:
                _pool.put_nowait(_create_conn())
            except Exception:
                logger.warning("Failed to pre-create pool connection", exc_info=True)
        _pool_initialized = True


def _is_alive(conn: snowflake.connector.SnowflakeConnection) -> bool:
    """Quick liveness check without a network round-trip when possible."""
    try:
        if conn.is_closed():
            return False
        # Light validation: run a trivial query
        cur = conn.cursor()
        try:
            cur.execute("SELECT 1")
            return True
        finally:
            cur.close()
    except Exception:
        return False


def _borrow() -> snowflake.connector.SnowflakeConnection:
    """Get a connection from the pool, creating one if needed."""
    _init_pool()
    try:
        conn = _pool.get_nowait()
        if _is_alive(conn):
            return conn
        # Dead connection – close quietly and create a fresh one
        try:
            conn.close()
        except Exception:
            pass
    except queue.Empty:
        pass
    return _create_conn()


def _return(conn: snowflake.connector.SnowflakeConnection) -> None:
    """Return a connection to the pool (or discard if pool is full)."""
    try:
        _pool.put_nowait(conn)
    except queue.Full:
        try:
            conn.close()
        except Exception:
            pass


def get_conn() -> snowflake.connector.SnowflakeConnection:
    """Public API – returns a *pooled* connection.

    Callers that use ``get_conn()`` directly (e.g. ``db/init.py``) are
    responsible for closing the connection themselves.  The pool helpers
    ``_borrow`` / ``_return`` are used automatically by ``_cursor()``.
    """
    return _borrow()


@contextmanager
def _cursor():
    conn = _borrow()
    try:
        cur = conn.cursor(snowflake.connector.DictCursor)
        try:
            yield cur
        finally:
            cur.close()
        _return(conn)
    except Exception:
        # On error, discard the connection instead of returning it
        try:
            conn.close()
        except Exception:
            pass
        raise


def exec_query(sql: str, params: Optional[Sequence[Any]] = None) -> None:
    """Execute a parameterized statement without returning rows."""
    with _cursor() as cur:
        cur.execute(sql, params or ())


def fetch_one(sql: str, params: Optional[Sequence[Any]] = None) -> Optional[Dict[str, Any]]:
    """Fetch a single row as a dictionary."""
    with _cursor() as cur:
        cur.execute(sql, params or ())
        row = cur.fetchone()
        if row is None:
            return None
        return {k.lower(): v for k, v in row.items()}


def fetch_all(sql: str, params: Optional[Sequence[Any]] = None) -> List[Dict[str, Any]]:
    """Fetch all rows as dictionaries."""
    with _cursor() as cur:
        cur.execute(sql, params or ())
        rows = cur.fetchall()
        return [{k.lower(): v for k, v in row.items()} for row in rows]
