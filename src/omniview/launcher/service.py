from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
from typing import Callable
from urllib.parse import urlsplit

from omniview.launcher.config import LauncherSettings
from omniview.launcher.models import LaunchRequest, LaunchResponse, LauncherStatusResponse, ProtocolCapability
from omniview.models import ProtocolKind


class LauncherUnsupportedError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    strategy: str
    command: list[str]
    detail: str


class CommandRunner:
    def spawn(self, command: list[str]) -> None:
        subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )


class LauncherService:
    def __init__(
        self,
        settings: LauncherSettings,
        *,
        system_name: str | None = None,
        which_resolver=shutil.which,
        runner: CommandRunner | None = None,
        on_info: Callable[[str], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        self.settings = settings
        self.system_name = (system_name or platform.system()).lower()
        self.which = which_resolver
        self.runner = runner or CommandRunner()
        self.on_info = on_info
        self.on_error = on_error

    def status(self) -> LauncherStatusResponse:
        return LauncherStatusResponse(
            viewer_platform=self.system_name,
            auth_required=bool(self.settings.token),
            config_path=str(self.settings.config_path),
            protocols=[self.capability(kind) for kind in ProtocolKind],
        )

    def capability(self, kind: ProtocolKind) -> ProtocolCapability:
        try:
            plan = self.plan(
                LaunchRequest(
                    node_name="Capability Probe",
                    overlay_ip="100.64.0.1",
                    protocol=kind,
                    host="100.64.0.1",
                    port=self._default_port(kind),
                    app_name=self.settings.moonlight_app_name,
                    launch_uri=self._default_uri(kind, host="100.64.0.1", port=self._default_port(kind), path=None, username="ops"),
                    dry_run=True,
                )
            )
            return ProtocolCapability(kind=kind, available=True, strategy=plan.strategy, detail=plan.detail)
        except LauncherUnsupportedError as exc:
            return ProtocolCapability(kind=kind, available=False, detail=str(exc))

    def launch(self, request: LaunchRequest) -> LaunchResponse:
        try:
            plan = self.plan(request)
            if not request.dry_run:
                self.runner.spawn(plan.command)
                self._record_info(f"launch {request.protocol.value} for {request.node_name} via {plan.strategy}")
            return LaunchResponse(
                launched=not request.dry_run,
                protocol=request.protocol,
                strategy=plan.strategy,
                detail=plan.detail,
                command=plan.command,
            )
        except LauncherUnsupportedError as exc:
            self._record_error(f"launch rejected for {request.node_name} ({request.protocol.value}): {exc}")
            raise
        except OSError as exc:
            self._record_error(f"launch failed for {request.node_name} ({request.protocol.value}): {exc}")
            raise

    def plan(self, request: LaunchRequest) -> ExecutionPlan:
        template_plan = self._plan_from_template(request)
        if template_plan is not None:
            return template_plan

        if request.protocol is ProtocolKind.MOONLIGHT:
            return self._moonlight_plan(request)
        if request.protocol is ProtocolKind.VNC:
            return self._open_url_plan(
                self._default_uri(request.protocol, host=self._host(request), port=request.port, path=request.path, username=request.username),
                strategy="url-opener",
                detail="Opening the native VNC handler for the selected node.",
                allowed_schemes={"vnc"},
            )
        if request.protocol is ProtocolKind.SSH:
            return self._ssh_plan(request)
        if request.protocol is ProtocolKind.GUACAMOLE:
            return self._open_url_plan(
                self._default_uri(request.protocol, host=self._host(request), port=request.port, path=request.path, username=request.username),
                strategy="browser-opener",
                detail="Opening the browser fallback for the selected node.",
                allowed_schemes={"https"},
            )
        raise LauncherUnsupportedError(f"Unsupported protocol '{request.protocol.value}'.")

    def _plan_from_template(self, request: LaunchRequest) -> ExecutionPlan | None:
        template = self.settings.command_templates.get(request.protocol)
        if not template:
            return None

        formatted = template.format(
            protocol=self._template_value(request.protocol.value),
            node_id=self._template_value(request.node_id or ""),
            node_name=self._template_value(request.node_name),
            host=self._template_value(self._host(request)),
            overlay_ip=self._template_value(request.overlay_ip),
            port=self._template_value(str(request.port or self._default_port(request.protocol) or "")),
            username=self._template_value(request.username or ""),
            path=self._template_value(request.path or ""),
            app_name=self._template_value(request.app_name or self.settings.moonlight_app_name),
            launch_uri=self._template_value(request.launch_uri or ""),
            target=self._template_value(self._ssh_target(request)),
        )
        return ExecutionPlan(
            strategy="template",
            command=shlex.split(formatted, posix=self.system_name != "windows"),
            detail=f"Launching via configured {request.protocol.value} template.",
        )

    def _moonlight_plan(self, request: LaunchRequest) -> ExecutionPlan:
        if request.port not in (None, 47984):
            raise LauncherUnsupportedError("Custom Moonlight ports require a configured command template.")

        binary = self._moonlight_binary()
        if binary is None:
            raise LauncherUnsupportedError(
                "Moonlight was not detected locally. Install Moonlight or set a moonlight command template in ~/.config/omv/client.toml."
            )

        app_name = request.app_name or self.settings.moonlight_app_name
        return ExecutionPlan(
            strategy="moonlight-cli",
            command=[binary, "stream", self._host(request), app_name],
            detail=f"Launching Moonlight directly into '{app_name}'.",
        )

    def _ssh_plan(self, request: LaunchRequest) -> ExecutionPlan:
        ssh_binary = self.which("ssh")
        if ssh_binary is None:
            raise LauncherUnsupportedError("OpenSSH client was not found on this machine.")

        ssh_command = [ssh_binary]
        if request.port and request.port != 22:
            ssh_command.extend(["-p", str(request.port)])
        ssh_command.append(self._ssh_target(request))

        if self.system_name == "darwin":
            if self.which("osascript") is None:
                raise LauncherUnsupportedError("osascript is required for macOS SSH launching.")
            command_text = shlex.join(ssh_command)
            script = self._terminal_applescript(command_text)
            return ExecutionPlan(
                strategy="terminal-applescript",
                command=["osascript", "-e", script],
                detail="Opening a new Terminal session with the requested SSH command.",
            )

        if self.system_name == "linux":
            terminal = self._linux_terminal_command(ssh_command)
            if terminal is None:
                raise LauncherUnsupportedError("No supported Linux terminal emulator was detected for SSH launching.")
            return ExecutionPlan(
                strategy="terminal-emulator",
                command=terminal,
                detail="Opening a terminal emulator with the requested SSH command.",
            )

        if self.system_name == "windows":
            if self.which("wt"):
                return ExecutionPlan(
                    strategy="windows-terminal",
                    command=["wt", *ssh_command],
                    detail="Opening Windows Terminal with the requested SSH command.",
                )
            if self.which("powershell"):
                return ExecutionPlan(
                    strategy="powershell",
                    command=["powershell", "-NoExit", "-Command", shlex.join(ssh_command)],
                    detail="Opening PowerShell with the requested SSH command.",
                )
            raise LauncherUnsupportedError("Windows Terminal or PowerShell is required for SSH launching on Windows.")

        raise LauncherUnsupportedError(f"SSH launching is not implemented for platform '{self.system_name}'.")

    def _open_url_plan(self, url: str | None, *, strategy: str, detail: str, allowed_schemes: set[str]) -> ExecutionPlan:
        if not url:
            raise LauncherUnsupportedError("No launch URL was available for this protocol.")
        if urlsplit(url).scheme not in allowed_schemes:
            raise LauncherUnsupportedError("Launcher rejected an unsafe URL scheme.")

        if self.system_name == "darwin":
            if self.which("open") is None:
                raise LauncherUnsupportedError("macOS 'open' command was not found.")
            return ExecutionPlan(strategy=strategy, command=["open", url], detail=detail)

        if self.system_name == "linux":
            opener = self.which("xdg-open") or self.which("gio")
            if opener is None:
                raise LauncherUnsupportedError("No URL opener was detected. Install xdg-open or gio.")
            command = [opener, url] if Path(opener).name != "gio" else [opener, "open", url]
            return ExecutionPlan(strategy=strategy, command=command, detail=detail)

        if self.system_name == "windows":
            return ExecutionPlan(strategy=strategy, command=["cmd", "/c", "start", "", url], detail=detail)

        raise LauncherUnsupportedError(f"URL launching is not implemented for platform '{self.system_name}'.")

    def _moonlight_binary(self) -> str | None:
        candidates: list[str] = []
        if self.settings.moonlight_binary:
            candidates.append(self.settings.moonlight_binary)
        for name in ("moonlight", "moonlight-qt"):
            resolved = self.which(name)
            if resolved:
                candidates.append(resolved)

        if self.system_name == "darwin":
            candidates.extend(
                [
                    "/Applications/Moonlight.app/Contents/MacOS/Moonlight",
                    str(Path.home() / "Applications" / "Moonlight.app" / "Contents" / "MacOS" / "Moonlight"),
                ]
            )

        for candidate in candidates:
            if not candidate:
                continue
            if Path(candidate).exists():
                return candidate
            resolved = self.which(candidate)
            if resolved and Path(resolved).exists():
                return resolved
        return None

    def _linux_terminal_command(self, ssh_command: list[str]) -> list[str] | None:
        terminal = self.which("x-terminal-emulator")
        if terminal:
            return [terminal, "-e", *ssh_command]

        gnome_terminal = self.which("gnome-terminal")
        if gnome_terminal:
            return [gnome_terminal, "--", *ssh_command]

        konsole = self.which("konsole")
        if konsole:
            return [konsole, "-e", *ssh_command]

        xterm = self.which("xterm")
        if xterm:
            return [xterm, "-e", *ssh_command]

        alacritty = self.which("alacritty")
        if alacritty:
            return [alacritty, "-e", *ssh_command]

        wezterm = self.which("wezterm")
        if wezterm:
            return [wezterm, "start", "--", *ssh_command]

        return None

    def _host(self, request: LaunchRequest) -> str:
        return request.host or request.overlay_ip

    def _template_value(self, value: str) -> str:
        if self.system_name == "windows":
            return subprocess.list2cmdline([value])
        return shlex.quote(value)

    def _record_info(self, message: str) -> None:
        if self.on_info is not None:
            self.on_info(message)

    def _record_error(self, message: str) -> None:
        if self.on_error is not None:
            self.on_error(message)

    def _ssh_target(self, request: LaunchRequest) -> str:
        host = self._host(request)
        return f"{request.username}@{host}" if request.username else host

    @staticmethod
    def _terminal_applescript(command_text: str) -> str:
        escaped = command_text.replace("\\", "\\\\").replace('"', '\\"')
        return f'tell application "Terminal"\nactivate\ndo script "{escaped}"\nend tell'

    @staticmethod
    def _default_port(kind: ProtocolKind) -> int | None:
        return {
            ProtocolKind.MOONLIGHT: 47984,
            ProtocolKind.VNC: 5900,
            ProtocolKind.SSH: 22,
            ProtocolKind.GUACAMOLE: 443,
        }[kind]

    @staticmethod
    def _default_uri(kind: ProtocolKind, *, host: str | None, port: int | None, path: str | None, username: str | None) -> str | None:
        if host is None:
            return None
        if kind is ProtocolKind.VNC:
            return f"vnc://{host}:{port or 5900}"
        if kind is ProtocolKind.SSH:
            target = f"{username}@{host}" if username else host
            return f"ssh://{target}:{port or 22}"
        if kind is ProtocolKind.GUACAMOLE:
            return f"https://{host}{path or '/guacamole'}"
        if kind is ProtocolKind.MOONLIGHT:
            return None
        return None
