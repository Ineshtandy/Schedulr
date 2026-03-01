"""Pydantic models for API request/response schemas."""
from datetime import date, datetime, timedelta
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class Priority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "med"
    HIGH = "high"


class TaskItem(BaseModel):
    """Individual task within a day."""
    title: str = Field(..., max_length=200, description="Task title")
    notes: str = Field(default="", description="Detailed notes, including subtasks")
    duration_min: int = Field(..., gt=0, le=480, description="Duration in minutes")
    priority: Priority = Field(default=Priority.MEDIUM, description="Task priority")


class DayPlan(BaseModel):
    """Plan for a single day."""
    date: str = Field(..., description="Date in ISO format YYYY-MM-DD")
    tasks: List[TaskItem] = Field(default_factory=list, max_length=5, description="Up to 5 tasks")
    
    @model_validator(mode='after')
    def validate_task_count(self):
        """Ensure maximum 5 tasks per day."""
        if len(self.tasks) > 5:
            raise ValueError("Maximum 5 tasks allowed per day")
        return self


class Plan(BaseModel):
    """Complete plan structure."""
    plan_id: str = Field(..., description="Unique plan identifier")
    goal: str = Field(..., max_length=500, description="User's goal")
    start_date: str = Field(..., description="Start date in ISO format YYYY-MM-DD")
    num_days: int = Field(..., gt=0, le=90, description="Number of days in the plan")
    minutes_per_day: int = Field(..., gt=0, le=480, description="Minutes available per day")
    days: List[DayPlan] = Field(..., description="Day-by-day breakdown")
    created_at: Optional[datetime] = Field(default=None, description="Timestamp of creation")
    
    @model_validator(mode='after')
    def validate_days(self):
        """Ensure days list length and continuity are valid."""
        if len(self.days) != self.num_days:
            raise ValueError(
                f"Number of days ({len(self.days)}) must match num_days ({self.num_days})"
            )

        start = date.fromisoformat(self.start_date)
        for idx, day in enumerate(self.days):
            expected = (start + timedelta(days=idx)).isoformat()
            if day.date != expected:
                raise ValueError(
                    f"Day {idx + 1} date must be {expected}, got {day.date}"
                )

        return self


class PlanGenerateRequest(BaseModel):
    """Request to generate a new plan."""
    goal: str = Field(..., max_length=500, description="User's goal")
    num_days: int = Field(default=14, gt=0, le=90, description="Number of days")
    minutes_per_day: int = Field(default=90, gt=0, le=480, description="Minutes per day")
    start_date: Optional[str] = Field(default=None, description="Start date, defaults to today")
    preferences: Optional[str] = Field(default=None, max_length=500, description="Additional preferences")


class PlanUpdateRequest(BaseModel):
    """Request to update an existing plan."""
    plan_id: str = Field(..., description="Plan ID to update")
    user_message: str = Field(..., max_length=500, description="Update instructions")


class PlanDeployRequest(BaseModel):
    """Request to deploy plan to Google Tasks."""
    plan_id: str = Field(..., description="Plan ID to deploy")


class PlanResponse(BaseModel):
    """Response containing a plan."""
    plan_id: str
    plan: Plan


class PlanDeployResponse(BaseModel):
    """Response from deploying a plan."""
    tasklist_id: str
    tasklist_title: str
    conversation_id: str
    plan_id: str
    created_count: int
    updated_count: int = 0
    message: str = "Plan deployed successfully to Google Tasks"


class PlanHistoryItem(BaseModel):
    """Lightweight plan metadata for history."""
    plan_id: str
    goal: str
    created_at: Optional[datetime]
    num_days: int


class UserInfo(BaseModel):
    """User information from session."""
    authenticated: bool
    user_id: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None


class MessageItem(BaseModel):
    message_id: str
    role: str
    content: str
    created_at: Optional[datetime] = None


class Conversation(BaseModel):
    conversation_id: str
    user_id: str
    title: str
    state: str = "idle"
    latest_plan_id: Optional[str] = None
    pending_goal: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_deployed: bool = False
    deployment_id: Optional[str] = None
    tasklist_id: Optional[str] = None
    deployed_at: Optional[datetime] = None


class ConversationCreateResponse(BaseModel):
    conversation_id: str


class ConversationDetailResponse(BaseModel):
    conversation: Conversation
    messages: List[MessageItem]
    latest_plan: Optional[Plan] = None


class ConversationUpdateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)


class ClarificationResponse(BaseModel):
    state: str = "awaiting_info"
    questions: List[str]
    original_goal: str


class ConversationGenerateRequest(BaseModel):
    user_message: str = Field(..., min_length=1, max_length=2000)
    num_days: Optional[int] = Field(default=None, gt=0, le=90)
    minutes_per_day: Optional[int] = Field(default=None, gt=0, le=480)
    start_date: Optional[str] = None
    preferences: Optional[str] = None


class ConversationPlanResponse(BaseModel):
    state: str = "idle"
    plan_id: Optional[str] = None
    plan: Optional[Plan] = None
    questions: Optional[List[str]] = None


class DeploymentResult(BaseModel):
    deployment_id: str
    tasklist_id: str
    tasklist_title: str
    created_count: int
    updated_count: int
    name: Optional[str] = None
