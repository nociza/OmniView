from __future__ import annotations

from pathlib import Path
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from omniview.api.routes.auth import router as auth_router
from omniview.api.routes.clients import router as clients_router
from omniview.api.routes.health import router as health_router
from omniview.api.routes.nodes import router as nodes_router
from omniview.config import Settings, get_settings
from omniview.services.demo_seed import build_demo_client_records, build_demo_records
from omniview.store import NodeRegistry


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    app = FastAPI(title=app_settings.api_title, version="0.3.0")
    app.state.settings = app_settings

    if app_settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(app_settings.cors_origins),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    registry = NodeRegistry(app_settings)
    if os.getenv("OMV_DEMO_DATA", "1").lower() not in {"0", "false", "no"}:
        registry.seed(build_demo_records())
        registry.seed_clients(build_demo_client_records())
    app.state.registry = registry

    @app.middleware("http")
    async def harden_responses(request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > app_settings.max_request_bytes:
                    return JSONResponse(status_code=413, content={"detail": "Request body too large."})
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length header."})

        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' http://127.0.0.1:* http://localhost:*; frame-ancestors 'none'; base-uri 'self'",
        )
        return response

    app.include_router(auth_router, prefix="/api")
    app.include_router(health_router, prefix="/api")
    app.include_router(clients_router, prefix="/api")
    app.include_router(nodes_router, prefix="/api")

    _mount_frontend(app, app_settings.frontend_dist)
    return app


def _mount_frontend(app: FastAPI, frontend_dist: Path) -> None:
    assets_dir = frontend_dist / "assets"
    index_file = frontend_dist / "index.html"

    if not index_file.exists():
        return

    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/", include_in_schema=False)
    async def serve_index() -> FileResponse:
        return FileResponse(index_file)

    @app.get("/{path:path}", include_in_schema=False)
    async def serve_spa(path: str):
        if path.startswith("api"):
            return JSONResponse(status_code=404, content={"detail": "Not found"})

        candidate = frontend_dist / path
        if candidate.exists() and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index_file)


app = create_app()
