"""Low-level Google Tasks API client helpers."""
from __future__ import annotations

from typing import Dict

import httpx

from app.config import settings

TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
TASKLISTS_ENDPOINT = "https://tasks.googleapis.com/tasks/v1/users/@me/lists"


async def refresh_access_token(refresh_token: str) -> str:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            TOKEN_ENDPOINT,
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        response.raise_for_status()
        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise ValueError("Missing access token in refresh response")
        return token


async def create_tasklist(access_token: str, title: str) -> Dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            TASKLISTS_ENDPOINT,
            headers={"Authorization": f"Bearer {access_token}"},
            json={"title": title},
        )
        response.raise_for_status()
        return response.json()


async def create_task(
    access_token: str,
    tasklist_id: str,
    title: str,
    notes: str,
    due_rfc3339: str,
) -> Dict:
    endpoint = f"{TASKLISTS_ENDPOINT}/{tasklist_id}/tasks"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            endpoint,
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "title": title,
                "notes": notes,
                "due": due_rfc3339,
            },
        )
        response.raise_for_status()
        return response.json()
