"""Snowflake persistence for users."""
from typing import Any, Dict, Optional

from app.db.snowflake import exec_query, fetch_one


def upsert_user(user_id: str, email: str) -> None:
    exec_query(
        """
        MERGE INTO users AS target
        USING (SELECT %s AS user_id, %s AS email) AS src
        ON target.user_id = src.user_id
        WHEN MATCHED THEN
          UPDATE SET email = src.email, updated_at = CURRENT_TIMESTAMP()
        WHEN NOT MATCHED THEN
          INSERT (user_id, email, created_at, updated_at)
          VALUES (src.user_id, src.email, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())
        """,
        (user_id, email),
    )


def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    return fetch_one(
        "SELECT user_id, email, created_at, updated_at FROM users WHERE user_id = %s",
        (user_id,),
    )
