"""Gemini AI service for plan generation, clarification, and updates."""
import google.generativeai as genai
import json
import uuid
from datetime import datetime
from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import settings
from app.models.schemas import Plan, PlanGenerateRequest
from pydantic import ValidationError


# Configure Gemini API
genai.configure(api_key=settings.GEMINI_API_KEY)

# Initialize model with JSON output configuration
model = genai.GenerativeModel(
    model_name=settings.GEMINI_MODEL,
    generation_config={
        "temperature": 0.2,  # Lower for more deterministic output
        "response_mime_type": "application/json",  # Force JSON output
    }
)


def get_plan_generation_prompt() -> str:
    """Get the system prompt for plan generation."""
    return """You are an expert planning assistant. Create a detailed day-by-day plan as STRICT JSON ONLY.

Return JSON matching this exact schema:
{
  "goal": "string - the user's goal",
  "start_date": "YYYY-MM-DD",
  "num_days": number,
  "minutes_per_day": number,
  "days": [
    {
      "date": "YYYY-MM-DD",
      "tasks": [
        {
          "title": "Task title (max 200 chars)",
          "notes": "Detailed notes with subtasks as bullet points if needed",
          "duration_min": number (realistic, total should not exceed minutes_per_day),
          "priority": "low" | "med" | "high"
        }
      ]
    }
  ]
}

CRITICAL RULES:
1. Plan must have EXACTLY num_days consecutive days starting from start_date
2. Each day can have MAXIMUM 5 tasks (usually 2-4 is better)
3. Total duration_min per day should not exceed minutes_per_day
4. Include subtasks in the "notes" field as bullet points, NOT as separate tasks
5. Be realistic about task durations
6. Distribute work evenly across days
7. Consider progression and dependencies (earlier tasks should prepare for later ones)
8. dates must be sequential and match the num_days count

Return ONLY valid JSON. No markdown, no explanations, just the JSON object."""


def get_plan_update_prompt() -> str:
    """Get the system prompt for plan updates."""
    return """You are an expert planning assistant. Update an existing plan based on user feedback.

You will receive:
1. The current plan as JSON
2. User's update request

Return the UPDATED plan as STRICT JSON ONLY, matching the same schema as the original plan.

CRITICAL RULES:
1. Keep the same date range and num_days UNLESS user explicitly asks to change it
2. Maintain MAXIMUM 5 tasks per day
3. Total duration_min per day should not exceed minutes_per_day
4. If user asks to "make it lighter", reduce tasks or durations
5. If user asks for "specific focus", adjust task titles and notes accordingly
6. Preserve task structure and quality while incorporating user feedback
7. dates must remain sequential

Return ONLY valid JSON. No markdown, no explanations, just the JSON object."""


def get_clarification_prompt(goal: str) -> str:
        """Prompt for generating two concise clarification questions."""
        return f"""You are helping refine a planning goal.

User goal:
{goal}

Return STRICT JSON ONLY as:
{{
    "questions": ["question 1", "question 2"]
}}

Rules:
1. Ask exactly 2 questions.
2. Questions should improve planning quality.
3. Keep each question under 140 characters.
4. No markdown, no extra keys.
"""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def call_gemini_with_retry(prompt: str) -> str:
    """Call Gemini API with retry logic.
    
    Args:
        prompt: The prompt to send to Gemini
        
    Returns:
        JSON response string
        
    Raises:
        Exception: If all retries fail
    """
    response = model.generate_content(prompt)
    return response.text


def generate_clarification_questions(goal: str) -> List[str]:
    """Generate two clarifying questions for first-time conversation setup."""
    response_text = call_gemini_with_retry(get_clarification_prompt(goal))
    try:
        payload = json.loads(response_text)
        questions = payload.get("questions", [])
        if isinstance(questions, list):
            clean = [str(item).strip() for item in questions if str(item).strip()]
            if len(clean) >= 2:
                return clean[:2]
    except json.JSONDecodeError:
        pass

    return [
        "How many days should this plan cover?",
        "When would you like to start?",
    ]


