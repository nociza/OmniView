from __future__ import annotations

from pathlib import Path
import os
import sys


APP_NAME = "omv"


def config_root() -> Path:
    override = os.getenv("OMV_CONFIG_DIR")
    if override:
        return Path(override).expanduser()

    if sys.platform == "win32":
        base = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / APP_NAME

    base = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / APP_NAME

def ensure_config_root() -> Path:
    root = config_root()
    root.mkdir(parents=True, exist_ok=True)
    return root


def hub_config_path() -> Path:
    return config_root() / "hub.toml"


def client_config_path() -> Path:
    return config_root() / "client.toml"


def host_config_path() -> Path:
    return config_root() / "host.toml"

def launch_agents_dir() -> Path:
    return Path.home() / "Library" / "LaunchAgents"


def systemd_user_dir() -> Path:
    return Path.home() / ".config" / "systemd" / "user"


def local_bin_dir() -> Path:
    return Path.home() / ".local" / "bin"


def first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None
