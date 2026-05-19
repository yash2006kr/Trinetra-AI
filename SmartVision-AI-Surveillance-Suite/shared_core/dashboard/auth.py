"""Simple API-key authentication with room for RBAC expansion."""

from __future__ import annotations

from fastapi import Header, HTTPException, status

from shared_core.utils.config import load_config


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    config = load_config()
    expected = config.get("dashboard", {}).get("api_key", "dev-token")
    if expected and x_api_key not in {expected, f"Bearer {expected}"}:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
