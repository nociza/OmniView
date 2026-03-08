from __future__ import annotations

import argparse
from datetime import UTC, datetime

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from omniview.launcher.config import LauncherSettings, get_launcher_settings
from omniview.launcher.models import AUTH_HEADER, LaunchRequest, LaunchResponse, LauncherStatusResponse
from omniview.launcher.service import LauncherService, LauncherUnsupportedError


class LauncherHealthResponse(BaseModel):
    status: str = Field(default="ok")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


def create_app(
    settings: LauncherSettings | None = None,
    service: LauncherService | None = None,
) -> FastAPI:
    app_settings = settings or get_launcher_settings()
    app = FastAPI(title="OMV Native Client", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(app_settings.allow_origins) or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.settings = app_settings
    app.state.service = service or LauncherService(app_settings)

    @app.get("/health", response_model=LauncherHealthResponse)
    def health() -> LauncherHealthResponse:
        return LauncherHealthResponse()

    @app.get("/api/status", response_model=LauncherStatusResponse)
    def launcher_status(request: Request) -> LauncherStatusResponse:
        launcher: LauncherService = request.app.state.service
        return launcher.status()

    @app.post("/api/launch", response_model=LaunchResponse)
    def launch(
        payload: LaunchRequest,
        request: Request,
        _token: None = Depends(require_token),
    ) -> LaunchResponse:
        launcher: LauncherService = request.app.state.service
        try:
            return launcher.launch(payload)
        except LauncherUnsupportedError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except OSError as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    return app


def require_token(
    request: Request,
    x_omv_token: str | None = Header(default=None, alias=AUTH_HEADER),
) -> None:
    settings: LauncherSettings = request.app.state.settings
    if settings.token and x_omv_token != settings.token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Launcher token mismatch.")


app = create_app()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the OMV native-client launcher service.")
    parser.add_argument("--host", help="Bind host override")
    parser.add_argument("--port", type=int, help="Bind port override")
    args = parser.parse_args()

    settings = get_launcher_settings()
    uvicorn.run(
        create_app(settings=settings),
        host=args.host or settings.host,
        port=args.port or settings.port,
        log_level="info",
    )
