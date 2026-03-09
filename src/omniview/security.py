from __future__ import annotations

from pathlib import Path
from secrets import token_urlsafe
from urllib.parse import urlsplit
import ipaddress
import os
import socket
import subprocess


ADMIN_COOKIE_NAME = "omv_session"
AGENT_TOKEN_HEADER = "X-OMV-Agent-Token"  # nosec B105
ADMIN_AUTH_SCHEME = "Bearer"
DEFAULT_MAX_REQUEST_BYTES = 2_000_000
DEFAULT_MAX_RECORDS = 250
_TAILSCALE_CGNAT = ipaddress.ip_network("100.64.0.0/10")


def generate_secret(length: int = 32) -> str:
    return token_urlsafe(length)


def hub_default_host() -> str:
    tailscale_ip = detect_tailscale_ip()
    if tailscale_ip:
        return tailscale_ip
    return "127.0.0.1"


def detect_tailscale_ip() -> str | None:
    tailscale = shutil_which("tailscale")
    if not tailscale:
        return None
    try:
        output = subprocess.check_output([tailscale, "ip", "-4"], text=True, stderr=subprocess.DEVNULL).strip().splitlines()
    except (OSError, subprocess.CalledProcessError):
        return None
    for line in output:
        candidate = line.strip()
        if candidate:
            return candidate
    return None


def hub_origin(base_url: str) -> str | None:
    parts = urlsplit(base_url)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return None
    return f"{parts.scheme}://{parts.netloc}"


def ensure_http_url(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ValueError(f"Unsupported URL '{url}'. Only http(s) URLs are allowed.")
    return url


def launcher_allow_origins(hub_url: str) -> list[str]:
    origin = hub_origin(hub_url)
    return [origin] if origin else []


def is_loopback_host(host: str) -> bool:
    normalized = host.strip().lower()
    if normalized in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def is_unspecified_host(host: str) -> bool:
    normalized = host.strip().lower()
    if normalized in {"", "0.0.0.0", "::", "*"}:  # nosec B104
        return True
    try:
        return ipaddress.ip_address(normalized).is_unspecified
    except ValueError:
        return False


def is_private_bind_host(host: str) -> bool:
    normalized = host.strip().lower()
    if normalized == "localhost":
        return True

    try:
        return _is_private_ip(ipaddress.ip_address(normalized))
    except ValueError:
        pass

    try:
        addresses = {
            item[4][0].split("%", 1)[0]
            for item in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        }
    except socket.gaierror:
        return False

    if not addresses:
        return False

    try:
        return all(_is_private_ip(ipaddress.ip_address(address)) for address in addresses)
    except ValueError:
        return False


def requires_tls_for_bind_host(host: str) -> bool:
    if is_unspecified_host(host):
        return True
    return not is_private_bind_host(host)


def secure_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "posix":
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        fd = os.open(path, flags, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        return
    path.write_text(content, encoding="utf-8")


def shutil_which(name: str) -> str | None:
    for directory in os.getenv("PATH", "").split(os.pathsep):
        candidate = Path(directory) / name
        if candidate.exists():
            return str(candidate)
    return None


def _is_private_ip(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        address.is_loopback
        or address.is_private
        or address.is_link_local
        or address in _TAILSCALE_CGNAT
    )
