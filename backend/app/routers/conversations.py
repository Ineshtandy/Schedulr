"""Conversation endpoints for chat list and thread loading."""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.conversations.storage import (
    create_conversation,
    delete_conversation_cascade,
    get_conversation,
    get_deployment_for_conversation,
    list_conversations,
    update_conversation_title,
)
from app.google_tasks.deployer import delete_plan_from_tasks
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

logger = logging.getLogger(__name__)

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


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, session: dict = Depends(get_session_data)):
    """Delete a conversation and all associated records (plans, deployments, messages).
    
    If the conversation has an active deployment, the Google Tasks tasklist will be deleted.
    """
    user_id = session["user_id"]

    # Verify conversation exists and belongs to user
    conversation = get_conversation(user_id=user_id, conversation_id=conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    try:
        # Clean up Google Tasks if deployment exists
        if conversation.get("is_deployed") and conversation.get("tasklist_id"):
            try:
                await delete_plan_from_tasks(user_id=user_id, tasklist_id=conversation["tasklist_id"])
            except Exception as exc:
                logger.warning(
                    "Failed to delete Google Tasks tasklist, continuing with database delete",
                    extra={
                        "user_id": user_id,
                        "conversation_id": conversation_id,
                        "tasklist_id": conversation.get("tasklist_id"),
                        "error": str(exc),
                    },
                )

        # Cascade delete conversation and all related records
        success = delete_conversation_cascade(user_id=user_id, conversation_id=conversation_id)
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found or already deleted")

        return {"message": "Conversation deleted successfully", "conversation_id": conversation_id}

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "Delete conversation failed",
            extra={
                "user_id": user_id,
                "conversation_id": conversation_id,
            },
        )
        raise HTTPException(status_code=500, detail="Failed to delete conversation") from exc