def generate_plan(request: PlanGenerateRequest, user_id: str) -> Plan:
    """Generate a new plan using Gemini.
    
    Args:
        request: Plan generation request
        user_id: User identifier
        
    Returns:
        Generated and validated Plan object
        
    Raises:
        ValueError: If plan generation or validation fails
    """
    # Use today's date if no start_date provided
    if not request.start_date:
        request.start_date = datetime.now().date().isoformat()
    
    # Build user prompt
    user_prompt = f"""Create a {request.num_days}-day plan for this goal:

Goal: {request.goal}
Start Date: {request.start_date}
Available Time: {request.minutes_per_day} minutes per day
"""
    
    if request.preferences:
        user_prompt += f"\nAdditional Preferences: {request.preferences}"
    
    # Combine system and user prompts
    full_prompt = f"{get_plan_generation_prompt()}\n\n{user_prompt}"
    
    try:
        # Call Gemini
        response_text = call_gemini_with_retry(full_prompt)
        
        # Parse JSON
        plan_data = json.loads(response_text)
        
        # Add required fields
        plan_data['plan_id'] = str(uuid.uuid4())
        plan_data['created_at'] = datetime.utcnow().isoformat()
        
        # Validate with Pydantic
        plan = Plan(**plan_data)
        
        return plan
        
    except (json.JSONDecodeError, ValidationError) as e:
        # Attempt one repair
        print(f"Plan validation failed, attempting repair: {e}")
        
        repair_prompt = f"""{get_plan_generation_prompt()}

The previous attempt failed validation with error: {str(e)}

Original request:
{user_prompt}

Please generate a CORRECTED plan that passes validation. Ensure:
- Exactly {request.num_days} days in the days array
- Each day has max 5 tasks
- All dates are sequential starting from {request.start_date}
- All required fields are present

Return ONLY valid JSON."""
        
        try:
            response_text = call_gemini_with_retry(repair_prompt)
            plan_data = json.loads(response_text)
            plan_data['plan_id'] = str(uuid.uuid4())
            plan_data['created_at'] = datetime.utcnow().isoformat()
            plan = Plan(**plan_data)
            return plan
        except Exception as repair_error:
            raise ValueError(f"Failed to generate valid plan after repair attempt: {repair_error}")
    
    except Exception as e:
        raise ValueError(f"Plan generation failed: {e}")


def update_plan(current_plan: Plan, user_message: str, user_id: str) -> Plan:
    """Update an existing plan based on user feedback.
    
    Args:
        current_plan: Current plan to update
        user_message: User's update instructions
        user_id: User identifier
        
    Returns:
        Updated and validated Plan object
        
    Raises:
        ValueError: If plan update or validation fails
    """
    # Convert current plan to JSON
    current_plan_json = current_plan.model_dump_json(indent=2)
    
    # Build prompt
    full_prompt = f"""{get_plan_update_prompt()}

CURRENT PLAN:
{current_plan_json}

USER UPDATE REQUEST:
{user_message}

Return the updated plan as JSON."""
    
    try:
        # Call Gemini
        response_text = call_gemini_with_retry(full_prompt)
        
        # Parse JSON
        plan_data = json.loads(response_text)
        
        # Generate new plan_id for the updated version
        plan_data['plan_id'] = str(uuid.uuid4())
        plan_data['created_at'] = datetime.utcnow().isoformat()
        
        # Validate with Pydantic
        plan = Plan(**plan_data)
        
        return plan
        
    except (json.JSONDecodeError, ValidationError) as e:
        # Attempt one repair
        print(f"Plan update validation failed, attempting repair: {e}")
        
        repair_prompt = f"""{get_plan_update_prompt()}

The previous update attempt failed validation with error: {str(e)}

CURRENT PLAN:
{current_plan_json}

USER UPDATE REQUEST:
{user_message}

Please generate a CORRECTED updated plan that passes validation.

Return ONLY valid JSON."""
        
        try:
            response_text = call_gemini_with_retry(repair_prompt)
            plan_data = json.loads(response_text)
            plan_data['plan_id'] = str(uuid.uuid4())
            plan_data['created_at'] = datetime.utcnow().isoformat()
            plan = Plan(**plan_data)
            return plan
        except Exception as repair_error:
            raise ValueError(f"Failed to update plan after repair attempt: {repair_error}")
    
    except Exception as e:
        raise ValueError(f"Plan update failed: {e}")
