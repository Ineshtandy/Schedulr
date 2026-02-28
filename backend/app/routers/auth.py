"""Authentication routes for Google OAuth."""
from fastapi import APIRouter, Request, Response, Cookie, HTTPException, Depends
from fastapi.responses import RedirectResponse
from typing import Optional
from urllib.parse import urlencode
from app.services.google_auth import oauth
from app.utils.session import create_session, load_session
from app.utils.encryption import encrypt_token
from app.utils.storage import save_user
from app.models.schemas import UserInfo
from app.config import settings


router = APIRouter()


@router.get("/login")
async def login(request: Request):
    """Initiate Google OAuth flow.
    
    Redirects user to Google's consent screen.
    """
    auth_url = oauth.get_authorization_url()
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def callback(request: Request, code: Optional[str] = None, error: Optional[str] = None):
    """Handle OAuth callback from Google.
    
    Exchanges authorization code for tokens, creates session, and redirects to frontend.
    """
    try:
        # Check for errors
        if error:
            raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
        
        if not code:
            raise HTTPException(status_code=400, detail="Missing authorization code")
        
        # Exchange code for tokens
        token_response = await oauth.exchange_code_for_tokens(code)
        access_token = token_response.get('access_token')
        refresh_token = token_response.get('refresh_token', '')
        
        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to get access token")
        
        # Get user info
        user_info = await oauth.get_user_info(access_token)
        
        user_id = user_info['sub']
        email = user_info['email']
        name = user_info.get('name', email)
        
        # Encrypt tokens for storage
        encrypted_access = encrypt_token(access_token)
        encrypted_refresh = encrypt_token(refresh_token) if refresh_token else ''
        
        # Save user to storage
        save_user(user_id, {
            'user_id': user_id,
            'email': email,
            'name': name,
        })
        
        # Create session data
        session_data = {
            'user_id': user_id,
            'email': email,
            'name': name,
            'access_token': encrypted_access,
            'refresh_token': encrypted_refresh,
            'token_expiry': token_response.get('expires_in', 3600),
        }
        
        # Create signed session token
        session_token = create_session(session_data)
        
        # Create redirect response to frontend
        response = RedirectResponse(url=f"{settings.FRONTEND_BASE_URL}/app")
        
        # Set secure cookie with session token
        response.set_cookie(
            key="session_id",
            value=session_token,
            httponly=True,
            secure=settings.COOKIE_SECURE,  # False for localhost, True for production
            samesite="lax",
            max_age=60 * 60 * 24 * 7,  # 7 days
            path="/",
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"OAuth callback error: {e}")
        # Redirect to frontend with error
        return RedirectResponse(url=f"{settings.FRONTEND_BASE_URL}/?error=auth_failed")


@router.get("/me")
async def get_current_user(session_id: Optional[str] = Cookie(None)) -> UserInfo:
    """Get current authenticated user info.
    
    Returns user information if authenticated, otherwise error.
    """
    if not session_id:
        return UserInfo(authenticated=False)
    
    session_data = load_session(session_id)
    if not session_data:
        return UserInfo(authenticated=False)
    
    return UserInfo(
        authenticated=True,
        email=session_data.get('email'),
        name=session_data.get('name'),
    )


@router.post("/logout")
async def logout(response: Response):
    """Logout user by clearing session cookie."""
    response.delete_cookie(key="session_id", path="/")
    return {"message": "Logged out successfully"}


async def get_session_data(session_id: Optional[str] = Cookie(None)) -> dict:
    """Dependency to get and validate session data.
    
    Raises HTTPException if not authenticated.
    """
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    session_data = load_session(session_id)
    if not session_data:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    return session_data
