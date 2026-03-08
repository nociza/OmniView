from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import shlex
import shutil
import subprocess
import sys

from omniview.paths import launch_agents_dir, systemd_user_dir


@dataclass(frozen=True, slots=True)
class ServiceDefinition:
    role: str
    label: str
    description: str
    command: list[str]


class ServiceManagerUnsupported(RuntimeError):
    pass


def install_user_service(definition: ServiceDefinition) -> Path:
    if sys.platform == "darwin":
        return _install_launchd_service(definition)
    if sys.platform.startswith("linux"):
        return _install_systemd_service(definition)
    raise ServiceManagerUnsupported("User service installation is currently supported on macOS and Linux only.")


def uninstall_user_service(definition: ServiceDefinition) -> Path:
    if sys.platform == "darwin":
        return _uninstall_launchd_service(definition)
    if sys.platform.startswith("linux"):
        return _uninstall_systemd_service(definition)
    raise ServiceManagerUnsupported("User service uninstallation is currently supported on macOS and Linux only.")


def resolve_omv_executable() -> str:
    executable = shutil.which("omv")
    if executable:
        return executable
    return sys.argv[0]


def _install_launchd_service(definition: ServiceDefinition) -> Path:
    target = launch_agents_dir() / f"{definition.label}.plist"
    target.parent.mkdir(parents=True, exist_ok=True)
    program_arguments = "\n".join(f"      <string>{_xml_escape(part)}</string>" for part in definition.command)
    content = f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">
<plist version=\"1.0\">
  <dict>
    <key>Label</key>
    <string>{definition.label}</string>
    <key>ProgramArguments</key>
    <array>
{program_arguments}
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
  </dict>
</plist>
"""
    target.write_text(content, encoding="utf-8")
    subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}", str(target)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["launchctl", "bootstrap", f"gui/{os.getuid()}", str(target)], check=True)
    return target


def _uninstall_launchd_service(definition: ServiceDefinition) -> Path:
    target = launch_agents_dir() / f"{definition.label}.plist"
    subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}", str(target)], check=False)
    if target.exists():
        target.unlink()
    return target


def _install_systemd_service(definition: ServiceDefinition) -> Path:
    target = systemd_user_dir() / f"{definition.label}.service"
    target.parent.mkdir(parents=True, exist_ok=True)
    command = shlex.join(definition.command)
    content = f"""[Unit]
Description={definition.description}
After=network-online.target

[Service]
Type=simple
ExecStart={command}
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
"""
    target.write_text(content, encoding="utf-8")
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", "--now", target.stem], check=True)
    return target


def _uninstall_systemd_service(definition: ServiceDefinition) -> Path:
    target = systemd_user_dir() / f"{definition.label}.service"
    subprocess.run(["systemctl", "--user", "disable", "--now", target.stem], check=False)
    if target.exists():
        target.unlink()
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
    return target


def _xml_escape(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
