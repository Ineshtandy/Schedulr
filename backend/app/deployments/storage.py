"""Snowflake persistence for deployments and deployed task mappings."""
from __future__ import annotations

import uuid
from typing import Dict

from app.db.snowflake import exec_query


def create_deployment(
    user_id: str,
    conversation_id: str,
    plan_id: str,
    tasklist_id: str,
    tasklist_title: str,
    created_count: int,
    updated_count: int,
) -> str:
    deployment_id = str(uuid.uuid4())
    exec_query(
        """
        INSERT INTO deployments (
            deployment_id, user_id, conversation_id, plan_id, tasklist_id, tasklist_title,
            created_count, updated_count, deployed_at, last_synced_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())
        """,
        (
            deployment_id,
            user_id,
            conversation_id,
            plan_id,
            tasklist_id,
            tasklist_title,
            created_count,
            updated_count,
        ),
    )
    return deployment_id


def upsert_deployed_task(
    deployment_id: str,
    user_id: str,
    conversation_id: str,
    plan_id: str,
    source_task_key: str,
    google_task_id: str,
    due_date: str,
) -> None:
    exec_query(
        """
        MERGE INTO deployed_tasks AS target
        USING (
          SELECT %s AS deployment_id, %s AS source_task_key
        ) AS src
        ON target.deployment_id = src.deployment_id
           AND target.source_task_key = src.source_task_key
        WHEN MATCHED THEN UPDATE SET
          google_task_id = %s,
          user_id = %s,
          conversation_id = %s,
          plan_id = %s,
          due_date = %s::DATE,
          updated_at = CURRENT_TIMESTAMP()
        WHEN NOT MATCHED THEN INSERT (
          deployment_id, user_id, conversation_id, plan_id, source_task_key,
          google_task_id, due_date, created_at, updated_at
        ) VALUES (
          %s, %s, %s, %s, %s, %s, %s::DATE, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()
        )
        """,
        (
            deployment_id,
            source_task_key,
            google_task_id,
            user_id,
            conversation_id,
            plan_id,
            due_date,
            deployment_id,
            user_id,
            conversation_id,
            plan_id,
            source_task_key,
            google_task_id,
            due_date,
        ),
    )
