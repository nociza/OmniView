from __future__ import annotations

from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from omniview.models import NodePlatform, NodeProfile, NodeRecord, ProtocolKind, ProtocolSpec, TelemetryMetrics, TelemetryPayload


def build_demo_records() -> list[NodeRecord]:
    now = datetime.now(UTC)

    atlas = _build_record(
        profile=NodeProfile(
            node_id="atlas-bot-lab",
            name="Atlas Bot Lab",
            hostname="atlas",
            overlay_ip="100.84.16.10",
            platform=NodePlatform.LINUX,
            description="Headless Linux automation node with a virtual display for Playwright and Sunshine streaming.",
            location="Rack 01 / Home Lab",
            tags=["automation", "headless", "sunshine"],
            headless=True,
            agent_version="agent-0.2.1",
            protocols=[
                ProtocolSpec(kind=ProtocolKind.MOONLIGHT, label="Moonlight", priority=1, port=47984, app_name="Desktop", note="Primary path for low-latency intervention."),
                ProtocolSpec(kind=ProtocolKind.SSH, label="SSH", priority=2, port=22, username="ops", note="Fallback for service repair and bot restarts."),
            ],
        ),
        telemetry=TelemetryPayload(
            reported_at=now - timedelta(seconds=18),
            metrics=TelemetryMetrics(
                cpu_percent=63.2,
                memory_percent=58.4,
                memory_used_gb=9.3,
                memory_total_gb=16.0,
                temperature_c=72.1,
                gpu_percent=41.0,
                network_rx_mbps=18.4,
                network_tx_mbps=6.2,
            ),
            thumbnail_data_url=_thumbnail(
                title="Atlas Bot Lab",
                subtitle="Playwright checkout flow on :99",
                accent="#ff6a3d",
                status="ACTIVE BOT",
            ),
            render_state="Playwright checkout flow",
            active_session=":99",
        ),
        last_seen_at=now - timedelta(seconds=12),
    )

    mac_mini = _build_record(
        profile=NodeProfile(
            node_id="mac-mini-studio",
            name="Mac Mini Studio",
            hostname="mac-mini.local",
            overlay_ip="100.92.24.7",
            platform=NodePlatform.MACOS,
            description="Headless macOS node registered with Screen Sharing as the primary access path and SSH as a repair lane.",
            location="Studio Shelf",
            tags=["macos", "vnc", "render"],
            headless=True,
            agent_version="agent-0.2.1",
            protocols=[
                ProtocolSpec(kind=ProtocolKind.VNC, label="Screen Sharing", priority=1, port=5900, note="Bypasses user-session lockouts via ARD service."),
                ProtocolSpec(kind=ProtocolKind.SSH, label="SSH", priority=2, port=22, username="nociza", note="Recovery path when WindowServer needs attention."),
            ],
        ),
        telemetry=TelemetryPayload(
            reported_at=now - timedelta(seconds=41),
            metrics=TelemetryMetrics(
                cpu_percent=24.8,
                memory_percent=47.2,
                memory_used_gb=7.5,
                memory_total_gb=16.0,
                temperature_c=48.7,
                gpu_percent=12.0,
                network_rx_mbps=4.5,
                network_tx_mbps=1.4,
            ),
            thumbnail_data_url=_thumbnail(
                title="Mac Mini Studio",
                subtitle="WindowServer healthy, session locked",
                accent="#0fb9b1",
                status="READY",
            ),
            render_state="Finder idle",
            active_session="console",
        ),
        last_seen_at=now - timedelta(seconds=36),
    )

    cinder = _build_record(
        profile=NodeProfile(
            node_id="cinder-render-box",
            name="Cinder Render Box",
            hostname="cinder",
            overlay_ip="100.71.2.44",
            platform=NodePlatform.LINUX,
            description="GPU-heavy Linux workstation used for long-running renders and emergency browser fallback via Guacamole.",
            location="Garage Rack",
            tags=["render", "gpu", "guacamole"],
            headless=False,
            agent_version="agent-0.1.9",
            protocols=[
                ProtocolSpec(kind=ProtocolKind.MOONLIGHT, label="Moonlight", priority=1, port=47984, app_name="Desktop"),
                ProtocolSpec(kind=ProtocolKind.GUACAMOLE, label="Browser Fallback", priority=3, path="/guacamole/#/client/cinder", note="Use only when native clients are unavailable."),
                ProtocolSpec(kind=ProtocolKind.SSH, label="SSH", priority=2, port=22, username="ops"),
            ],
        ),
        telemetry=TelemetryPayload(
            reported_at=now - timedelta(minutes=3, seconds=12),
            metrics=TelemetryMetrics(
                cpu_percent=81.5,
                memory_percent=74.6,
                memory_used_gb=23.9,
                memory_total_gb=32.0,
                temperature_c=84.2,
                gpu_percent=93.0,
                network_rx_mbps=2.4,
                network_tx_mbps=12.8,
            ),
            thumbnail_data_url=_thumbnail(
                title="Cinder Render Box",
                subtitle="Render queue checkpoint 87%",
                accent="#f6b73c",
                status="STALE SIGNAL",
            ),
            render_state="Blender render batch",
            active_session=":0",
        ),
        last_seen_at=now - timedelta(minutes=2, seconds=48),
    )

    relay = _build_record(
        profile=NodeProfile(
            node_id="pocket-relay",
            name="Pocket Relay",
            hostname="relaybook",
            overlay_ip="100.103.91.16",
            platform=NodePlatform.MACOS,
            description="Travel laptop that participates in the overlay network when powered on in the field.",
            location="Offsite",
            tags=["mobile", "travel"],
            headless=False,
            agent_version="agent-0.1.4",
            protocols=[
                ProtocolSpec(kind=ProtocolKind.VNC, label="Screen Sharing", priority=1, port=5900),
                ProtocolSpec(kind=ProtocolKind.SSH, label="SSH", priority=2, port=22, username="nociza"),
            ],
        ),
        telemetry=TelemetryPayload(
            reported_at=now - timedelta(minutes=18),
            metrics=TelemetryMetrics(
                cpu_percent=9.4,
                memory_percent=39.1,
                memory_used_gb=6.2,
                memory_total_gb=16.0,
                temperature_c=39.4,
                gpu_percent=0.0,
                network_rx_mbps=0.0,
                network_tx_mbps=0.0,
            ),
            thumbnail_data_url=_thumbnail(
                title="Pocket Relay",
                subtitle="Sleeping since last trip handoff",
                accent="#6a7cff",
                status="OFFLINE",
            ),
            render_state="Lid closed",
            active_session="console",
        ),
        last_seen_at=now - timedelta(minutes=16),
    )

    return [atlas, mac_mini, cinder, relay]


