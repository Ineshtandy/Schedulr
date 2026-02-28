"""Session management using itsdangerous for signed cookies."""
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from typing import Optional, Dict, Any
from app.config import settings


# Session serializer with SECRET_KEY
serializer = URLSafeTimedSerializer(settings.SECRET_KEY)

# Session expiry: 7 days in seconds
SESSION_MAX_AGE = 60 * 60 * 24 * 7


def create_session(user_data: Dict[str, Any]) -> str:
    """Create an encrypted, signed session token.
    
    Args:
        user_data: Dictionary containing user session data
        
    Returns:
        Signed session token string
    """
    return serializer.dumps(user_data, salt='session')


def load_session(token: str, max_age: int = SESSION_MAX_AGE) -> Optional[Dict[str, Any]]:
    """Load and verify a session token.
    
    Args:
        token: Signed session token
        max_age: Maximum age of token in seconds (default 7 days)
        
    Returns:
        Dictionary containing user session data, or None if invalid/expired
    """
    try:
        return serializer.loads(token, salt='session', max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
