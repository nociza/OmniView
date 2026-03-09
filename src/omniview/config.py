from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
import os

from omniview.security import DEFAULT_MAX_RECORDS, DEFAULT_MAX_REQUEST_BYTES, generate_secret


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
    admin_token: str
    agent_token: str
    max_request_bytes: int
    max_nodes: int
    max_clients: int


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
            "",
        ),
        frontend_dist=frontend_dist or (source_dist if source_dist.exists() else packaged_dist),
        admin_token=os.getenv("OMV_ADMIN_TOKEN", generate_secret()),
        agent_token=os.getenv("OMV_AGENT_TOKEN", generate_secret()),
        max_request_bytes=int(os.getenv("OMV_MAX_REQUEST_BYTES", str(DEFAULT_MAX_REQUEST_BYTES))),
        max_nodes=int(os.getenv("OMV_MAX_NODES", str(DEFAULT_MAX_RECORDS))),
        max_clients=int(os.getenv("OMV_MAX_CLIENTS", str(DEFAULT_MAX_RECORDS))),
    )
