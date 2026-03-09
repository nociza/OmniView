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
from omniview.security import AGENT_TOKEN_HEADER, ensure_http_url
from omniview.telemetry import NetworkRateSampler, load_average, temperature_celsius, uptime_seconds


def package_version() -> str:
    try:
        return version("omv")
    except PackageNotFoundError:
        pass
    return "0.0.0"


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
        load_1, load_5, load_15 = load_average()
        metrics = TelemetryMetrics(
            cpu_percent=psutil.cpu_percent(interval=0.2),
            memory_percent=memory.percent,
            memory_used_gb=memory.used / (1024 ** 3),
            memory_total_gb=memory.total / (1024 ** 3),
            temperature_c=temperature_celsius(),
            gpu_percent=None,
            network_rx_mbps=rx_mbps,
            network_tx_mbps=tx_mbps,
            load_average_1=load_1,
            load_average_5=load_5,
            load_average_15=load_15,
            uptime_seconds=uptime_seconds(),
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
    def _active_session() -> str | None:
        for key in ("DISPLAY", "WAYLAND_DISPLAY", "SESSIONNAME"):
            value = os.environ.get(key)
            if value:
                return value
        return None

    def _post_report(self, report: AgentReport) -> None:
        url = ensure_http_url(f"{self.config.hub_url.rstrip('/')}/api/agent/report")
        payload = report.model_dump(mode="json", exclude_none=True)
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.config.hub_token:
            headers[AGENT_TOKEN_HEADER] = self.config.hub_token
        req = request.Request(url, data=body, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=15) as response:  # nosec B310
                response.read()
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Hub rejected telemetry with HTTP {exc.code}: {detail or exc.reason}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Unable to reach OMV hub at {url}: {exc.reason}") from exc
