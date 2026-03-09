from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import os
import tomllib

from omniview.models import ProtocolKind
from omniview.paths import client_config_path
from omniview.security import launcher_allow_origins


def _read_config(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _csv_env(name: str, default: str) -> tuple[str, ...]:
    raw = os.getenv(name, default)
    values = tuple(item.strip() for item in raw.split(",") if item.strip())
    return values or tuple()


@dataclass(frozen=True, slots=True)
class LauncherSettings:
    hub_url: str
    hub_token: str | None
    host: str
    port: int
    client_id: str | None
    client_name: str | None
    token: str | None
    telemetry_enabled: bool
    telemetry_interval_seconds: int
    log_retention: int
    allow_origins: tuple[str, ...]
    config_path: Path
    moonlight_binary: str | None
    moonlight_app_name: str
    ssh_terminal: str
    command_templates: dict[ProtocolKind, str]

@lru_cache(maxsize=1)
def get_launcher_settings() -> LauncherSettings:
    config_path = Path(os.getenv("OMV_LAUNCHER_CONFIG", str(client_config_path()))).expanduser()
    raw = _read_config(config_path)
    command_templates = raw.get("commands", {}) if isinstance(raw.get("commands", {}), dict) else {}
    hub_url = str(raw.get("hub_url", "http://127.0.0.1:8000"))
    raw_allow_origins = raw.get("allow_origins")
    default_allow_origins = launcher_allow_origins(hub_url)

    parsed_templates: dict[ProtocolKind, str] = {}
    for kind in ProtocolKind:
        value = command_templates.get(kind.value)
        if isinstance(value, str) and value.strip():
            parsed_templates[kind] = value.strip()

    return LauncherSettings(
        hub_url=hub_url,
        hub_token=str(raw.get("hub_token", "")).strip() or None,
        host=os.getenv("OMV_LAUNCHER_HOST", str(raw.get("host", "127.0.0.1"))),
        port=int(os.getenv("OMV_LAUNCHER_PORT", str(raw.get("port", 32145)))),
        client_id=str(raw.get("client_id", "")).strip() or None,
        client_name=str(raw.get("name", "")).strip() or None,
        token=os.getenv("OMV_LAUNCHER_TOKEN", str(raw.get("token", "")).strip()) or None,
        telemetry_enabled=str(raw.get("telemetry_enabled", True)).lower() not in {"0", "false", "no"},
        telemetry_interval_seconds=int(raw.get("telemetry_interval_seconds", 30)),
        log_retention=int(raw.get("log_retention", 50)),
        allow_origins=_csv_env(
            "OMV_LAUNCHER_ALLOW_ORIGINS",
            ",".join(raw_allow_origins if isinstance(raw_allow_origins, list) else default_allow_origins),
        ),
        config_path=config_path,
        moonlight_binary=os.getenv("OMV_LAUNCHER_MOONLIGHT_BINARY", str(raw.get("moonlight_binary", "")).strip()) or None,
        moonlight_app_name=os.getenv("OMV_LAUNCHER_MOONLIGHT_APP", str(raw.get("moonlight_app_name", "Desktop"))),
        ssh_terminal=os.getenv("OMV_LAUNCHER_SSH_TERMINAL", str(raw.get("ssh_terminal", "auto"))).lower(),
        command_templates=parsed_templates,
    )
