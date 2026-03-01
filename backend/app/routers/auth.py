"""Authentication routes for Google OAuth and sessions."""
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse

from app.auth.token_store import upsert_refresh_token
from app.config import settings
from app.models.schemas import UserInfo
from app.services.google_auth import oauth
from app.users.storage import upsert_user
from app.utils.session import create_session, load_session


router = APIRouter()


@router.get("/login")
async def login():
    """Initiate Google OAuth flow."""
    auth_url = oauth.get_authorization_url()
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def callback(code: Optional[str] = None, error: Optional[str] = None):
    """Handle OAuth callback, persist user/token, and set session cookie."""
    try:
        if error:
            raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
        if not code:
            raise HTTPException(status_code=400, detail="Missing authorization code")

        token_response = await oauth.exchange_code_for_tokens(code)
        access_token = token_response.get("access_token")
        refresh_token = token_response.get("refresh_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to get access token")

        user_info = await oauth.get_user_info(access_token)
        user_id = user_info["sub"]
        email = user_info["email"]

        upsert_user(user_id=user_id, email=email)
        if refresh_token:
            upsert_refresh_token(user_id=user_id, refresh_token=refresh_token)

        session_data = {
            "user_id": user_id,
            "email": email,
        }
        session_token = create_session(session_data)

        response = RedirectResponse(url=f"{settings.FRONTEND_BASE_URL}/app", status_code=302)
        response.set_cookie(
            key="session_id",
            value=session_token,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite="lax",
            max_age=60 * 60 * 24 * 7,
            path="/",
        )
        return response

    except HTTPException:
        raise
    except Exception:
        return RedirectResponse(url=f"{settings.FRONTEND_BASE_URL}/?error=auth_failed")


@router.get("/me")
async def get_current_user(session_id: Optional[str] = Cookie(None)) -> UserInfo:
    """Return auth state for current session."""
    if not session_id:
        return UserInfo(authenticated=False)

    session_data = load_session(session_id)
    if not session_data:
        return UserInfo(authenticated=False)

    return UserInfo(
        authenticated=True,
        user_id=session_data.get("user_id"),
        email=session_data.get("email"),
    )


@router.post("/logout")
async def logout(response: Response):
    """Logout by clearing session cookie."""
    response.delete_cookie(key="session_id", path="/")
    return {"message": "Logged out successfully"}


async def get_session_data(session_id: Optional[str] = Cookie(None)) -> dict:
    """Dependency to require a valid authenticated session."""
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session_data = load_session(session_id)
    if not session_data:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    return session_data


@router.get("/ping")
async def ping_auth(session: dict = Depends(get_session_data)):
    """Diagnostic endpoint for auth debugging."""
    return {"ok": True, "user_id": session["user_id"]}
