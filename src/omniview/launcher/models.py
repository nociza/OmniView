from __future__ import annotations

from pydantic import BaseModel, Field

from omniview.models import NodePlatform, ProtocolCapability, ProtocolKind

AUTH_HEADER = "X-OMV-Token"


class LaunchRequest(BaseModel):
    node_id: str | None = None
    node_name: str
    overlay_ip: str
    platform: NodePlatform | None = None
    protocol: ProtocolKind
    label: str | None = None
    host: str | None = None
    port: int | None = Field(default=None, ge=1, le=65535)
    username: str | None = None
    path: str | None = None
    app_name: str | None = None
    launch_uri: str | None = None
    dry_run: bool = False


class LauncherStatusResponse(BaseModel):
    service: str = "omv-client"
    viewer_platform: str
    auth_required: bool
    config_path: str
    protocols: list[ProtocolCapability]


class LaunchResponse(BaseModel):
    ok: bool = True
    launched: bool
    protocol: ProtocolKind
    strategy: str
    detail: str
    command: list[str] = Field(default_factory=list)
