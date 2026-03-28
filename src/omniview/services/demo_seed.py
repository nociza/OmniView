from __future__ import annotations

from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from omniview.models import ClientProfile, ClientRecord, NodePlatform, NodeProfile, NodeRecord, ProtocolCapability, ProtocolKind, ProtocolSpec, TelemetryMetrics, TelemetryPayload


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
            agent_version="agent-0.3.2",
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
            agent_version="agent-0.3.2",
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


def build_demo_client_records() -> list[ClientRecord]:
    now = datetime.now(UTC)

    desk = ClientRecord(
        profile=ClientProfile(
            client_id="studio-desk-client",
            name="Studio Desk Client",
            hostname="studio-desk",
            overlay_ip="100.64.8.21",
            platform=NodePlatform.MACOS,
            hub_url="http://100.64.8.21:8000",
            launcher_url="http://127.0.0.1:32145",
            app_version="omv-0.3.2",
            capabilities=[
                ProtocolCapability(kind=ProtocolKind.MOONLIGHT, available=True, strategy="moonlight-cli", detail="Moonlight installed locally."),
                ProtocolCapability(kind=ProtocolKind.VNC, available=True, strategy="url-opener", detail="Screen Sharing URI handler available."),
                ProtocolCapability(kind=ProtocolKind.SSH, available=True, strategy="terminal-applescript", detail="Terminal SSH handoff available."),
                ProtocolCapability(kind=ProtocolKind.GUACAMOLE, available=True, strategy="browser-opener", detail="Browser fallback available."),
            ],
        ),
        telemetry=TelemetryPayload(
            reported_at=now - timedelta(seconds=11),
            metrics=TelemetryMetrics(
                cpu_percent=18.5,
                memory_percent=46.1,
                memory_used_gb=7.4,
                memory_total_gb=16.0,
                temperature_c=43.7,
                gpu_percent=8.0,
                gpu_power_watts=None,
                network_rx_mbps=6.1,
                network_tx_mbps=1.8,
                load_average_1=2.1,
                load_average_5=1.7,
                load_average_15=1.5,
                network_latency_ms=22.4,
                power_watts=None,
                uptime_seconds=25214,
            ),
            active_session="console",
            render_state="Launcher idle",
            collector_notes=[
                "gpu telemetry unavailable on this platform without a supported vendor tool.",
                "machine power telemetry unavailable on this platform.",
            ],
            recent_logs=[
                f"{(now - timedelta(seconds=30)).isoformat()} launch moonlight for Atlas Bot Lab via moonlight-cli",
                f"{(now - timedelta(seconds=90)).isoformat()} client telemetry reporter started",
            ],
            recent_errors=[],
        ),
        registered_at=now - timedelta(minutes=40),
        last_seen_at=now - timedelta(seconds=9),
    )

    field = ClientRecord(
        profile=ClientProfile(
            client_id="field-laptop-client",
            name="Field Laptop Client",
            hostname="fieldbook",
            overlay_ip="100.103.91.16",
            platform=NodePlatform.WINDOWS,
            hub_url="http://100.64.8.21:8000",
            launcher_url="http://127.0.0.1:32145",
            app_version="omv-0.3.2",
            capabilities=[
                ProtocolCapability(kind=ProtocolKind.MOONLIGHT, available=False, detail="Moonlight was not detected locally."),
                ProtocolCapability(kind=ProtocolKind.VNC, available=True, strategy="url-opener", detail="VNC URI handler available."),
                ProtocolCapability(kind=ProtocolKind.SSH, available=True, strategy="windows-terminal", detail="Windows Terminal SSH handoff available."),
                ProtocolCapability(kind=ProtocolKind.GUACAMOLE, available=True, strategy="browser-opener", detail="Browser fallback available."),
            ],
        ),
        telemetry=TelemetryPayload(
            reported_at=now - timedelta(minutes=5),
            metrics=TelemetryMetrics(
                cpu_percent=33.2,
                memory_percent=58.8,
                memory_used_gb=9.4,
                memory_total_gb=16.0,
                temperature_c=None,
                gpu_percent=None,
                gpu_power_watts=None,
                network_rx_mbps=1.4,
                network_tx_mbps=0.4,
                load_average_1=None,
                load_average_5=None,
                load_average_15=None,
                network_latency_ms=84.6,
                power_watts=None,
                uptime_seconds=6180,
            ),
            active_session="Console",
            render_state="Launcher idle",
            collector_notes=[
                "gpu telemetry unavailable on this platform without a supported vendor tool.",
                "machine power telemetry unavailable on this platform.",
            ],
            recent_logs=[
                f"{(now - timedelta(minutes=8)).isoformat()} launch ssh for Mac Mini Studio via windows-terminal",
            ],
            recent_errors=[
                f"{(now - timedelta(minutes=6)).isoformat()} launch rejected for Atlas Bot Lab (moonlight): Moonlight was not detected locally.",
            ],
        ),
        registered_at=now - timedelta(hours=3),
        last_seen_at=now - timedelta(minutes=4, seconds=33),
    )

    return [desk, field]


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
