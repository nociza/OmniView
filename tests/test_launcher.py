from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from omniview.launcher.app import create_app
from omniview.launcher.config import LauncherSettings
from omniview.launcher.service import CommandRunner, LauncherService


class DummyRunner(CommandRunner):
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def spawn(self, command: list[str]) -> None:
        self.commands.append(command)


def make_settings(tmp_path: Path, *, token: str | None = None) -> LauncherSettings:
    return LauncherSettings(
        hub_url='http://127.0.0.1:8000',
        hub_token='agent-token',
        host='127.0.0.1',
        port=32145,
        client_id='viewer-client',
        client_name='Viewer Client',
        token=token,
        telemetry_enabled=False,
        telemetry_interval_seconds=30,
        log_retention=50,
        allow_origins=('*',),
        config_path=tmp_path / 'client.toml',
        moonlight_binary=None,
        moonlight_app_name='Desktop',
        ssh_terminal='auto',
        command_templates={},
    )


def test_launcher_status_and_dry_run_moonlight(tmp_path: Path) -> None:
    moonlight_binary = tmp_path / 'Moonlight'
    moonlight_binary.write_text('#!/bin/sh\n')
    moonlight_binary.chmod(0o755)

    def fake_which(name: str) -> str | None:
        mapping = {
            'open': '/usr/bin/open',
            'osascript': '/usr/bin/osascript',
            'ssh': '/usr/bin/ssh',
            'moonlight': str(moonlight_binary),
        }
        return mapping.get(name)

    settings = make_settings(tmp_path, token='secret-token')
    service = LauncherService(settings, system_name='Darwin', which_resolver=fake_which, runner=DummyRunner())
    client = TestClient(create_app(settings=settings, service=service))

    status = client.get('/api/status')
    assert status.status_code == 200
    protocols = {item['kind']: item for item in status.json()['protocols']}
    assert protocols['moonlight']['available'] is True
    assert protocols['vnc']['available'] is True
    assert protocols['ssh']['available'] is True

    launch = client.post(
        '/api/launch',
        headers={'X-OMV-Token': 'secret-token'},
        json={
            'node_name': 'Atlas Bot Lab',
            'overlay_ip': '100.84.16.10',
            'protocol': 'moonlight',
            'host': '100.84.16.10',
            'app_name': 'Desktop',
            'dry_run': True,
        },
    )
    assert launch.status_code == 200
    payload = launch.json()
    assert payload['launched'] is False
    assert payload['strategy'] == 'moonlight-cli'
    assert payload['command'] == [str(moonlight_binary), 'stream', '100.84.16.10', 'Desktop']


def test_launcher_requires_token_for_launch(tmp_path: Path) -> None:
    def fake_which(name: str) -> str | None:
        mapping = {
            'open': '/usr/bin/open',
        }
        return mapping.get(name)

    settings = make_settings(tmp_path, token='secret-token')
    service = LauncherService(settings, system_name='Darwin', which_resolver=fake_which, runner=DummyRunner())
    client = TestClient(create_app(settings=settings, service=service))

    response = client.post(
        '/api/launch',
        json={
            'node_name': 'Mac Mini Studio',
            'overlay_ip': '100.92.24.7',
            'protocol': 'vnc',
            'host': '100.92.24.7',
            'port': 5900,
            'dry_run': True,
        },
    )
    assert response.status_code == 401


def test_launcher_executes_vnc_command_with_runner(tmp_path: Path) -> None:
    runner = DummyRunner()

    def fake_which(name: str) -> str | None:
        mapping = {
            'open': '/usr/bin/open',
        }
        return mapping.get(name)

    settings = make_settings(tmp_path)
    service = LauncherService(settings, system_name='Darwin', which_resolver=fake_which, runner=runner)
    client = TestClient(create_app(settings=settings, service=service))

    response = client.post(
        '/api/launch',
        json={
            'node_name': 'Mac Mini Studio',
            'overlay_ip': '100.92.24.7',
            'protocol': 'vnc',
            'host': '100.92.24.7',
            'port': 5900,
            'dry_run': False,
        },
    )
    assert response.status_code == 200
    assert runner.commands == [['open', 'vnc://100.92.24.7:5900']]
