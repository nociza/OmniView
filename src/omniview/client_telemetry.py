from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Event, Lock, Thread
import json
import os
import socket
from urllib import error, request

import psutil

from omniview.host_agent import package_version
from omniview.launcher.config import LauncherSettings
from omniview.launcher.service import LauncherService
from omniview.models import ClientProfile, ClientReport, NodePlatform, TelemetryMetrics, TelemetryPayload
from omniview.role_config import detect_overlay_ip, slugify
from omniview.security import AGENT_TOKEN_HEADER, ensure_http_url
from omniview.telemetry import NetworkRateSampler, load_average, network_latency_ms, nvidia_gpu_metrics, power_watts, temperature_celsius, uptime_seconds


class ClientRuntimeState:
    def __init__(self, max_entries: int = 50) -> None:
        self._logs: deque[str] = deque(maxlen=max_entries)
        self._errors: deque[str] = deque(maxlen=max_entries)
        self._lock = Lock()

    def info(self, message: str) -> None:
        self._append(self._logs, message)

    def error(self, message: str) -> None:
        entry = self._timestamped(message)
        with self._lock:
            self._errors.append(entry)
            self._logs.append(entry)

    def snapshot(self) -> tuple[list[str], list[str]]:
        with self._lock:
            return list(self._logs), list(self._errors)

    def _append(self, target: deque[str], message: str) -> None:
        entry = self._timestamped(message)
        with self._lock:
            target.append(entry)

    @staticmethod
    def _timestamped(message: str) -> str:
        return f"{datetime.now(UTC).isoformat()} {message}"


@dataclass(frozen=True, slots=True)
class ClientIdentity:
    client_id: str
    name: str
    hostname: str
    overlay_ip: str
    platform: NodePlatform


class ClientTelemetryCollector:
    def __init__(self, settings: LauncherSettings, runtime: ClientRuntimeState, launcher: LauncherService) -> None:
        self.settings = settings
        self.runtime = runtime
        self.launcher = launcher
        self.network = NetworkRateSampler()
        self.identity = self._identity()

    def build_report(self) -> ClientReport:
        logs, errors = self.runtime.snapshot()
        metrics, notes = self._metrics()
        telemetry = TelemetryPayload(
            reported_at=datetime.now(UTC),
            metrics=metrics,
            active_session=self._active_session(),
            render_state="Launcher idle",
            collector_notes=notes,
            recent_logs=logs[-20:],
            recent_errors=errors[-10:],
        )
        profile = ClientProfile(
            client_id=self.identity.client_id,
            name=self.identity.name,
            hostname=self.identity.hostname,
            overlay_ip=self.identity.overlay_ip,
            platform=self.identity.platform,
            hub_url=self.settings.hub_url,
            launcher_url=f"http://{self.settings.host}:{self.settings.port}",
            app_version=package_version(),
            capabilities=self.launcher.status().protocols,
        )
        return ClientReport(profile=profile, telemetry=telemetry)

    def post_once(self) -> ClientReport:
        report = self.build_report()
        url = ensure_http_url(f"{self.settings.hub_url.rstrip('/')}/api/clients/report")
        payload = report.model_dump(mode="json", exclude_none=True)
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.settings.hub_token:
            headers[AGENT_TOKEN_HEADER] = self.settings.hub_token
        req = request.Request(url, data=body, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=15) as response:  # nosec B310
                response.read()
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            self.runtime.error(f"hub rejected client telemetry with HTTP {exc.code}: {detail or exc.reason}")
            raise RuntimeError(f"Hub rejected client telemetry with HTTP {exc.code}: {detail or exc.reason}") from exc
        except error.URLError as exc:
            self.runtime.error(f"unable to reach hub at {url}: {exc.reason}")
            raise RuntimeError(f"Unable to reach hub at {url}: {exc.reason}") from exc
        return report

    def _metrics(self) -> tuple[TelemetryMetrics, list[str]]:
        rx_mbps, tx_mbps = self.network.sample()
        memory = psutil.virtual_memory()
        load_1, load_5, load_15 = load_average()
        gpu_percent, gpu_power = nvidia_gpu_metrics()
        watts = power_watts()
        latency = network_latency_ms(self.settings.hub_url)
        notes: list[str] = []

        if gpu_percent is None:
            notes.append("gpu telemetry unavailable on this platform without a supported vendor tool.")
        if watts is None:
            notes.append("machine power telemetry unavailable on this platform.")
        if latency is None:
            notes.append("hub latency probe failed.")

        return (
            TelemetryMetrics(
                cpu_percent=psutil.cpu_percent(interval=0.2),
                memory_percent=memory.percent,
                memory_used_gb=memory.used / (1024 ** 3),
                memory_total_gb=memory.total / (1024 ** 3),
                temperature_c=temperature_celsius(),
                gpu_percent=gpu_percent,
                gpu_power_watts=gpu_power,
                network_rx_mbps=rx_mbps,
                network_tx_mbps=tx_mbps,
                load_average_1=load_1,
                load_average_5=load_5,
                load_average_15=load_15,
                network_latency_ms=latency,
                power_watts=watts,
                uptime_seconds=uptime_seconds(),
            ),
            notes,
        )

    def _identity(self) -> ClientIdentity:
        hostname = socket.gethostname()
        platform = self._platform()
        client_id = self.settings.client_id or f"{slugify(hostname)}-client"
        name = self.settings.client_name or f"{hostname} Client"
        overlay_ip = detect_overlay_ip()
        return ClientIdentity(
            client_id=client_id,
            name=name,
            hostname=hostname,
            overlay_ip=overlay_ip,
            platform=platform,
        )

    def _platform(self) -> NodePlatform:
        if self.launcher.system_name == "darwin":
            return NodePlatform.MACOS
        if self.launcher.system_name == "windows":
            return NodePlatform.WINDOWS
        return NodePlatform.LINUX

    @staticmethod
    def _active_session() -> str | None:
        for key in ("DISPLAY", "WAYLAND_DISPLAY", "SESSIONNAME"):
            value = os.environ.get(key)
            if value:
                return value
        return None


class ClientTelemetryReporter:
    def __init__(self, collector: ClientTelemetryCollector, interval_seconds: int) -> None:
        self.collector = collector
        self.interval_seconds = interval_seconds
        self._stop = Event()
        self._thread = Thread(target=self._run, name="omv-client-telemetry", daemon=True)

    def start(self) -> None:
        if not self._thread.is_alive():
            self.collector.runtime.info("client telemetry reporter started")
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=2)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.collector.post_once()
            except RuntimeError:
                pass
            self._stop.wait(self.interval_seconds)
