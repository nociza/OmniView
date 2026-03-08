from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from omniview.api.routes.health import router as health_router
from omniview.api.routes.nodes import router as nodes_router
from omniview.config import Settings, get_settings
from omniview.services.demo_seed import build_demo_records
from omniview.store import NodeRegistry


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    app = FastAPI(title=app_settings.api_title, version="0.1.0")

    if app_settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(app_settings.cors_origins),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    registry = NodeRegistry(app_settings)
    registry.seed(build_demo_records())
    app.state.registry = registry

    app.include_router(health_router, prefix="/api")
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
