"""Plan API endpoints for generation, updating, and deployment."""
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.models.schemas import (
    PlanGenerateRequest,
    PlanUpdateRequest,
    PlanDeployRequest,
    PlanResponse,
    PlanDeployResponse,
    PlanHistoryItem,
    Plan
)
from app.routers.auth import get_session_data
from app.services.gemini import generate_plan, update_plan
from app.services.google_tasks import deploy_plan_to_tasks
from app.utils.storage import save_plan, get_plan, get_plan_history_metadata


router = APIRouter()


@router.post("/generate", response_model=PlanResponse)
async def generate_plan_endpoint(
    request: PlanGenerateRequest,
    session: dict = Depends(get_session_data)
):
    """Generate a new plan using AI.
    
    Requires authentication. Creates a day-by-day plan based on user's goal.
    """
    try:
        user_id = session['user_id']
        
        # Generate plan using Gemini
        plan = generate_plan(request, user_id)
        
        # Save plan to storage
        save_plan(user_id, plan.plan_id, plan.model_dump())
        
        return PlanResponse(
            plan_id=plan.plan_id,
            plan=plan
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Plan generation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate plan")


@router.post("/update", response_model=PlanResponse)
async def update_plan_endpoint(
    request: PlanUpdateRequest,
    session: dict = Depends(get_session_data)
):
    """Update an existing plan based on user feedback.
    
    Requires authentication. Creates a new version of the plan with requested changes.
    """
    try:
        user_id = session['user_id']
        
        # Load existing plan
        existing_plan_data = get_plan(request.plan_id)
        if not existing_plan_data:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        existing_plan = Plan(**existing_plan_data)
        
        # Update plan using Gemini
        updated_plan = update_plan(existing_plan, request.user_message, user_id)
        
        # Save updated plan to storage
        save_plan(user_id, updated_plan.plan_id, updated_plan.model_dump())
        
        return PlanResponse(
            plan_id=updated_plan.plan_id,
            plan=updated_plan
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Plan update error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update plan")


@router.post("/deploy", response_model=PlanDeployResponse)
async def deploy_plan_endpoint(
    request: PlanDeployRequest,
    session: dict = Depends(get_session_data)
):
    """Deploy a plan to Google Tasks.
    
    Requires authentication. Creates a new task list and populates it with all tasks.
    """
    try:
        # Load plan
        plan_data = get_plan(request.plan_id)
        if not plan_data:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        plan = Plan(**plan_data)
        
        # Get tokens from session
        access_token = session['access_token']
        refresh_token = session['refresh_token']
        
        # Deploy to Google Tasks
        tasklist_id, created_count = deploy_plan_to_tasks(
            plan, access_token, refresh_token
        )
        
        return PlanDeployResponse(
            tasklist_id=tasklist_id,
            created_count=created_count
        )
        
    except Exception as e:
        print(f"Plan deployment error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=List[PlanHistoryItem])
async def get_plan_history(
    session: dict = Depends(get_session_data)
):
    """Get plan history for the authenticated user.
    
    Returns lightweight metadata for all plans created by the user.
    """
    try:
        user_id = session['user_id']
        history = get_plan_history_metadata(user_id)
        return [PlanHistoryItem(**item) for item in history]
        
    except Exception as e:
        print(f"Get history error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve plan history")


@router.get("/{plan_id}", response_model=Plan)
async def get_plan_by_id(
    plan_id: str,
    session: dict = Depends(get_session_data)
):
    """Get a specific plan by ID.
    
    Requires authentication. Returns full plan details.
    """
    plan_data = get_plan(plan_id)
    if not plan_data:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    return Plan(**plan_data)
