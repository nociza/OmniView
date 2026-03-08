from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import os
import tomllib

from omniview.models import ProtocolKind
from omniview.paths import client_config_path


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
    host: str
    port: int
    token: str | None
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

    parsed_templates: dict[ProtocolKind, str] = {}
    for kind in ProtocolKind:
        value = command_templates.get(kind.value)
        if isinstance(value, str) and value.strip():
            parsed_templates[kind] = value.strip()

    return LauncherSettings(
        host=os.getenv("OMV_LAUNCHER_HOST", str(raw.get("host", "127.0.0.1"))),
        port=int(os.getenv("OMV_LAUNCHER_PORT", str(raw.get("port", 32145)))),
        token=os.getenv("OMV_LAUNCHER_TOKEN", str(raw.get("token", "")).strip()) or None,
        allow_origins=_csv_env(
            "OMV_LAUNCHER_ALLOW_ORIGINS",
            ",".join(raw.get("allow_origins", ["*"])) if isinstance(raw.get("allow_origins"), list) else "*",
        ),
        config_path=config_path,
        moonlight_binary=os.getenv("OMV_LAUNCHER_MOONLIGHT_BINARY", str(raw.get("moonlight_binary", "")).strip()) or None,
        moonlight_app_name=os.getenv("OMV_LAUNCHER_MOONLIGHT_APP", str(raw.get("moonlight_app_name", "Desktop"))),
        ssh_terminal=os.getenv("OMV_LAUNCHER_SSH_TERMINAL", str(raw.get("ssh_terminal", "auto"))).lower(),
        command_templates=parsed_templates,
    )
