"""Plan deployment endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException

from app.conversations.storage import get_conversation
from app.google_tasks.deployer import deploy_plan_to_tasks
from app.models.schemas import Plan, PlanDeployResponse
from app.plans.storage import get_plan_by_id
from app.routers.auth import get_session_data


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/plans/{plan_id}/deploy", response_model=PlanDeployResponse)
async def deploy_plan(plan_id: str, session: dict = Depends(get_session_data)):
    user_id = session["user_id"]

    plan_data = get_plan_by_id(user_id=user_id, plan_id=plan_id)
    if not plan_data:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan = Plan(**plan_data)
    conversation_id = plan_data.get("conversation_id")
    if not conversation_id:
        # Fallback if older snapshots don't contain conversation_id in payload.
        raise HTTPException(status_code=400, detail="Conversation mapping missing for this plan")

    conversation = get_conversation(user_id=user_id, conversation_id=conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    try:
        result = await deploy_plan_to_tasks(user_id=user_id, conversation_id=conversation_id, plan=plan)
        return PlanDeployResponse(
            tasklist_id=result["tasklist_id"],
            tasklist_title=result["tasklist_title"],
            conversation_id=conversation_id,
            plan_id=plan_id,
            created_count=result["created_count"],
            updated_count=result["updated_count"],
        )
    except Exception as exc:
        logger.exception(
            "Deploy failed",
            extra={
                "user_id": user_id,
                "plan_id": plan_id,
                "conversation_id": conversation_id,
            },
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc
