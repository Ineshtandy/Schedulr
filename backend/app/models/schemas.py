"""Pydantic models for API request/response schemas."""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from enum import Enum
from datetime import date, datetime


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
    
    @field_validator('tasks')
    @classmethod
    def validate_task_count(cls, v):
        """Ensure maximum 5 tasks per day."""
        if len(v) > 5:
            raise ValueError("Maximum 5 tasks allowed per day")
        return v


class Plan(BaseModel):
    """Complete plan structure."""
    plan_id: str = Field(..., description="Unique plan identifier")
    goal: str = Field(..., max_length=500, description="User's goal")
    start_date: str = Field(..., description="Start date in ISO format YYYY-MM-DD")
    num_days: int = Field(..., gt=0, le=90, description="Number of days in the plan")
    minutes_per_day: int = Field(..., gt=0, le=480, description="Minutes available per day")
    days: List[DayPlan] = Field(..., description="Day-by-day breakdown")
    created_at: Optional[str] = Field(default=None, description="Timestamp of creation")
    
    @field_validator('days')
    @classmethod
    def validate_days_count(cls, v, info):
        """Ensure days list matches num_days."""
        num_days = info.data.get('num_days')
        if num_days and len(v) != num_days:
            raise ValueError(f"Number of days ({len(v)}) must match num_days ({num_days})")
        return v


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
    created_count: int
    message: str = "Plan deployed successfully to Google Tasks"


class PlanHistoryItem(BaseModel):
    """Lightweight plan metadata for history."""
    plan_id: str
    goal: str
    created_at: Optional[str]
    num_days: int


class UserInfo(BaseModel):
    """User information from session."""
    authenticated: bool
    email: Optional[str] = None
    name: Optional[str] = None
