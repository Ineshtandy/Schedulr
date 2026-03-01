"""Plan deployment endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException

from app.conversations.storage import (
    clear_deployment_status,
    get_conversation,
    set_deployment_status,
)
from app.google_tasks.deployer import (
    delete_plan_from_tasks,
    deploy_plan_to_tasks,
    update_plan_in_tasks,
)
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
        
        # Update conversation with deployment status
        set_deployment_status(
            conversation_id=conversation_id,
            deployment_id=result["deployment_id"],
            tasklist_id=result["tasklist_id"],
        )
        
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


@router.delete("/plans/{plan_id}/deployment")
async def delete_deployment(plan_id: str, session: dict = Depends(get_session_data)):
    """Delete a deployed plan from Google Tasks."""
    user_id = session["user_id"]

    plan_data = get_plan_by_id(user_id=user_id, plan_id=plan_id)
    if not plan_data:
        raise HTTPException(status_code=404, detail="Plan not found")

    conversation_id = plan_data.get("conversation_id")
    if not conversation_id:
        raise HTTPException(status_code=400, detail="Conversation mapping missing for this plan")

    conversation = get_conversation(user_id=user_id, conversation_id=conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if not conversation.get("is_deployed") or not conversation.get("tasklist_id"):
        raise HTTPException(status_code=400, detail="No active deployment found for this conversation")

    try:
        await delete_plan_from_tasks(user_id=user_id, tasklist_id=conversation["tasklist_id"])
        
        # Clear deployment status from conversation
        clear_deployment_status(conversation_id=conversation_id)
        
        return {"message": "Plan deleted from Google Tasks successfully"}
    except Exception as exc:
        logger.exception(
            "Delete deployment failed",
            extra={
                "user_id": user_id,
                "plan_id": plan_id,
                "conversation_id": conversation_id,
            },
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/plans/{plan_id}/deployment/update", response_model=PlanDeployResponse)
async def update_deployment(plan_id: str, session: dict = Depends(get_session_data)):
    """Update a deployed plan by replacing it with the latest plan from the conversation."""
    user_id = session["user_id"]

    plan_data = get_plan_by_id(user_id=user_id, plan_id=plan_id)
    if not plan_data:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan = Plan(**plan_data)
    conversation_id = plan_data.get("conversation_id")
    if not conversation_id:
        raise HTTPException(status_code=400, detail="Conversation mapping missing for this plan")

    conversation = get_conversation(user_id=user_id, conversation_id=conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if not conversation.get("is_deployed") or not conversation.get("tasklist_id"):
        raise HTTPException(status_code=400, detail="No active deployment found for this conversation")

    # Get the latest plan from the conversation
    latest_plan_id = conversation.get("latest_plan_id")
    if not latest_plan_id:
        raise HTTPException(status_code=400, detail="No latest plan found in conversation")

    latest_plan_data = get_plan_by_id(user_id=user_id, plan_id=latest_plan_id)
    if not latest_plan_data:
        raise HTTPException(status_code=404, detail="Latest plan not found")

    latest_plan = Plan(**latest_plan_data)

    try:
        # Update deployment (deletes old, creates new)
        result = await update_plan_in_tasks(
            user_id=user_id,
            conversation_id=conversation_id,
            old_tasklist_id=conversation["tasklist_id"],
            new_plan=latest_plan,
        )
        
        # Update conversation with new deployment status
        set_deployment_status(
            conversation_id=conversation_id,
            deployment_id=result["deployment_id"],
            tasklist_id=result["tasklist_id"],
        )
        
        return PlanDeployResponse(
            tasklist_id=result["tasklist_id"],
            tasklist_title=result["tasklist_title"],
            conversation_id=conversation_id,
            plan_id=latest_plan_id,
            created_count=result["created_count"],
            updated_count=result["updated_count"],
        )
    except Exception as exc:
        logger.exception(
            "Update deployment failed",
            extra={
                "user_id": user_id,
                "plan_id": plan_id,
                "conversation_id": conversation_id,
            },
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc
