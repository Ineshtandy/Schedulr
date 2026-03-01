"""Plan orchestration on top of Gemini generation and updates."""
from typing import List

from app.models.schemas import Plan, PlanGenerateRequest
from app.services.gemini import generate_clarification_questions, generate_plan, update_plan


def ask_questions(goal: str) -> List[str]:
    return generate_clarification_questions(goal)


def generate_plan_orchestrated(req: PlanGenerateRequest, user_id: str) -> Plan:
    return generate_plan(req, user_id)


def update_plan_orchestrated(existing_plan: Plan, user_message: str, user_id: str) -> Plan:
    return update_plan(existing_plan, user_message, user_id)
