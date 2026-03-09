from __future__ import annotations

from pathlib import Path
import getpass
import os
import re
import socket
import subprocess
import sys
import tomllib
from typing import Any

import tomli_w
from pydantic import BaseModel, Field

from omniview.models import NodePlatform, ProtocolKind, ProtocolSpec
from omniview.paths import client_config_path, ensure_config_root, host_config_path, hub_config_path
from omniview.security import (
    DEFAULT_MAX_RECORDS,
    DEFAULT_MAX_REQUEST_BYTES,
    generate_secret,
    hub_default_host,
    launcher_allow_origins,
    secure_write_text,
)

_DEFAULT_CORS: list[str] = []


class HubConfig(BaseModel):
    host: str = Field(default_factory=hub_default_host)
    port: int = 8000
    cors_origins: list[str] = Field(default_factory=lambda: list(_DEFAULT_CORS))
    admin_token: str = Field(default_factory=generate_secret)
    agent_token: str = Field(default_factory=generate_secret)
    tls_certfile: str | None = None
    tls_keyfile: str | None = None
    allow_insecure_public_http: bool = False
    max_request_bytes: int = Field(default=DEFAULT_MAX_REQUEST_BYTES, ge=65_536, le=10_000_000)
    max_nodes: int = Field(default=DEFAULT_MAX_RECORDS, ge=10, le=5_000)
    max_clients: int = Field(default=DEFAULT_MAX_RECORDS, ge=10, le=5_000)


class ClientConfig(BaseModel):
    hub_url: str = "http://127.0.0.1:8000"
    hub_token: str | None = None
    host: str = "127.0.0.1"
    port: int = 32145
    client_id: str | None = None
    name: str | None = None
    token: str | None = None
    telemetry_enabled: bool = True
    telemetry_interval_seconds: int = Field(default=30, ge=5)
    log_retention: int = Field(default=50, ge=10, le=500)
    allow_origins: list[str] = Field(default_factory=list)
    moonlight_binary: str | None = None
    moonlight_app_name: str = "Desktop"
    ssh_terminal: str = "auto"
    commands: dict[str, str] = Field(default_factory=dict)


class HostConfig(BaseModel):
    hub_url: str = "http://127.0.0.1:8000"
    hub_token: str | None = None
    report_interval_seconds: int = Field(default=30, ge=5)
    screenshot_interval_seconds: int = Field(default=60, ge=5)
    screenshots_enabled: bool = True
    node_id: str
    name: str
    hostname: str
    overlay_ip: str
    platform: NodePlatform
    description: str | None = None
    location: str | None = None
    tags: list[str] = Field(default_factory=list)
    headless: bool = False
    protocols: list[ProtocolSpec] = Field(default_factory=list)


def load_hub_config(path: Path | None = None) -> HubConfig:
    target = path or hub_config_path()
    if not target.exists():
        return HubConfig()
    return HubConfig.model_validate(_read_toml(target))


def save_hub_config(config: HubConfig, path: Path | None = None) -> Path:
    target = path or hub_config_path()
    _write_toml(target, config.model_dump(exclude_none=True))
    return target


def load_client_config(path: Path | None = None) -> ClientConfig:
    target = path or client_config_path()
    if not target.exists():
        return ClientConfig(allow_origins=launcher_allow_origins("http://127.0.0.1:8000"))
    config = ClientConfig.model_validate(_read_toml(target))
    if not config.allow_origins:
        return config.model_copy(update={"allow_origins": launcher_allow_origins(config.hub_url)})
    return config


def save_client_config(config: ClientConfig, path: Path | None = None) -> Path:
    target = path or client_config_path()
    _write_toml(target, config.model_dump(exclude_none=True))
    return target


def load_host_config(path: Path | None = None) -> HostConfig:
    target = path or host_config_path()
    if not target.exists():
        raise FileNotFoundError(f"Host config was not found at {target}")
    return HostConfig.model_validate(_read_toml(target))


def save_host_config(config: HostConfig, path: Path | None = None) -> Path:
    target = path or host_config_path()
    _write_toml(target, config.model_dump(exclude_none=True))
    return target


def default_host_config(
    *,
    hub_url: str,
    hub_token: str | None,
    node_id: str | None,
    name: str | None,
    overlay_ip: str | None,
    location: str | None,
    description: str | None,
    tags: list[str],
    headless: bool,
    protocols: list[ProtocolKind] | None,
) -> HostConfig:
    hostname = socket.gethostname()
    platform = detect_platform()
    final_name = name or hostname
    final_node_id = node_id or slugify(final_name)
    final_ip = overlay_ip or detect_overlay_ip()
    selected_protocols = protocols or default_protocol_kinds(platform)

    return HostConfig(
        hub_url=hub_url,
        hub_token=hub_token,
        node_id=final_node_id,
        name=final_name,
        hostname=hostname,
        overlay_ip=final_ip,
        platform=platform,
        description=description,
        location=location,
        tags=tags,
        headless=headless,
        protocols=build_protocol_specs(platform=platform, kinds=selected_protocols),
    )


def detect_platform() -> NodePlatform:
    if sys.platform == "darwin":
        return NodePlatform.MACOS
    if sys.platform.startswith("win"):
        return NodePlatform.WINDOWS
    return NodePlatform.LINUX


def default_protocol_kinds(platform: NodePlatform) -> list[ProtocolKind]:
    if platform is NodePlatform.MACOS:
        return [ProtocolKind.VNC, ProtocolKind.SSH]
    return [ProtocolKind.MOONLIGHT, ProtocolKind.SSH]


def build_protocol_specs(*, platform: NodePlatform, kinds: list[ProtocolKind]) -> list[ProtocolSpec]:
    specs: list[ProtocolSpec] = []
    for index, kind in enumerate(kinds, start=1):
        if kind is ProtocolKind.MOONLIGHT:
            specs.append(ProtocolSpec(kind=kind, label="Moonlight", priority=index, port=47984, app_name="Desktop"))
        elif kind is ProtocolKind.VNC:
            specs.append(ProtocolSpec(kind=kind, label="Screen Sharing", priority=index, port=5900))
        elif kind is ProtocolKind.SSH:
            specs.append(ProtocolSpec(kind=kind, label="SSH", priority=index, port=22, username=getpass.getuser()))
        elif kind is ProtocolKind.GUACAMOLE:
            specs.append(ProtocolSpec(kind=kind, label="Browser Fallback", priority=index, path="/guacamole"))
    return specs


def detect_overlay_ip() -> str:
    tailscale = shutil_which("tailscale")
    if tailscale:
        try:
            output = subprocess.check_output([tailscale, "ip", "-4"], text=True, stderr=subprocess.DEVNULL).strip().splitlines()
            for line in output:
                if line.strip():
                    return line.strip()
        except (OSError, subprocess.CalledProcessError):
            pass

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned or "host-node"


def _read_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _write_toml(path: Path, payload: dict[str, Any]) -> None:
    ensure_config_root()
    path.parent.mkdir(parents=True, exist_ok=True)
    secure_write_text(path, tomli_w.dumps(payload))


def shutil_which(name: str) -> str | None:
    for directory in os.getenv("PATH", "").split(os.pathsep):
        candidate = Path(directory) / name
        if candidate.exists():
            return str(candidate)
    return None
