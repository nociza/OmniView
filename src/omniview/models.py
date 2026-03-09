from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, computed_field, field_validator


SmallText = Annotated[str, Field(max_length=160)]
LogLine = Annotated[str, Field(max_length=400)]
TagText = Annotated[str, Field(max_length=32)]


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
    label: SmallText
    priority: int = 100
    port: int | None = Field(default=None, ge=1, le=65535)
    path: str | None = Field(default=None, max_length=160)
    username: str | None = Field(default=None, max_length=64)
    app_name: str | None = Field(default=None, max_length=80)
    note: str | None = Field(default=None, max_length=240)
    enabled: bool = True

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value.startswith(("http://", "https://")):
            raise ValueError("Absolute URLs are not allowed in protocol paths.")
        if value and not value.startswith("/"):
            return f"/{value}"
        return value


class TelemetryMetrics(BaseModel):
    cpu_percent: float = Field(ge=0, le=100)
    memory_percent: float = Field(ge=0, le=100)
    memory_used_gb: float | None = Field(default=None, ge=0)
    memory_total_gb: float | None = Field(default=None, ge=0)
    temperature_c: float | None = None
    gpu_percent: float | None = Field(default=None, ge=0, le=100)
    gpu_power_watts: float | None = Field(default=None, ge=0)
    network_rx_mbps: float | None = Field(default=None, ge=0)
    network_tx_mbps: float | None = Field(default=None, ge=0)
    load_average_1: float | None = Field(default=None, ge=0)
    load_average_5: float | None = Field(default=None, ge=0)
    load_average_15: float | None = Field(default=None, ge=0)
    network_latency_ms: float | None = Field(default=None, ge=0)
    power_watts: float | None = Field(default=None, ge=0)
    uptime_seconds: int | None = Field(default=None, ge=0)


class TelemetryPayload(BaseModel):
    reported_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metrics: TelemetryMetrics
    thumbnail_data_url: str | None = Field(default=None, max_length=1_000_000)
    render_state: str | None = Field(default=None, max_length=120)
    active_session: str | None = Field(default=None, max_length=120)
    collector_notes: list[SmallText] = Field(default_factory=list, max_length=16)
    recent_logs: list[LogLine] = Field(default_factory=list, max_length=32)
    recent_errors: list[LogLine] = Field(default_factory=list, max_length=16)

    @field_validator("thumbnail_data_url")
    @classmethod
    def validate_thumbnail(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.startswith("data:image/"):
            raise ValueError("Only data:image thumbnails are allowed.")
        return value


class NodeProfile(BaseModel):
    node_id: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=2, max_length=100)
    hostname: str = Field(min_length=1, max_length=255)
    overlay_ip: str = Field(min_length=3, max_length=255)
    platform: NodePlatform
    description: str | None = Field(default=None, max_length=240)
    location: str | None = Field(default=None, max_length=120)
    tags: list[TagText] = Field(default_factory=list, max_length=16)
    headless: bool = False
    agent_version: str | None = Field(default=None, max_length=40)
    protocols: list[ProtocolSpec] = Field(default_factory=list, max_length=8)

    @computed_field(return_type=ProtocolKind | None)
    @property
    def preferred_protocol(self) -> ProtocolKind | None:
        enabled = sorted((protocol for protocol in self.protocols if protocol.enabled), key=lambda item: item.priority)
        return enabled[0].kind if enabled else None


class ProtocolLaunch(BaseModel):
    kind: ProtocolKind
    label: SmallText
    priority: int
    host: str
    port: int | None = Field(default=None, ge=1, le=65535)
    username: str | None = Field(default=None, max_length=64)
    path: str | None = Field(default=None, max_length=160)
    app_name: str | None = Field(default=None, max_length=80)
    launch_uri: str | None = Field(default=None, max_length=512)
    native_client: SmallText
    requires_native_client: bool = True
    note: str | None = Field(default=None, max_length=240)
    is_primary: bool = False


class ProtocolCapability(BaseModel):
    kind: ProtocolKind
    available: bool
    strategy: str | None = Field(default=None, max_length=80)
    detail: str = Field(max_length=240)


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
    tags: list[TagText] = Field(default_factory=list)
    headless: bool = False
    agent_version: str | None = None
    status: NodeStatus
    status_message: str
    last_seen_at: datetime
    heartbeat_age_seconds: int = Field(ge=0)
    preferred_protocol: ProtocolKind | None = None
    protocols: list[ProtocolLaunch] = Field(default_factory=list)
    telemetry: TelemetryPayload | None = None


class ClientProfile(BaseModel):
    client_id: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=2, max_length=100)
    hostname: str = Field(min_length=1, max_length=255)
    overlay_ip: str = Field(min_length=3, max_length=255)
    platform: NodePlatform
    hub_url: str = Field(max_length=255)
    launcher_url: str = Field(max_length=255)
    app_version: str | None = Field(default=None, max_length=40)
    capabilities: list[ProtocolCapability] = Field(default_factory=list, max_length=8)


class ClientRecord(BaseModel):
    profile: ClientProfile
    telemetry: TelemetryPayload | None = None
    registered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_seen_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ClientView(BaseModel):
    client_id: str
    name: str
    hostname: str
    overlay_ip: str
    platform: NodePlatform
    hub_url: str
    launcher_url: str
    app_version: str | None = None
    status: NodeStatus
    status_message: str
    last_seen_at: datetime
    heartbeat_age_seconds: int = Field(ge=0)
    capabilities: list[ProtocolCapability] = Field(default_factory=list)
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
    clients: list[ClientView] = Field(default_factory=list)
    poll_interval_seconds: int = Field(ge=1)


class AgentReport(BaseModel):
    profile: NodeProfile
    telemetry: TelemetryPayload


class ClientReport(BaseModel):
    profile: ClientProfile
    telemetry: TelemetryPayload
