from __future__ import annotations

import argparse
import base64
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib import request


def main() -> None:
    parser = argparse.ArgumentParser(description="Push a sample OmniView agent report to the control plane.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="FastAPI base URL")
    parser.add_argument("--node-id", default="sample-agent", help="Unique node identifier")
    parser.add_argument("--name", default="Sample Agent", help="Display name")
    parser.add_argument("--overlay-ip", default="100.64.0.50", help="Overlay network IP")
    parser.add_argument("--thumbnail", type=Path, help="Optional path to an image file to embed as a data URL")
    args = parser.parse_args()

    payload = {
        "profile": {
            "node_id": args.node_id,
            "name": args.name,
            "hostname": args.node_id,
            "overlay_ip": args.overlay_ip,
            "platform": "linux",
            "description": "Sample node submitted by examples/agent_reporter.py",
            "location": "CLI demo",
            "tags": ["example"],
            "headless": True,
            "agent_version": "example-0.1.0",
            "protocols": [
                {"kind": "moonlight", "label": "Moonlight", "priority": 1, "port": 47984, "app_name": "Desktop"},
                {"kind": "ssh", "label": "SSH", "priority": 2, "port": 22, "username": "ops"},
            ],
        },
        "telemetry": {
            "reported_at": datetime.now(UTC).isoformat(),
            "metrics": {
                "cpu_percent": 34.5,
                "memory_percent": 51.2,
                "memory_used_gb": 8.2,
                "memory_total_gb": 16.0,
                "temperature_c": 66.1,
                "gpu_percent": 23.0,
                "network_rx_mbps": 3.1,
                "network_tx_mbps": 1.7,
            },
            "render_state": "Example workflow",
            "active_session": ":99",
            "thumbnail_data_url": _thumbnail_data_url(args.thumbnail),
        },
    }

    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        f"{args.base_url.rstrip('/')}/api/agent/report",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req) as response:
        print(response.read().decode("utf-8"))


def _thumbnail_data_url(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


if __name__ == "__main__":
    main()
