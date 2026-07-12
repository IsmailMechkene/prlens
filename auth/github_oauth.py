import os

import httpx

GITHUB_CLIENT_ID = os.getenv("GITHUB_OAUTH_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_OAUTH_CLIENT_SECRET")


class OAuthError(Exception):
    """GitHub refused to exchange the OAuth code for an access token."""


def get_github_auth_url() -> str:
    return (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&scope=repo"
    )

async def exchange_code_for_token(code: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        data = response.json()

        # A reused, expired or otherwise rejected code still answers 200 — the
        # failure is in the body ({"error": "bad_verification_code", ...}) — so the
        # status code is not enough to tell success from failure here.
        token = data.get("access_token") if isinstance(data, dict) else None
        if not token:
            reason = "no access_token in response"
            if isinstance(data, dict):
                reason = data.get("error_description") or data.get("error") or reason
            raise OAuthError(reason)

        return token

async def get_github_user(token: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
        )
        return response.json()