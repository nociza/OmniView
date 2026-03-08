from __future__ import annotations

from base64 import b64encode
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from io import BytesIO
import json
import os
import time
from urllib import error, request

import psutil
from mss import mss
from PIL import Image

from omniview.models import AgentReport, NodeProfile, TelemetryMetrics, TelemetryPayload
from omniview.role_config import HostConfig


def package_version() -> str:
    try:
        return version("omv")
    except PackageNotFoundError:
        pass
    return "0.0.0"


class NetworkRateSampler:
    def __init__(self) -> None:
        self._last = psutil.net_io_counters()
        self._last_at = time.monotonic()

    def sample(self) -> tuple[float, float]:
        now = time.monotonic()
        current = psutil.net_io_counters()
        elapsed = max(now - self._last_at, 1e-6)
        rx_mbps = ((current.bytes_recv - self._last.bytes_recv) * 8) / elapsed / 1_000_000
        tx_mbps = ((current.bytes_sent - self._last.bytes_sent) * 8) / elapsed / 1_000_000
        self._last = current
        self._last_at = now
        return max(rx_mbps, 0.0), max(tx_mbps, 0.0)


class ThumbnailCapture:
    def __init__(self, interval_seconds: int, enabled: bool) -> None:
        self.interval_seconds = interval_seconds
        self.enabled = enabled
        self._cached_thumbnail: str | None = None
        self._captured_at = 0.0

    def current(self) -> str | None:
        if not self.enabled:
            return None

        now = time.monotonic()
        if self._cached_thumbnail and now - self._captured_at < self.interval_seconds:
            return self._cached_thumbnail

        try:
            with mss() as grabber:
                monitor = grabber.monitors[1]
                screenshot = grabber.grab(monitor)
                image = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                image.thumbnail((480, 270))
                output = BytesIO()
                image.save(output, format="PNG", optimize=True)
                encoded = b64encode(output.getvalue()).decode("ascii")
                self._cached_thumbnail = f"data:image/png;base64,{encoded}"
                self._captured_at = now
        except Exception:
            return self._cached_thumbnail

        return self._cached_thumbnail


class HostAgent:
    def __init__(self, config: HostConfig) -> None:
        self.config = config
        self.network = NetworkRateSampler()
        self.thumbnails = ThumbnailCapture(config.screenshot_interval_seconds, config.screenshots_enabled)

    def run_forever(self) -> None:
        while True:
            self.post_once()
            time.sleep(self.config.report_interval_seconds)

    def post_once(self, *, dry_run: bool = False) -> AgentReport:
        report = self.build_report()
        if not dry_run:
            self._post_report(report)
        return report

    def build_report(self) -> AgentReport:
        rx_mbps, tx_mbps = self.network.sample()
        memory = psutil.virtual_memory()
        metrics = TelemetryMetrics(
            cpu_percent=psutil.cpu_percent(interval=0.2),
            memory_percent=memory.percent,
            memory_used_gb=memory.used / (1024 ** 3),
            memory_total_gb=memory.total / (1024 ** 3),
            temperature_c=self._temperature_celsius(),
            gpu_percent=None,
            network_rx_mbps=rx_mbps,
            network_tx_mbps=tx_mbps,
        )
        telemetry = TelemetryPayload(
            reported_at=datetime.now(UTC),
            metrics=metrics,
            thumbnail_data_url=self.thumbnails.current(),
            render_state=None,
            active_session=self._active_session(),
        )
        return AgentReport(profile=self._profile(), telemetry=telemetry)

    def _profile(self) -> NodeProfile:
        return NodeProfile(
            node_id=self.config.node_id,
            name=self.config.name,
            hostname=self.config.hostname,
            overlay_ip=self.config.overlay_ip,
            platform=self.config.platform,
            description=self.config.description,
            location=self.config.location,
            tags=self.config.tags,
            headless=self.config.headless,
            agent_version=package_version(),
            protocols=self.config.protocols,
        )

    @staticmethod
    def _temperature_celsius() -> float | None:
        try:
            sensors = psutil.sensors_temperatures(fahrenheit=False)
        except (AttributeError, NotImplementedError):
            return None
        values = [entry.current for group in sensors.values() for entry in group if entry.current is not None]
        return max(values) if values else None

    @staticmethod
    def _active_session() -> str | None:
        for key in ("DISPLAY", "WAYLAND_DISPLAY", "SESSIONNAME"):
            value = os.environ.get(key)
            if value:
                return value
        return None

    def _post_report(self, report: AgentReport) -> None:
        url = f"{self.config.hub_url.rstrip('/')}/api/agent/report"
        payload = report.model_dump(mode="json", exclude_none=True)
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with request.urlopen(req, timeout=15) as response:
                response.read()
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Hub rejected telemetry with HTTP {exc.code}: {detail or exc.reason}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Unable to reach OmniView hub at {url}: {exc.reason}") from exc
