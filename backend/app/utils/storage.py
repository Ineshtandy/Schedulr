"""In-memory storage for MVP (will be replaced with Snowflake later)."""
from typing import Dict, List, Optional, Any
from datetime import datetime


# In-memory storage dictionaries
users_store: Dict[str, Dict[str, Any]] = {}
plans_store: Dict[str, Dict[str, Any]] = {}
user_plans_store: Dict[str, List[str]] = {}  # user_id -> list of plan_ids


def save_user(user_id: str, user_data: Dict[str, Any]) -> None:
    """Save user information.
    
    Args:
        user_id: Unique user identifier
        user_data: User data dictionary
    """
    users_store[user_id] = user_data


def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve user information.
    
    Args:
        user_id: Unique user identifier
        
    Returns:
        User data dictionary or None if not found
    """
    return users_store.get(user_id)


def save_plan(user_id: str, plan_id: str, plan_data: Dict[str, Any]) -> None:
    """Save a plan for a user.
    
    Args:
        user_id: User identifier
        plan_id: Unique plan identifier
        plan_data: Complete plan data dictionary
    """
    # Add timestamp if not present
    if 'created_at' not in plan_data:
        plan_data['created_at'] = datetime.utcnow().isoformat()
    
    # Store plan
    plans_store[plan_id] = plan_data
    
    # Add to user's plan list
    if user_id not in user_plans_store:
        user_plans_store[user_id] = []
    
    if plan_id not in user_plans_store[user_id]:
        user_plans_store[user_id].append(plan_id)


def get_plan(plan_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a specific plan.
    
    Args:
        plan_id: Unique plan identifier
        
    Returns:
        Plan data dictionary or None if not found
    """
    return plans_store.get(plan_id)


def get_user_plans(user_id: str) -> List[Dict[str, Any]]:
    """Get all plans for a user.
    
    Args:
        user_id: User identifier
        
    Returns:
        List of plan dictionaries (sorted by created_at, most recent first)
    """
    plan_ids = user_plans_store.get(user_id, [])
    plans = [plans_store[pid] for pid in plan_ids if pid in plans_store]
    
    # Sort by created_at descending (most recent first)
    plans.sort(key=lambda p: p.get('created_at', ''), reverse=True)
    
    return plans


def get_plan_history_metadata(user_id: str) -> List[Dict[str, Any]]:
    """Get lightweight metadata for user's plan history.
    
    Args:
        user_id: User identifier
        
    Returns:
        List of plan metadata (plan_id, goal, created_at)
    """
    plans = get_user_plans(user_id)
    return [
        {
            'plan_id': p['plan_id'],
            'goal': p['goal'],
            'created_at': p.get('created_at'),
            'num_days': p['num_days']
        }
        for p in plans
    ]
