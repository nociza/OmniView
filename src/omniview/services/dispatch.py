from __future__ import annotations

from urllib.parse import quote, urlencode

from omniview.models import ProtocolKind, ProtocolLaunch, ProtocolSpec


_NATIVE_CLIENT_LABELS = {
    ProtocolKind.MOONLIGHT: "Moonlight",
    ProtocolKind.VNC: "Screen Sharing / VNC Viewer",
    ProtocolKind.SSH: "Terminal / SSH Client",
    ProtocolKind.GUACAMOLE: "Browser",
}


def build_launches(name: str, overlay_ip: str, protocols: list[ProtocolSpec]) -> list[ProtocolLaunch]:
    enabled = sorted((protocol for protocol in protocols if protocol.enabled), key=lambda item: item.priority)
    launches: list[ProtocolLaunch] = []

    for index, protocol in enumerate(enabled):
        launches.append(
            ProtocolLaunch(
                kind=protocol.kind,
                label=protocol.label,
                priority=protocol.priority,
                host=overlay_ip,
                port=protocol.port,
                username=protocol.username,
                path=protocol.path,
                app_name=protocol.app_name,
                launch_uri=_build_launch_uri(name=name, overlay_ip=overlay_ip, protocol=protocol),
                native_client=_NATIVE_CLIENT_LABELS[protocol.kind],
                requires_native_client=protocol.kind is not ProtocolKind.GUACAMOLE,
                note=protocol.note,
                is_primary=index == 0,
            )
        )

    return launches


def _build_launch_uri(*, name: str, overlay_ip: str, protocol: ProtocolSpec) -> str | None:
    if protocol.kind is ProtocolKind.MOONLIGHT:
        query = urlencode({
            "host": overlay_ip,
            "port": protocol.port or 47984,
            "name": name,
        })
        return f"omniview-moonlight://connect?{query}"

    if protocol.kind is ProtocolKind.VNC:
        port = protocol.port or 5900
        return f"vnc://{overlay_ip}:{port}"

    if protocol.kind is ProtocolKind.SSH:
        port = protocol.port or 22
        authority = f"{quote(protocol.username)}@{overlay_ip}" if protocol.username else overlay_ip
        return f"ssh://{authority}:{port}"

    if protocol.kind is ProtocolKind.GUACAMOLE:
        path = protocol.path or "/guacamole"
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return f"https://{overlay_ip}{path}"

    return None
