from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field, computed_field


class NodePlatform(str, Enum):
    LINUX = "linux"
    MACOS = "macos"
    WINDOWS = "windows"


class NodeStatus(str, Enum):
    ONLINE = "online"
    STALE = "stale"
    OFFLINE = "offline"


class ProtocolKind(str, Enum):
    MOONLIGHT = "moonlight"
    VNC = "vnc"
    SSH = "ssh"
    GUACAMOLE = "guacamole"


class ProtocolSpec(BaseModel):
    kind: ProtocolKind
    label: str
    priority: int = 100
    port: int | None = Field(default=None, ge=1, le=65535)
    path: str | None = None
    username: str | None = None
    app_name: str | None = None
    note: str | None = None
    enabled: bool = True


class TelemetryMetrics(BaseModel):
    cpu_percent: float = Field(ge=0, le=100)
    memory_percent: float = Field(ge=0, le=100)
    memory_used_gb: float | None = Field(default=None, ge=0)
    memory_total_gb: float | None = Field(default=None, ge=0)
    temperature_c: float | None = None
    gpu_percent: float | None = Field(default=None, ge=0, le=100)
    network_rx_mbps: float | None = Field(default=None, ge=0)
    network_tx_mbps: float | None = Field(default=None, ge=0)


class TelemetryPayload(BaseModel):
    reported_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metrics: TelemetryMetrics
    thumbnail_data_url: str | None = None
    render_state: str | None = None
    active_session: str | None = None


class NodeProfile(BaseModel):
    node_id: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=2, max_length=100)
    hostname: str = Field(min_length=1, max_length=255)
    overlay_ip: str = Field(min_length=3, max_length=255)
    platform: NodePlatform
    description: str | None = None
    location: str | None = None
    tags: list[str] = Field(default_factory=list)
    headless: bool = False
    agent_version: str | None = None
    protocols: list[ProtocolSpec] = Field(default_factory=list)

    @computed_field(return_type=ProtocolKind | None)
    @property
    def preferred_protocol(self) -> ProtocolKind | None:
        enabled = sorted((protocol for protocol in self.protocols if protocol.enabled), key=lambda item: item.priority)
        return enabled[0].kind if enabled else None


class ProtocolLaunch(BaseModel):
    kind: ProtocolKind
    label: str
    priority: int
    host: str
    port: int | None = Field(default=None, ge=1, le=65535)
    username: str | None = None
    path: str | None = None
    app_name: str | None = None
    launch_uri: str | None = None
    native_client: str
    requires_native_client: bool = True
    note: str | None = None
    is_primary: bool = False


class NodeRecord(BaseModel):
    profile: NodeProfile
    telemetry: TelemetryPayload | None = None
    registered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_seen_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class NodeView(BaseModel):
    node_id: str
    name: str
    hostname: str
    overlay_ip: str
    platform: NodePlatform
    description: str | None = None
    location: str | None = None
    tags: list[str] = Field(default_factory=list)
    headless: bool = False
    agent_version: str | None = None
    status: NodeStatus
    status_message: str
    last_seen_at: datetime
    heartbeat_age_seconds: int = Field(ge=0)
    preferred_protocol: ProtocolKind | None = None
    protocols: list[ProtocolLaunch] = Field(default_factory=list)
    telemetry: TelemetryPayload | None = None


class DashboardCounts(BaseModel):
    total: int = 0
    online: int = 0
    stale: int = 0
    offline: int = 0


class DashboardSummary(BaseModel):
    counts: DashboardCounts
    average_cpu_percent: float | None = None
    hottest_node_name: str | None = None
    last_updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DashboardResponse(BaseModel):
    summary: DashboardSummary
    nodes: list[NodeView]
    poll_interval_seconds: int = Field(ge=1)


class AgentReport(BaseModel):
    profile: NodeProfile
    telemetry: TelemetryPayload
