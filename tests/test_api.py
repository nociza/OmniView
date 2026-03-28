from __future__ import annotations

from fastapi.testclient import TestClient

from omniview.main import app
from omniview.security import ADMIN_AUTH_SCHEME, AGENT_TOKEN_HEADER


client = TestClient(app)


def admin_headers() -> dict[str, str]:
    return {"Authorization": f"{ADMIN_AUTH_SCHEME} {app.state.settings.admin_token}"}


def agent_headers() -> dict[str, str]:
    return {AGENT_TOKEN_HEADER: app.state.settings.agent_token}


def test_dashboard_seed_data_is_available() -> None:
    response = client.get("/api/dashboard", headers=admin_headers())
    assert response.status_code == 200

    payload = response.json()
    assert payload["summary"]["counts"]["total"] >= 4
    assert payload["poll_interval_seconds"] == 15
    assert any(node["preferred_protocol"] == "moonlight" for node in payload["nodes"])
    assert len(payload["clients"]) >= 2


def test_root_serves_embedded_frontend() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "id=\"root\"" in response.text


def test_agent_report_upserts_node_and_launch_uri() -> None:
    payload = {
        "profile": {
            "node_id": "integration-box",
            "name": "Integration Box",
            "hostname": "integration-box",
            "overlay_ip": "100.70.0.8",
            "platform": "linux",
            "description": "CI worker",
            "location": "Test Rack",
            "tags": ["ci"],
            "headless": True,
            "agent_version": "agent-1.0.0",
            "protocols": [
                {"kind": "moonlight", "label": "Moonlight", "priority": 1, "port": 47984},
                {"kind": "ssh", "label": "SSH", "priority": 2, "port": 22, "username": "runner"},
            ],
        },
        "telemetry": {
            "metrics": {
                "cpu_percent": 14.2,
                "memory_percent": 40.1,
                "memory_used_gb": 3.2,
                "memory_total_gb": 8,
                "temperature_c": 52.0,
                "gpu_percent": 0,
                "network_rx_mbps": 1.1,
                "network_tx_mbps": 0.3,
            },
            "render_state": "Idle",
            "active_session": ":0",
        },
    }

    response = client.post("/api/agent/report", json=payload, headers=agent_headers())
    assert response.status_code == 202
    node = response.json()
    assert node["node_id"] == "integration-box"
    assert node["protocols"][0]["launch_uri"].startswith("omv-moonlight://")

    lookup = client.get("/api/nodes/integration-box", headers=admin_headers())
    assert lookup.status_code == 200
    assert lookup.json()["telemetry"]["metrics"]["cpu_percent"] == 14.2


def test_unknown_node_telemetry_returns_404() -> None:
    response = client.post(
        "/api/nodes/missing-node/telemetry",
        headers=agent_headers(),
        json={
            "metrics": {
                "cpu_percent": 10,
                "memory_percent": 20,
            },
        },
    )
    assert response.status_code == 404


def test_client_report_upserts_viewer_client() -> None:
    payload = {
        "profile": {
            "client_id": "road-warrior-client",
            "name": "Road Warrior Client",
            "hostname": "roadbook",
            "overlay_ip": "100.99.1.11",
            "platform": "macos",
            "hub_url": "http://100.64.8.21:8000",
            "launcher_url": "http://127.0.0.1:32145",
            "app_version": "omv-0.3.2",
            "capabilities": [
                {"kind": "moonlight", "available": True, "strategy": "moonlight-cli", "detail": "Moonlight installed locally."},
                {"kind": "ssh", "available": True, "strategy": "terminal-applescript", "detail": "Terminal SSH handoff available."},
            ],
        },
        "telemetry": {
            "metrics": {
                "cpu_percent": 22.5,
                "memory_percent": 51.0,
                "memory_used_gb": 8.1,
                "memory_total_gb": 16.0,
                "network_latency_ms": 31.4,
                "network_rx_mbps": 3.2,
                "network_tx_mbps": 1.0,
                "uptime_seconds": 7200,
            },
            "render_state": "Launcher idle",
            "active_session": "console",
            "recent_logs": ["2026-03-08T01:02:03Z launch ssh for atlas via terminal-applescript"],
            "recent_errors": [],
            "collector_notes": [],
        },
    }

    response = client.post("/api/clients/report", json=payload, headers=agent_headers())
    assert response.status_code == 202
    viewer = response.json()
    assert viewer["client_id"] == "road-warrior-client"
    assert viewer["capabilities"][0]["kind"] == "moonlight"

    lookup = client.get("/api/clients/road-warrior-client", headers=admin_headers())
    assert lookup.status_code == 200
    assert lookup.json()["telemetry"]["metrics"]["network_latency_ms"] == 31.4


def test_session_login_sets_cookie_for_dashboard() -> None:
    session = client.post("/api/session", json={"token": app.state.settings.admin_token})
    assert session.status_code == 200
    response = client.get("/api/dashboard")
    assert response.status_code == 200
