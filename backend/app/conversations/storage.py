"""Snowflake persistence for conversations."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from app.db.snowflake import exec_query, fetch_all, fetch_one


DEFAULT_TITLE = "New chat"


def _auto_title_from_message(message: str, max_len: int = 48) -> str:
    clean = " ".join(message.strip().split())
    if not clean:
        return DEFAULT_TITLE
    return clean[:max_len]


def create_conversation(user_id: str, title: Optional[str] = None) -> str:
    conversation_id = str(uuid.uuid4())
    exec_query(
        """
        INSERT INTO conversations (conversation_id, user_id, title, state, created_at, updated_at)
        VALUES (%s, %s, %s, 'idle', CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())
        """,
        (conversation_id, user_id, title or DEFAULT_TITLE),
    )
    return conversation_id


def list_conversations(user_id: str) -> List[Dict[str, Any]]:
    return fetch_all(
        """
        SELECT conversation_id, user_id, title, state, latest_plan_id, pending_goal, 
               created_at, updated_at, is_deployed, deployment_id, tasklist_id, deployed_at
        FROM conversations
        WHERE user_id = %s
        ORDER BY updated_at DESC
        """,
        (user_id,),
    )


def get_conversation(user_id: str, conversation_id: str) -> Optional[Dict[str, Any]]:
    return fetch_one(
        """
        SELECT conversation_id, user_id, title, state, latest_plan_id, pending_goal, 
               created_at, updated_at, is_deployed, deployment_id, tasklist_id, deployed_at
        FROM conversations
        WHERE user_id = %s AND conversation_id = %s
        """,
        (user_id, conversation_id),
    )


def touch_conversation(conversation_id: str) -> None:
    exec_query(
        "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP() WHERE conversation_id = %s",
        (conversation_id,),
    )


def set_latest_plan(conversation_id: str, latest_plan_id: str) -> None:
    exec_query(
        """
        UPDATE conversations
        SET latest_plan_id = %s, state = 'idle', pending_goal = NULL, updated_at = CURRENT_TIMESTAMP()
        WHERE conversation_id = %s
        """,
        (latest_plan_id, conversation_id),
    )


def set_pending_goal(conversation_id: str, goal: str) -> None:
    exec_query(
        """
        UPDATE conversations
        SET pending_goal = %s, state = 'awaiting_info', updated_at = CURRENT_TIMESTAMP()
        WHERE conversation_id = %s
        """,
        (goal, conversation_id),
    )


def clear_pending_goal(conversation_id: str) -> None:
    exec_query(
        """
        UPDATE conversations
        SET pending_goal = NULL, state = 'idle', updated_at = CURRENT_TIMESTAMP()
        WHERE conversation_id = %s
        """,
        (conversation_id,),
    )


def update_conversation_title(user_id: str, conversation_id: str, title: str) -> None:
    exec_query(
        """
        UPDATE conversations
        SET title = %s, updated_at = CURRENT_TIMESTAMP()
        WHERE user_id = %s AND conversation_id = %s
        """,
        (title, user_id, conversation_id),
    )


def ensure_title_from_first_message(user_id: str, conversation_id: str, first_user_message: str) -> None:
    conversation = get_conversation(user_id, conversation_id)
    if not conversation:
        return
    if conversation.get("title") and conversation["title"] != DEFAULT_TITLE:
        return
    title = _auto_title_from_message(first_user_message)
    update_conversation_title(user_id, conversation_id, title)


def set_deployment_status(
    conversation_id: str, deployment_id: str, tasklist_id: str
) -> None:
    """Mark conversation as deployed with deployment details."""
    exec_query(
        """
        UPDATE conversations
        SET is_deployed = TRUE, 
            deployment_id = %s, 
            tasklist_id = %s, 
            deployed_at = CURRENT_TIMESTAMP(),
            updated_at = CURRENT_TIMESTAMP()
        WHERE conversation_id = %s
        """,
        (deployment_id, tasklist_id, conversation_id),
    )


def clear_deployment_status(conversation_id: str) -> None:
    """Clear deployment status after deletion."""
    exec_query(
        """
        UPDATE conversations
        SET is_deployed = FALSE, 
            deployment_id = NULL, 
            tasklist_id = NULL, 
            deployed_at = NULL,
            updated_at = CURRENT_TIMESTAMP()
        WHERE conversation_id = %s
        """,
        (conversation_id,),
    )
