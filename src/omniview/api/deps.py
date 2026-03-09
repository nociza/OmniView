from __future__ import annotations

from fastapi import Header, HTTPException, Request, status

from omniview.config import Settings
from omniview.security import ADMIN_AUTH_SCHEME, ADMIN_COOKIE_NAME, AGENT_TOKEN_HEADER
from omniview.store import NodeRegistry


def get_registry(request: Request) -> NodeRegistry:
    return request.app.state.registry


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def require_admin(
    request: Request,
    authorization: str | None = Header(default=None),
) -> None:
    settings = get_settings(request)
    if request.cookies.get(ADMIN_COOKIE_NAME) == settings.admin_token:
        return
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme == ADMIN_AUTH_SCHEME and token == settings.admin_token:
            return
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Hub authentication required.")


def require_agent(
    request: Request,
    x_omv_agent_token: str | None = Header(default=None, alias=AGENT_TOKEN_HEADER),
) -> None:
    settings = get_settings(request)
    if x_omv_agent_token == settings.agent_token:
        return
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Agent token mismatch.")
