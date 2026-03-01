"""Conversation endpoints for chat list and thread loading."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.conversations.storage import create_conversation, get_conversation, list_conversations, update_conversation_title
from app.messages.storage import list_messages
from app.models.schemas import (
    Conversation,
    ConversationCreateResponse,
    ConversationDetailResponse,
    ConversationUpdateRequest,
    MessageItem,
    Plan,
    UserInfo,
)
from app.plans.storage import get_latest_plan_for_conversation
from app.routers.auth import get_session_data

# Thread pool for parallel DB reads
_read_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="db-read")


router = APIRouter()

@router.get("/conversations", response_model=List[Conversation])
async def get_conversations(session: dict = Depends(get_session_data)):
    user_id = session["user_id"]
    rows = list_conversations(user_id)
    return [Conversation(**row) for row in rows]


@router.post("/conversations", response_model=ConversationCreateResponse)
async def post_conversation(session: dict = Depends(get_session_data)):
    user_id = session["user_id"]
    conversation_id = create_conversation(user_id=user_id)
    return ConversationCreateResponse(conversation_id=conversation_id)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation_detail(conversation_id: str, session: dict = Depends(get_session_data)):
    user_id = session["user_id"]
    conversation = get_conversation(user_id=user_id, conversation_id=conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Run messages + plan fetch in parallel (both are independent reads)
    loop = asyncio.get_event_loop()
    messages_future = loop.run_in_executor(
        _read_pool, list_messages, conversation_id, user_id
    )
    plan_future = loop.run_in_executor(
        _read_pool, get_latest_plan_for_conversation, user_id, conversation_id
    )
    raw_messages, latest_plan_data = await asyncio.gather(messages_future, plan_future)

    messages = [MessageItem(**item) for item in raw_messages]
    latest_plan = Plan(**latest_plan_data) if latest_plan_data else None

    return ConversationDetailResponse(
        conversation=Conversation(**conversation),
        messages=messages,
        latest_plan=latest_plan,
    )


@router.patch("/conversations/{conversation_id}", response_model=Conversation)
async def patch_conversation(
    conversation_id: str,
    request: ConversationUpdateRequest,
    session: dict = Depends(get_session_data),
):
    user_id = session["user_id"]
    conversation = get_conversation(user_id=user_id, conversation_id=conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    update_conversation_title(user_id=user_id, conversation_id=conversation_id, title=request.title.strip())
    updated = get_conversation(user_id=user_id, conversation_id=conversation_id)
    return Conversation(**updated)
