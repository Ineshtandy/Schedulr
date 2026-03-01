"""Deploy plans to Google Tasks with Snowflake traceability."""
from __future__ import annotations

from typing import Dict

from app.auth.token_store import get_refresh_token
from app.deployments.storage import create_deployment, upsert_deployed_task
from app.google_tasks.client import (
    create_task,
    create_tasklist,
    delete_tasklist,
    refresh_access_token,
)
from app.models.schemas import Plan


def _source_task_key(day_index: int, task_index: int) -> str:
    return f"d{day_index + 1}_t{task_index + 1}"


async def deploy_plan_to_tasks(user_id: str, conversation_id: str, plan: Plan) -> Dict:
    refresh_token = get_refresh_token(user_id)
    if not refresh_token:
        raise ValueError("No refresh token found. Please sign in again.")

    access_token = await refresh_access_token(refresh_token)
    tasklist_title = f"📅 {plan.goal[:80]} ({conversation_id[:8]})"

    tasklist = await create_tasklist(access_token, tasklist_title)
    tasklist_id = tasklist["id"]

    created_count = 0
    updated_count = 0
    pending_mappings = []

    for day_index, day in enumerate(plan.days):
        due_timestamp = f"{day.date}T12:00:00Z"
        for task_index, task in enumerate(day.tasks):
            source_key = _source_task_key(day_index, task_index)
            notes = (
                f"ConversationId: {conversation_id}\n"
                f"PlanId: {plan.plan_id}\n"
                f"SourceTaskKey: {source_key}\n"
                f"Duration: {task.duration_min} min\n"
                f"Priority: {task.priority}\n\n"
                f"{task.notes or ''}"
            )
            created = await create_task(
                access_token=access_token,
                tasklist_id=tasklist_id,
                title=task.title,
                notes=notes,
                due_rfc3339=due_timestamp,
            )
            created_count += 1
            pending_mappings.append(
                {
                    "source_task_key": source_key,
                    "google_task_id": created["id"],
                    "due_date": day.date,
                }
            )

    deployment_id = create_deployment(
        user_id=user_id,
        conversation_id=conversation_id,
        plan_id=plan.plan_id,
        tasklist_id=tasklist_id,
        tasklist_title=tasklist_title,
        created_count=created_count,
        updated_count=updated_count,
    )

    for mapping in pending_mappings:
        upsert_deployed_task(
            deployment_id=deployment_id,
            user_id=user_id,
            conversation_id=conversation_id,
            plan_id=plan.plan_id,
            source_task_key=mapping["source_task_key"],
            google_task_id=mapping["google_task_id"],
            due_date=mapping["due_date"],
        )

    return {
        "deployment_id": deployment_id,
        "tasklist_id": tasklist_id,
        "tasklist_title": tasklist_title,
        "created_count": created_count,
        "updated_count": updated_count,
    }


async def delete_plan_from_tasks(user_id: str, tasklist_id: str) -> None:
    """Delete a deployed plan from Google Tasks."""
    refresh_token = get_refresh_token(user_id)
    if not refresh_token:
        raise ValueError("No refresh token found. Please sign in again.")

    access_token = await refresh_access_token(refresh_token)
    await delete_tasklist(access_token, tasklist_id)


async def update_plan_in_tasks(
    user_id: str, conversation_id: str, old_tasklist_id: str, new_plan: Plan
) -> Dict:
    """Update a deployed plan by deleting the old one and deploying the new one."""
    # Delete the old tasklist
    await delete_plan_from_tasks(user_id, old_tasklist_id)
    
    # Deploy the new plan
    return await deploy_plan_to_tasks(user_id, conversation_id, new_plan)
