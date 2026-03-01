"""Snowflake persistence for conversation messages."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List

from app.db.snowflake import exec_query, fetch_all


def add_message(conversation_id: str, user_id: str, role: str, content: str) -> str:
    message_id = str(uuid.uuid4())
    exec_query(
        """
        INSERT INTO messages (message_id, conversation_id, user_id, role, content, created_at)
        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP())
        """,
        (message_id, conversation_id, user_id, role, content),
    )
    return message_id


def list_messages(conversation_id: str, user_id: str) -> List[Dict[str, Any]]:
    return fetch_all(
        """
        SELECT message_id, role, content, created_at
        FROM messages
        WHERE conversation_id = %s AND user_id = %s
        ORDER BY created_at ASC
        """,
        (conversation_id, user_id),
    )
