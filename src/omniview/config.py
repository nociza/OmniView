from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
import os

def _parse_csv_env(name: str, default: str) -> tuple[str, ...]:
    raw = os.getenv(name, default)
    values = tuple(item.strip() for item in raw.split(",") if item.strip())
    return values or tuple()


@dataclass(frozen=True, slots=True)
class Settings:
    api_title: str
    online_ttl_seconds: int
    stale_ttl_seconds: int
    poll_interval_seconds: int
    cors_origins: tuple[str, ...]
    frontend_dist: Path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    project_root = Path(__file__).resolve().parents[2]
    source_dist = project_root / "frontend" / "dist"
    packaged_dist = Path(str(files("omniview").joinpath("frontend_assets")))
    frontend_override = os.getenv("OMV_FRONTEND_DIST", "")
    frontend_dist = Path(frontend_override).expanduser() if frontend_override else None

    return Settings(
        api_title=os.getenv("OMV_API_TITLE", "OMV Control Plane"),
        online_ttl_seconds=int(os.getenv("OMV_ONLINE_TTL_SECONDS", "90")),
        stale_ttl_seconds=int(os.getenv("OMV_STALE_TTL_SECONDS", "300")),
        poll_interval_seconds=int(os.getenv("OMV_POLL_INTERVAL_SECONDS", "15")),
        cors_origins=_parse_csv_env(
            "OMV_CORS_ORIGINS",
            "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:8000,http://localhost:8000",
        ),
        frontend_dist=frontend_dist or (source_dist if source_dist.exists() else packaged_dist),
    )
