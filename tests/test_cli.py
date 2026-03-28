from __future__ import annotations

from argparse import Namespace
import json
from pathlib import Path

import pytest

from omniview.cli import (
    _select_protocol,
    client_start_command,
    host_init_command,
    host_report_command,
    host_start_command,
    hub_init_command,
    hub_rotate_tokens_command,
    hub_start_command,
    launch_command,
    status_command,
)
from omniview.launcher.config import get_launcher_settings
from omniview.launcher.models import LaunchResponse
from omniview.role_config import ClientConfig, load_host_config, load_hub_config, save_client_config
from omniview.models import ProtocolKind


@pytest.fixture(autouse=True)
def clear_launcher_settings_cache() -> None:
    get_launcher_settings.cache_clear()
    yield
    get_launcher_settings.cache_clear()


def test_select_protocol_uses_primary_when_no_override() -> None:
    node = {
        "node_id": "atlas-bot-lab",
        "protocols": [
            {"kind": "moonlight", "label": "Moonlight"},
            {"kind": "ssh", "label": "SSH"},
        ],
    }

    selected = _select_protocol(node, override=None)
    assert selected["kind"] == "moonlight"


def test_launch_command_dry_run_uses_launcher_service(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    node = {
        "node_id": "atlas-bot-lab",
        "name": "Atlas Bot Lab",
        "overlay_ip": "100.84.16.10",
        "platform": "linux",
        "protocols": [
            {
                "kind": "moonlight",
                "label": "Moonlight",
                "host": "100.84.16.10",
                "port": 47984,
                "app_name": "Desktop",
                "launch_uri": "omv-moonlight://connect?host=100.84.16.10",
            }
        ],
    }

    class DummyLauncher:
        def launch(self, payload):
            assert payload.protocol is ProtocolKind.MOONLIGHT
            assert payload.dry_run is True
            return LaunchResponse(
                launched=False,
                protocol=ProtocolKind.MOONLIGHT,
                strategy="moonlight-cli",
                detail="Launching Moonlight directly into 'Desktop'.",
                command=["/Applications/Moonlight.app/Contents/MacOS/Moonlight", "stream", "100.84.16.10", "Desktop"],
            )

    monkeypatch.setattr("omniview.cli._fetch_json", lambda url, **kwargs: node)
    monkeypatch.setattr("omniview.cli.get_launcher_settings", lambda: object())
    monkeypatch.setattr("omniview.cli.LauncherService", lambda settings: DummyLauncher())

    launch_command(
        Namespace(
                node_id="atlas-bot-lab",
                base_url="http://127.0.0.1:8000",
                admin_token="admin-token",
                protocol=None,
                dry_run=True,
            )
    )

    output = capsys.readouterr().out
    assert "Launching Moonlight directly into 'Desktop'." in output
    assert "/Applications/Moonlight.app/Contents/MacOS/Moonlight" in output


def test_hub_init_writes_role_config(monkeypatch: pytest.MonkeyPatch, tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("OMV_CONFIG_DIR", str(tmp_path))
    hub_init_command(
        Namespace(
            host="127.0.0.1",
            port=8123,
            cors_origin=["http://localhost:3000"],
            tls_cert=None,
            tls_key=None,
            allow_insecure_public_http=False,
        )
    )

    config = load_hub_config()
    assert config.port == 8123
    assert config.cors_origins == ["http://localhost:3000"]
    assert "Wrote hub config" in capsys.readouterr().out


def test_client_config_is_discovered_by_launcher_settings(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("OMV_CONFIG_DIR", str(tmp_path))
    save_client_config(ClientConfig(port=45678, moonlight_app_name="Steam"))

    settings = get_launcher_settings()
    assert settings.port == 45678
    assert settings.moonlight_app_name == "Steam"


def test_host_init_and_dry_run_report(monkeypatch: pytest.MonkeyPatch, tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("OMV_CONFIG_DIR", str(tmp_path))
    host_init_command(
        Namespace(
                hub_url="http://127.0.0.1:8000",
                hub_token="secret-agent-token",
                node_id="test-host",
                name="Test Host",
                overlay_ip="100.64.0.10",
            location="Rack",
            description="demo",
            tag=["test"],
            headless=True,
            protocol=["ssh"],
            report_interval=15,
            screenshot_interval=30,
            no_screenshots=True,
        )
    )

    config = load_host_config()
    assert config.node_id == "test-host"
    assert config.protocols[0].kind is ProtocolKind.SSH
    assert config.screenshots_enabled is False

    capsys.readouterr()
    host_report_command(Namespace(dry_run=True))
    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"]["node_id"] == "test-host"


def test_status_command_reports_local_roles(monkeypatch: pytest.MonkeyPatch, tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("OMV_CONFIG_DIR", str(tmp_path))
    hub_init_command(
        Namespace(
            host="127.0.0.1",
            port=8123,
            cors_origin=[],
            tls_cert=None,
            tls_key=None,
            allow_insecure_public_http=False,
        )
    )
    save_client_config(ClientConfig(port=45678))
    (Path(tmp_path) / "host.toml").write_text(
        """
hub_url = "http://127.0.0.1:8000"
report_interval_seconds = 30
screenshot_interval_seconds = 60
screenshots_enabled = false
node_id = "test-host"
name = "Test Host"
hostname = "testbox"
overlay_ip = "100.64.0.10"
platform = "linux"
headless = true

[[protocols]]
kind = "ssh"
label = "SSH"
priority = 1
port = 22
username = "ops"
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setattr("omniview.cli._fetch_json", lambda url, **kwargs: {"status": "ok"} if url.endswith("/api/health") else {"viewer_platform": "darwin"})
    monkeypatch.setattr("omniview.cli.detect_tool", lambda name: Namespace(installed=name != "sunshine", detail="ok"))

    capsys.readouterr()
    status_command(Namespace())
    output = capsys.readouterr().out
    assert "hub:" in output
    assert "client:" in output
    assert "host:" in output
    assert "tools:" in output


def test_hub_init_rejects_public_http_without_explicit_override(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("OMV_CONFIG_DIR", str(tmp_path))
    with pytest.raises(SystemExit, match="Refusing to bind the hub"):
        hub_init_command(
            Namespace(
                host="0.0.0.0",
                port=8123,
                cors_origin=[],
                tls_cert=None,
                tls_key=None,
                allow_insecure_public_http=False,
            )
        )


def test_hub_rotate_tokens_syncs_local_agent_configs(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("OMV_CONFIG_DIR", str(tmp_path))
    hub_init_command(
        Namespace(
            host="127.0.0.1",
            port=8000,
            cors_origin=[],
            tls_cert=None,
            tls_key=None,
            allow_insecure_public_http=False,
        )
    )
    initial_hub = load_hub_config()
    save_client_config(ClientConfig(hub_url="http://127.0.0.1:8000", hub_token=initial_hub.agent_token))
    host_init_command(
        Namespace(
            hub_url="http://127.0.0.1:8000",
            hub_token=initial_hub.agent_token,
            node_id="test-host",
            name="Test Host",
            overlay_ip="100.64.0.10",
            location="Rack",
            description="demo",
            tag=["test"],
            headless=True,
            protocol=["ssh"],
            report_interval=15,
            screenshot_interval=30,
            no_screenshots=True,
        )
    )

    hub_rotate_tokens_command(Namespace(scope="agent"))

    rotated_hub = load_hub_config()
    rotated_host = load_host_config()
    rotated_client = get_launcher_settings()
    assert rotated_hub.agent_token != initial_hub.agent_token
    assert rotated_host.hub_token == rotated_hub.agent_token
    assert rotated_client.hub_token == rotated_hub.agent_token


def test_hub_start_uses_background_service(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    recorded: dict[str, object] = {}

    def fake_install(definition):
        recorded["label"] = definition.label
        recorded["command"] = definition.command
        return Path("/tmp/dev.omv.hub.service")

    monkeypatch.setattr("omniview.cli.install_user_service", fake_install)
    monkeypatch.setattr("omniview.cli.resolve_omv_executable", lambda: "/usr/local/bin/omv")

    hub_start_command(Namespace())

    assert recorded["label"] == "dev.omv.hub"
    assert recorded["command"] == ["/usr/local/bin/omv", "hub", "run"]
    assert "Started hub service" in capsys.readouterr().out


def test_client_start_uses_background_service(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    recorded: dict[str, object] = {}

    def fake_install(definition):
        recorded["label"] = definition.label
        recorded["command"] = definition.command
        return Path("/tmp/dev.omv.client.service")

    monkeypatch.setattr("omniview.cli.install_user_service", fake_install)
    monkeypatch.setattr("omniview.cli.resolve_omv_executable", lambda: "/usr/local/bin/omv")

    client_start_command(Namespace())

    assert recorded["label"] == "dev.omv.client"
    assert recorded["command"] == ["/usr/local/bin/omv", "client", "run"]
    assert "Started client service" in capsys.readouterr().out


def test_host_start_uses_background_service(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    recorded: dict[str, object] = {}

    def fake_install(definition):
        recorded["label"] = definition.label
        recorded["command"] = definition.command
        return Path("/tmp/dev.omv.host.service")

    monkeypatch.setattr("omniview.cli.install_user_service", fake_install)
    monkeypatch.setattr("omniview.cli.resolve_omv_executable", lambda: "/usr/local/bin/omv")

    host_start_command(Namespace())

    assert recorded["label"] == "dev.omv.host"
    assert recorded["command"] == ["/usr/local/bin/omv", "host", "run"]
    assert "Started host service" in capsys.readouterr().out
