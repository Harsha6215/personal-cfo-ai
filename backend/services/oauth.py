"""
Google OAuth service — Epic 6 Sprint 6.3

Handles Google OAuth2 token exchange:
1. Frontend gets auth code from Google Identity Services
2. Backend exchanges code for user info (email, name, picture)
3. Finds or creates local user, returns JWT tokens

Uses httpx for token exchange (authlib optional, but httpx is simpler
for the code-exchange flow since we don't need a full OAuth client).
"""

import structlog
import httpx
from pydantic import BaseModel

from backend.core.config import settings

logger = structlog.get_logger(__name__)

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


class GoogleUserInfo(BaseModel):
    """Parsed user info from Google."""
    email: str
    name: str | None = None
    picture: str | None = None
    email_verified: bool = False


async def exchange_google_code(code: str) -> GoogleUserInfo:
    """
    Exchange a Google authorization code for user information.

    Steps:
    1. POST to Google token endpoint with code → get access_token
    2. GET Google userinfo endpoint with access_token → get email, name, picture

    Raises:
        ValueError: If the code exchange fails or user info can't be fetched.
    """
    async with httpx.AsyncClient() as client:
        # Step 1: Exchange code for tokens
        token_response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )

        if token_response.status_code != 200:
            logger.error(
                "oauth.google.token_exchange_failed",
                status=token_response.status_code,
                body=token_response.text[:200],
            )
            raise ValueError("Failed to exchange Google auth code for tokens")

        token_data = token_response.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise ValueError("No access_token in Google token response")

        # Step 2: Get user info
        userinfo_response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if userinfo_response.status_code != 200:
            logger.error(
                "oauth.google.userinfo_failed",
                status=userinfo_response.status_code,
            )
            raise ValueError("Failed to fetch Google user info")

        info = userinfo_response.json()

        return GoogleUserInfo(
            email=info.get("email", ""),
            name=info.get("name"),
            picture=info.get("picture"),
            email_verified=info.get("email_verified", False),
        )


async def exchange_google_id_token(id_token: str) -> GoogleUserInfo:
    """
    Verify a Google ID token (from Google Identity Services one-tap/popup).

    This is the simpler flow: frontend gets an id_token directly and sends it.
    We verify it by calling Google's tokeninfo endpoint.
    """
    async with httpx.AsyncClient() as client:
        # Verify via Google's tokeninfo endpoint
        response = await client.get(
            f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"
        )

        if response.status_code != 200:
            raise ValueError("Invalid Google ID token")

        info = response.json()

        # Verify the token is for our app
        if info.get("aud") != settings.GOOGLE_CLIENT_ID:
            raise ValueError("Token audience mismatch")

        return GoogleUserInfo(
            email=info.get("email", ""),
            name=info.get("name"),
            picture=info.get("picture"),
            email_verified=info.get("email_verified") == "true",
        )