def _build_record(*, profile: NodeProfile, telemetry: TelemetryPayload, last_seen_at: datetime) -> NodeRecord:
    return NodeRecord(
        profile=profile,
        telemetry=telemetry,
        registered_at=last_seen_at,
        last_seen_at=last_seen_at,
    )


def _thumbnail(*, title: str, subtitle: str, accent: str, status: str) -> str:
    svg = f"""
    <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 640 360'>
      <defs>
        <linearGradient id='bg' x1='0' y1='0' x2='1' y2='1'>
          <stop offset='0%' stop-color='#111827' />
          <stop offset='100%' stop-color='#1f2937' />
        </linearGradient>
        <linearGradient id='pulse' x1='0' y1='0' x2='1' y2='0'>
          <stop offset='0%' stop-color='{accent}' stop-opacity='0.18' />
          <stop offset='100%' stop-color='{accent}' stop-opacity='0.75' />
        </linearGradient>
      </defs>
      <rect width='640' height='360' fill='url(#bg)' rx='32' />
      <circle cx='530' cy='85' r='110' fill='{accent}' fill-opacity='0.16' />
      <circle cx='118' cy='302' r='140' fill='{accent}' fill-opacity='0.12' />
      <rect x='36' y='38' width='188' height='34' rx='17' fill='url(#pulse)' />
      <text x='58' y='61' fill='#f9fafb' font-family='Space Grotesk, Arial, sans-serif' font-size='18' font-weight='700'>{status}</text>
      <text x='36' y='162' fill='#f9fafb' font-family='Space Grotesk, Arial, sans-serif' font-size='42' font-weight='700'>{title}</text>
      <text x='36' y='206' fill='#d1d5db' font-family='Space Grotesk, Arial, sans-serif' font-size='20'>{subtitle}</text>
      <path d='M36 258 C136 218 218 312 318 272 S500 228 604 278' fill='none' stroke='{accent}' stroke-width='10' stroke-linecap='round' />
      <rect x='36' y='288' width='188' height='14' rx='7' fill='#e5e7eb' fill-opacity='0.18' />
      <rect x='36' y='288' width='124' height='14' rx='7' fill='{accent}' />
    </svg>
    """.strip()
    return f"data:image/svg+xml;charset=UTF-8,{quote(svg)}"
