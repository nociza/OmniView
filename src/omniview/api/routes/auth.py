from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from omniview.api.deps import get_settings, require_admin
from omniview.config import Settings
from omniview.security import ADMIN_COOKIE_NAME


router = APIRouter(tags=["auth"])


class SessionLoginRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)


class SessionStatusResponse(BaseModel):
    authenticated: bool


@router.get("/session", response_model=SessionStatusResponse)
def session_status(request: Request, settings: Settings = Depends(get_settings)) -> SessionStatusResponse:
    return SessionStatusResponse(authenticated=request.cookies.get(ADMIN_COOKIE_NAME) == settings.admin_token)


@router.post("/session", response_model=SessionStatusResponse)
def create_session(
    payload: SessionLoginRequest,
    request: Request,
    response: Response,
    settings: Settings = Depends(get_settings),
) -> SessionStatusResponse:
    if payload.token != settings.admin_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Hub authentication required.")
    response.set_cookie(
        ADMIN_COOKIE_NAME,
        payload.token,
        httponly=True,
        samesite="strict",
        secure=request.url.scheme == "https",
        path="/",
    )
    return SessionStatusResponse(authenticated=True)


@router.delete("/session", response_model=SessionStatusResponse)
def destroy_session(
    response: Response,
    _admin: None = Depends(require_admin),
) -> SessionStatusResponse:
    response.delete_cookie(ADMIN_COOKIE_NAME, path="/")
    return SessionStatusResponse(authenticated=False)
