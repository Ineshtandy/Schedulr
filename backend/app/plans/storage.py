"""Snowflake persistence for plan snapshots."""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from fastapi.encoders import jsonable_encoder

from app.conversations.storage import set_latest_plan
from app.db.snowflake import exec_query, fetch_one


def create_plan_snapshot(user_id: str, conversation_id: str, plan_obj: Dict[str, Any]) -> str:
    json_ready = jsonable_encoder(plan_obj)
    json_ready["conversation_id"] = conversation_id
    plan_id = json_ready["plan_id"]
    exec_query(
        """
        INSERT INTO plans (
          plan_id, conversation_id, user_id, goal, start_date, num_days, minutes_per_day, plan_json, created_at
        )
        SELECT %s, %s, %s, %s, %s::DATE, %s, %s, PARSE_JSON(%s), CURRENT_TIMESTAMP()
        """,
        (
            plan_id,
            conversation_id,
            user_id,
            json_ready["goal"],
            json_ready["start_date"],
            json_ready["num_days"],
            json_ready["minutes_per_day"],
            json.dumps(json_ready),
        ),
    )
    # set_latest_plan already updates updated_at, no need for touch_conversation
    set_latest_plan(conversation_id, plan_id)
    return plan_id


def get_plan_by_id(user_id: str, plan_id: str) -> Optional[Dict[str, Any]]:
    row = fetch_one(
        """
        SELECT conversation_id, TO_JSON(plan_json) AS plan_json
        FROM plans
        WHERE user_id = %s AND plan_id = %s
        """,
        (user_id, plan_id),
    )
    if not row or not row.get("plan_json"):
        return None
    payload = __import__("json").loads(row["plan_json"])
    payload["conversation_id"] = row["conversation_id"]
    return payload


def get_latest_plan_for_conversation(user_id: str, conversation_id: str) -> Optional[Dict[str, Any]]:
    row = fetch_one(
        """
        SELECT TO_JSON(p.plan_json) AS plan_json
        FROM conversations c
        JOIN plans p ON p.plan_id = c.latest_plan_id
        WHERE c.user_id = %s AND c.conversation_id = %s
        """,
        (user_id, conversation_id),
    )
    if not row or not row.get("plan_json"):
        return None
    return __import__("json").loads(row["plan_json"])
