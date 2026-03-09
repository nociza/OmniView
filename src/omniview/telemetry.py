from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse
import os
import shutil
import socket
import subprocess
import time

import psutil


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


def temperature_celsius() -> float | None:
    try:
        sensors = psutil.sensors_temperatures(fahrenheit=False)
    except (AttributeError, NotImplementedError):
        return None
    values = [entry.current for group in sensors.values() for entry in group if entry.current is not None]
    return max(values) if values else None


def load_average() -> tuple[float | None, float | None, float | None]:
    if not hasattr(os, "getloadavg"):
        return None, None, None
    try:
        return tuple(float(item) for item in os.getloadavg())  # type: ignore[return-value]
    except OSError:
        return None, None, None


def uptime_seconds() -> int | None:
    try:
        return max(0, int(time.time() - psutil.boot_time()))
    except (OSError, AttributeError):
        return None


def network_latency_ms(url: str, timeout_seconds: float = 2.0) -> float | None:
    target = urlparse(url)
    if not target.hostname:
        return None

    port = target.port
    if port is None:
        port = 443 if target.scheme == "https" else 80

    started = time.perf_counter()
    try:
        with socket.create_connection((target.hostname, port), timeout=timeout_seconds):
            return round((time.perf_counter() - started) * 1000, 2)
    except OSError:
        return None


def nvidia_gpu_metrics() -> tuple[float | None, float | None]:
    binary = shutil.which("nvidia-smi")
    if binary is None:
        return None, None
    try:
        output = subprocess.check_output(
            [
                binary,
                "--query-gpu=utilization.gpu,power.draw",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=2,
        ).strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None, None

    if not output:
        return None, None

    first_row = output.splitlines()[0]
    parts = [item.strip() for item in first_row.split(",")]
    if len(parts) != 2:
        return None, None

    return _parse_float(parts[0]), _parse_float(parts[1])


def power_watts() -> float | None:
    linux = _linux_power_watts()
    if linux is not None:
        return linux
    return None


def _linux_power_watts() -> float | None:
    power_supply_dir = Path("/sys/class/power_supply")
    if not power_supply_dir.exists():
        return None

    for device in power_supply_dir.iterdir():
        power_now = device / "power_now"
        if power_now.exists():
            value = _read_numeric(power_now)
            if value is not None:
                return round(value / 1_000_000, 2)

        current_now = device / "current_now"
        voltage_now = device / "voltage_now"
        if current_now.exists() and voltage_now.exists():
            current = _read_numeric(current_now)
            voltage = _read_numeric(voltage_now)
            if current is not None and voltage is not None:
                return round((current * voltage) / 1_000_000_000_000, 2)

    return None


def _read_numeric(path: Path) -> float | None:
    try:
        return float(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def _parse_float(value: str) -> float | None:
    try:
        return float(value)
    except ValueError:
        return None
