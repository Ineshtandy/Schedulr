"""Google Tasks API service for deploying plans."""
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from datetime import datetime
from typing import Tuple
from app.utils.encryption import decrypt_token
from app.models.schemas import Plan
from app.config import settings


def get_tasks_service(access_token: str, refresh_token: str):
    """Create Google Tasks API service with credentials.
    
    Args:
        access_token: Encrypted access token
        refresh_token: Encrypted refresh token
        
    Returns:
        Google Tasks API service object
    """
    # Decrypt tokens
    decrypted_access = decrypt_token(access_token)
    decrypted_refresh = decrypt_token(refresh_token) if refresh_token else None
    
    # Create credentials object
    creds = Credentials(
        token=decrypted_access,
        refresh_token=decrypted_refresh,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/tasks"]
    )
    
    # Build service
    service = build('tasks', 'v1', credentials=creds)
    return service


def deploy_plan_to_tasks(plan: Plan, access_token: str, refresh_token: str) -> Tuple[str, int]:
    """Deploy a plan to Google Tasks.
    
    Creates a new task list and populates it with all tasks from the plan.
    
    Args:
        plan: Plan object to deploy
        access_token: Encrypted access token
        refresh_token: Encrypted refresh token
        
    Returns:
        Tuple of (tasklist_id, created_task_count)
        
    Raises:
        HttpError: If Google Tasks API call fails
        Exception: For other errors
    """
    try:
        service = get_tasks_service(access_token, refresh_token)
        
        # Create a new task list with the plan goal as title
        tasklist_title = f"📅 {plan.goal[:90]}"  # Limit title length
        
        tasklist_body = {
            'title': tasklist_title
        }
        
        tasklist = service.tasklists().insert(body=tasklist_body).execute()
        tasklist_id = tasklist['id']
        
        # Create tasks for each day
        created_count = 0
        
        for day in plan.days:
            day_date = day.date  # Already in YYYY-MM-DD format
            
            for task in day.tasks:
                # Build task title with day context
                task_title = f"{task.title}"
                
                # Build detailed notes
                notes_lines = [
                    f"📆 Scheduled for: {day_date}",
                    f"⏱️ Duration: {task.duration_min} minutes",
                    f"🎯 Priority: {task.priority.value.upper()}",
                    f"📝 Plan ID: {plan.plan_id}",
                    ""
                ]
                
                if task.notes:
                    notes_lines.append("Details:")
                    notes_lines.append(task.notes)
                
                notes = "\n".join(notes_lines)
                
                # Convert date to RFC 3339 format for due date
                # Google Tasks expects YYYY-MM-DDTHH:MM:SS.000Z
                due_datetime = f"{day_date}T12:00:00.000Z"
                
                # Create task body
                task_body = {
                    'title': task_title,
                    'notes': notes,
                    'due': due_datetime
                }
                
                # Insert task
                service.tasks().insert(
                    tasklist=tasklist_id,
                    body=task_body
                ).execute()
                
                created_count += 1
        
        return tasklist_id, created_count
        
    except HttpError as e:
        if e.resp.status == 401:
            raise Exception("Authentication expired. Please sign in again.")
        elif e.resp.status == 429:
            raise Exception("Rate limit exceeded. Please try again later.")
        else:
            raise Exception(f"Google Tasks API error: {e}")
    
    except Exception as e:
        raise Exception(f"Failed to deploy plan: {e}")


def list_task_lists(access_token: str, refresh_token: str) -> list:
    """Get all task lists for the user.
    
    Args:
        access_token: Encrypted access token
        refresh_token: Encrypted refresh token
        
    Returns:
        List of task list objects
    """
    try:
        service = get_tasks_service(access_token, refresh_token)
        results = service.tasklists().list().execute()
        return results.get('items', [])
    except Exception as e:
        raise Exception(f"Failed to list task lists: {e}")
