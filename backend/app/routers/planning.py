"""Conversation planning endpoints for generate/update loop."""
from __future__ import annotations

import asyncio
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from app.conversations.storage import (
    clear_pending_goal,
    ensure_title_from_first_message,
    get_conversation,
    set_pending_goal,
)
from app.messages.storage import add_message
from app.models.schemas import ConversationGenerateRequest, ConversationPlanResponse, Plan, PlanGenerateRequest
from app.plans.orchestrator import ask_questions, generate_plan_orchestrated, update_plan_orchestrated
from app.plans.storage import create_plan_snapshot, get_latest_plan_for_conversation
from app.routers.auth import get_session_data

logger = logging.getLogger(__name__)
router = APIRouter()

# Shared thread pool for running blocking DB writes in the background
_bg_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="bg-db")


def _fire_and_forget(fn, *args, **kwargs) -> None:
    """Submit a blocking function to run in the background thread pool.

    Errors are logged but never propagated to the caller.
    """
    def _wrapper():
        try:
            fn(*args, **kwargs)
        except Exception:
            logger.exception("Background task %s failed", fn.__name__)
    _bg_pool.submit(_wrapper)


def _extract_num_days(text: str) -> Optional[int]:
    m = re.search(r"(\d+)\s*(day|days|week|weeks)", text.lower())
    if not m:
        return None
    value = int(m.group(1))
    unit = m.group(2)
    return min(90, value * 7) if unit.startswith("week") else min(90, value)


def _extract_minutes(text: str) -> Optional[int]:
    m = re.search(r"(\d+)\s*(minute|minutes|min|hour|hours|hr|hrs)", text.lower())
    if not m:
        return None
    value = int(m.group(1))
    unit = m.group(2)
    if unit.startswith("hour") or unit.startswith("hr"):
        value *= 60
    return min(480, value)


def _extract_start_date(text: str) -> Optional[str]:
    m = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    if m:
        return m.group(1)
    return None


@router.post("/conversations/{conversation_id}/plan/generate", response_model=ConversationPlanResponse)
async def generate_plan_for_conversation(
    conversation_id: str,
    request: ConversationGenerateRequest,
    session: dict = Depends(get_session_data),
):
    user_id = session["user_id"]
    conversation = get_conversation(user_id=user_id, conversation_id=conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    user_message = request.user_message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Save user message (critical) + title update (cosmetic, background)
    add_message(conversation_id=conversation_id, user_id=user_id, role="user", content=user_message)
    _fire_and_forget(ensure_title_from_first_message, user_id=user_id, conversation_id=conversation_id, first_user_message=user_message)

    if not conversation.get("latest_plan_id") and conversation.get("state") != "awaiting_info":
        questions = ask_questions(user_message)
        question_text = "\n".join([f"{idx + 1}. {q}" for idx, q in enumerate(questions)])
        # Assistant message + state update are non-blocking
        _fire_and_forget(
            add_message,
            conversation_id=conversation_id,
            user_id=user_id,
            role="assistant",
            content=f"Before I build your first plan, please answer:\n{question_text}",
        )
        _fire_and_forget(set_pending_goal, conversation_id=conversation_id, goal=user_message)
        return ConversationPlanResponse(state="awaiting_info", questions=questions)

    if not conversation.get("latest_plan_id") and conversation.get("state") == "awaiting_info":
        base_goal = conversation.get("pending_goal") or "Create a practical plan"
        num_days = request.num_days or _extract_num_days(user_message) or 14
        minutes_per_day = request.minutes_per_day or _extract_minutes(user_message) or 90
        start_date = request.start_date or _extract_start_date(user_message) or datetime.utcnow().date().isoformat()

        plan_request = PlanGenerateRequest(
            goal=base_goal,
            num_days=num_days,
            minutes_per_day=minutes_per_day,
            start_date=start_date,
            preferences=request.preferences or user_message,
        )
        plan = generate_plan_orchestrated(plan_request, user_id=user_id)
        # Plan snapshot is critical (must complete before response)
        create_plan_snapshot(user_id=user_id, conversation_id=conversation_id, plan_obj=plan.model_dump(mode="json"))
        # These are non-critical: fire-and-forget
        _fire_and_forget(clear_pending_goal, conversation_id)
        _fire_and_forget(add_message, conversation_id=conversation_id, user_id=user_id, role="assistant", content="Plan generated.")
        return ConversationPlanResponse(state="idle", plan_id=plan.plan_id, plan=plan)

    raise HTTPException(
        status_code=400,
        detail="This conversation already has a plan. Use update endpoint for further changes.",
    )


@router.post("/conversations/{conversation_id}/plan/update", response_model=ConversationPlanResponse)
async def update_plan_for_conversation(
    conversation_id: str,
    request: ConversationGenerateRequest,
    session: dict = Depends(get_session_data),
):
    user_id = session["user_id"]
    conversation = get_conversation(user_id=user_id, conversation_id=conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    existing_data = get_latest_plan_for_conversation(user_id=user_id, conversation_id=conversation_id)
    if not existing_data:
        raise HTTPException(status_code=400, detail="No plan exists yet. Start with generate endpoint.")

    message_text = request.user_message.strip()
    add_message(conversation_id=conversation_id, user_id=user_id, role="user", content=message_text)

    existing_plan = Plan(**existing_data)
    updated_plan = update_plan_orchestrated(existing_plan, message_text, user_id=user_id)
    # Plan snapshot is critical (must complete before response)
    create_plan_snapshot(user_id=user_id, conversation_id=conversation_id, plan_obj=updated_plan.model_dump(mode="json"))
    # Assistant message is non-critical: fire-and-forget
    _fire_and_forget(add_message, conversation_id=conversation_id, user_id=user_id, role="assistant", content="Plan updated.")
    return ConversationPlanResponse(state="idle", plan_id=updated_plan.plan_id, plan=updated_plan)
