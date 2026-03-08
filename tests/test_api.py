from __future__ import annotations

from fastapi.testclient import TestClient

from omniview.main import app


client = TestClient(app)


def test_dashboard_seed_data_is_available() -> None:
    response = client.get("/api/dashboard")
    assert response.status_code == 200

    payload = response.json()
    assert payload["summary"]["counts"]["total"] >= 4
    assert payload["poll_interval_seconds"] == 15
    assert any(node["preferred_protocol"] == "moonlight" for node in payload["nodes"])


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

    response = client.post("/api/agent/report", json=payload)
    assert response.status_code == 202
    node = response.json()
    assert node["node_id"] == "integration-box"
    assert node["protocols"][0]["launch_uri"].startswith("omniview-moonlight://")

    lookup = client.get("/api/nodes/integration-box")
    assert lookup.status_code == 200
    assert lookup.json()["telemetry"]["metrics"]["cpu_percent"] == 14.2


def test_unknown_node_telemetry_returns_404() -> None:
    response = client.post(
        "/api/nodes/missing-node/telemetry",
        json={
            "metrics": {
                "cpu_percent": 10,
                "memory_percent": 20,
            },
        },
    )
    assert response.status_code == 404
