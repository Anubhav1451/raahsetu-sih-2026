"""Supabase access-token validation and application role lookup."""

import os
from typing import Annotated, Literal

import httpx
import psycopg
from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel


class AuthUser(BaseModel):
    id: str
    email: str | None = None
    role: Literal["field_official", "reviewer", "admin"] = "field_official"
    region_code: str | None = None


def require_user(authorization: Annotated[str | None, Header()] = None) -> AuthUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, detail="Sign in as a field official")
    token = authorization.removeprefix("Bearer ").strip()
    # Explicitly local-only demo tokens. Never enable this in production.
    demo_enabled = os.getenv("ALLOW_DEMO_AUTH", "false").lower() == "true"
    production = os.getenv("APP_ENV", "development").lower() in {"production", "prod"}
    if demo_enabled and not production and token.startswith("demo:"):
        role_key = token.removeprefix("demo:").split(":", 1)[0].lower()
        role = "admin" if role_key == "admin" else "reviewer" if role_key == "reviewer" else "field_official"
        return AuthUser(
            id=f"demo-{role_key}",
            email=f"{role_key}@demo.local",
            role=role,
            # The demo reviewer is deliberately scoped to the seeded Meghalaya
            # candidates. Production reviewers still come from their provisioned
            # database profile and never inherit this demo scope.
            region_code="meghalaya" if role == "reviewer" else None,
        )
    base_url = os.getenv("SUPABASE_URL")
    api_key = os.getenv("SUPABASE_PUBLISHABLE_KEY")
    if not base_url or not api_key:
        raise HTTPException(503, detail="Supabase authentication is not configured")
    try:
        response = httpx.get(
            f"{base_url}/auth/v1/user",
            headers={"apikey": api_key, "Authorization": authorization},
            timeout=8,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(503, detail="Authentication service is unavailable") from exc
    if response.status_code != 200:
        raise HTTPException(401, detail="Session expired or invalid")
    identity = response.json()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return AuthUser(id=identity["id"], email=identity.get("email"), role="field_official", region_code=None)
    with psycopg.connect(database_url, sslmode=os.getenv("DATABASE_SSLMODE", "require"),
                         connect_timeout=int(os.getenv("DB_CONNECT_TIMEOUT_SECONDS", "5")),
                         options=f"-c statement_timeout={int(os.getenv('DB_STATEMENT_TIMEOUT_MS', '5000'))} -c idle_in_transaction_session_timeout=10000") as conn:
        profile = conn.execute(
            "select role,region_code from profiles where id=%s", (identity["id"],)
        ).fetchone()
    if not profile:
        raise HTTPException(403, detail="User profile is not provisioned")
    return AuthUser(id=identity["id"], email=identity.get("email"), role=profile[0], region_code=profile[1])


def require_reviewer(user: Annotated[AuthUser, Depends(require_user)]) -> AuthUser:
    if user.role not in {"reviewer", "admin"}:
        raise HTTPException(403, detail="Reviewer role required")
    return user


def require_admin(user: Annotated[AuthUser, Depends(require_user)]) -> AuthUser:
    if user.role != "admin":
        raise HTTPException(403, detail="Admin role required")
    return user
