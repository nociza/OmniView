from __future__ import annotations

import argparse
from importlib.metadata import PackageNotFoundError, version
import json
import sys
from typing import Any
from urllib import error, parse, request

import uvicorn

from omniview.config import Settings, get_settings
from omniview.host_agent import HostAgent
from omniview.installers import ToolInstallerError, detect_tool, install_tool
from omniview.launcher.app import create_app as create_launcher_app
from omniview.launcher.config import get_launcher_settings
from omniview.launcher.models import LaunchRequest
from omniview.launcher.service import LauncherService, LauncherUnsupportedError
from omniview.main import create_app as create_control_plane_app
from omniview.models import ProtocolKind
from omniview.paths import client_config_path, host_config_path, hub_config_path
from omniview.role_config import (
    ClientConfig,
    HubConfig,
    HostConfig,
    default_host_config,
    load_client_config,
    load_host_config,
    load_hub_config,
    save_client_config,
    save_host_config,
    save_hub_config,
)
from omniview.service_manager import ServiceDefinition, ServiceManagerUnsupported, install_user_service, resolve_omv_executable, uninstall_user_service


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OMV command-line interface.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {_package_version()}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    hub = subparsers.add_parser("hub", help="Configure and run the central hub.")
    hub_sub = hub.add_subparsers(dest="hub_command", required=True)
    hub_init = hub_sub.add_parser("init", help="Write a hub config file.")
    hub_init.add_argument("--host", default="0.0.0.0")
    hub_init.add_argument("--port", type=int, default=8000)
    hub_init.add_argument("--cors-origin", action="append", default=[])
    hub_init.set_defaults(func=hub_init_command)

    hub_start = hub_sub.add_parser("start", help="Start the hub from config.")
    hub_start.add_argument("--host")
    hub_start.add_argument("--port", type=int)
    hub_start.set_defaults(func=hub_start_command)

    hub_doctor = hub_sub.add_parser("doctor", help="Inspect the hub setup.")
    hub_doctor.add_argument("--base-url")
    hub_doctor.set_defaults(func=hub_doctor_command)

    hub_service_install = hub_sub.add_parser("service-install", help="Install the hub as a user service.")
    hub_service_install.set_defaults(func=hub_service_install_command)

    hub_service_uninstall = hub_sub.add_parser("service-uninstall", help="Remove the hub user service.")
    hub_service_uninstall.set_defaults(func=hub_service_uninstall_command)

    client = subparsers.add_parser("client", help="Configure and run the native client launcher.")
    client_sub = client.add_subparsers(dest="client_command", required=True)
    client_init = client_sub.add_parser("init", help="Write a native-client config file.")
    client_init.add_argument("--hub-url", default="http://127.0.0.1:8000")
    client_init.add_argument("--host", default="127.0.0.1")
    client_init.add_argument("--port", type=int, default=32145)
    client_init.add_argument("--client-id")
    client_init.add_argument("--name")
    client_init.add_argument("--token")
    client_init.add_argument("--telemetry-interval", type=int, default=30)
    client_init.add_argument("--disable-telemetry", action="store_true")
    client_init.add_argument("--moonlight-binary")
    client_init.add_argument("--moonlight-app", default="Desktop")
    client_init.set_defaults(func=client_init_command)

    client_start = client_sub.add_parser("start", help="Start the local launcher from config.")
    client_start.add_argument("--host")
    client_start.add_argument("--port", type=int)
    client_start.set_defaults(func=client_start_command)

    client_doctor = client_sub.add_parser("doctor", help="Inspect native-client launch capabilities.")
    client_doctor.set_defaults(func=client_doctor_command)

    client_install = client_sub.add_parser("install", help="Install native-client dependencies.")
    client_install.add_argument("tool", choices=["moonlight", "tailscale"], nargs="?", default="moonlight")
    client_install.set_defaults(func=install_command)

    client_service_install = client_sub.add_parser("service-install", help="Install the native-client launcher as a user service.")
    client_service_install.set_defaults(func=client_service_install_command)

    client_service_uninstall = client_sub.add_parser("service-uninstall", help="Remove the native-client user service.")
    client_service_uninstall.set_defaults(func=client_service_uninstall_command)

    host = subparsers.add_parser("host", help="Configure and run a reporting host agent.")
    host_sub = host.add_subparsers(dest="host_command", required=True)
    host_init = host_sub.add_parser("init", help="Write a host config file.")
    host_init.add_argument("--hub-url", default="http://127.0.0.1:8000")
    host_init.add_argument("--node-id")
    host_init.add_argument("--name")
    host_init.add_argument("--overlay-ip")
    host_init.add_argument("--location")
    host_init.add_argument("--description")
    host_init.add_argument("--tag", action="append", default=[])
    host_init.add_argument("--headless", action="store_true")
    host_init.add_argument("--protocol", action="append", choices=[kind.value for kind in ProtocolKind], default=[])
    host_init.add_argument("--report-interval", type=int, default=30)
    host_init.add_argument("--screenshot-interval", type=int, default=60)
    host_init.add_argument("--no-screenshots", action="store_true")
    host_init.set_defaults(func=host_init_command)

    host_start = host_sub.add_parser("start", help="Start the host agent from config.")
    host_start.set_defaults(func=host_start_command)

    host_report = host_sub.add_parser("report", help="Send one telemetry report or print it.")
    host_report.add_argument("--dry-run", action="store_true")
    host_report.set_defaults(func=host_report_command)

    host_doctor = host_sub.add_parser("doctor", help="Inspect host readiness and hub connectivity.")
    host_doctor.set_defaults(func=host_doctor_command)

    host_install = host_sub.add_parser("install", help="Install host-side dependencies.")
    host_install.add_argument("tool", choices=["sunshine", "tailscale"], nargs="?", default="sunshine")
    host_install.set_defaults(func=install_command)

    host_service_install = host_sub.add_parser("service-install", help="Install the host agent as a user service.")
    host_service_install.set_defaults(func=host_service_install_command)

    host_service_uninstall = host_sub.add_parser("service-uninstall", help="Remove the host-agent user service.")
    host_service_uninstall.set_defaults(func=host_service_uninstall_command)

    install_parser = subparsers.add_parser("install", help="Install an external dependency like Moonlight or Sunshine.")
    install_parser.add_argument("tool", choices=["moonlight", "sunshine", "tailscale"])
    install_parser.set_defaults(func=install_command)

    status_parser = subparsers.add_parser("status", help="Show local role status across hub, client, and host.")
    status_parser.set_defaults(func=status_command)

    nodes = subparsers.add_parser("nodes", help="List nodes from a running hub.")
    nodes.add_argument("--base-url", default=None, help="Base URL of the control plane.")
    nodes.set_defaults(func=nodes_command)

    capabilities = subparsers.add_parser("capabilities", help="Show local native-client launcher capabilities.")
    capabilities.set_defaults(func=capabilities_command)

    launch = subparsers.add_parser("launch", help="Launch a node protocol directly from the command line.")
    launch.add_argument("node_id", help="Node identifier from the control plane.")
    launch.add_argument("--base-url", default=None, help="Base URL of the control plane.")
    launch.add_argument("--protocol", choices=[kind.value for kind in ProtocolKind], help="Override the protocol to launch.")
    launch.add_argument("--dry-run", action="store_true", help="Print the command that would run instead of launching it.")
    launch.set_defaults(func=launch_command)

    return parser


def hub_init_command(args: argparse.Namespace) -> None:
    config = HubConfig(host=args.host, port=args.port, cors_origins=args.cors_origin or HubConfig().cors_origins)
    path = save_hub_config(config)
    print(f"Wrote hub config to {path}")
    print("Next: omv hub start")
    print("Optional: omv hub service-install")


def hub_start_command(args: argparse.Namespace) -> None:
    config = load_hub_config()
    effective_host = args.host or config.host
    effective_port = args.port or config.port
    settings = _settings_from_hub_config(config)
    uvicorn.run(create_control_plane_app(settings=settings), host=effective_host, port=effective_port, log_level="info")


def hub_doctor_command(args: argparse.Namespace) -> None:
    config = load_hub_config()
    base_settings = get_settings()
    base_url = args.base_url or f"http://127.0.0.1:{config.port}"
    print(f"config:   {hub_config_path()}")
    print(f"listen:   {config.host}:{config.port}")
    print(f"frontend: {base_settings.frontend_dist} ({'ok' if base_settings.frontend_dist.exists() else 'missing'})")
    try:
        health = _fetch_json(f"{_normalize_base_url(base_url)}/api/health")
        print(f"health:   {health['status']}")
    except SystemExit as exc:
        print(f"health:   unreachable ({exc})")


def hub_service_install_command(args: argparse.Namespace) -> None:
    del args
    _install_service(role="hub", label="dev.omv.hub", description="OMV central hub", command=[resolve_omv_executable(), "hub", "start"])


def hub_service_uninstall_command(args: argparse.Namespace) -> None:
    del args
    _uninstall_service(role="hub", label="dev.omv.hub", description="OMV central hub", command=[resolve_omv_executable(), "hub", "start"])


def client_init_command(args: argparse.Namespace) -> None:
    config = ClientConfig(
        hub_url=args.hub_url,
        host=args.host,
        port=args.port,
        client_id=args.client_id,
        name=args.name,
        token=args.token,
        telemetry_enabled=not args.disable_telemetry,
        telemetry_interval_seconds=args.telemetry_interval,
        moonlight_binary=args.moonlight_binary,
        moonlight_app_name=args.moonlight_app,
    )
    path = save_client_config(config)
    print(f"Wrote client config to {path}")
    print("Optional: omv client install moonlight")
    print("Optional: omv client install tailscale")
    print("Then: omv client start")
    print("Optional: omv client service-install")


def client_start_command(args: argparse.Namespace) -> None:
    settings = get_launcher_settings()
    uvicorn.run(
        create_launcher_app(settings=settings),
        host=args.host or settings.host,
        port=args.port or settings.port,
        log_level="info",
    )


def client_doctor_command(args: argparse.Namespace) -> None:
    del args
    config = load_client_config()
    base_url = f"http://{config.host}:{config.port}"
    print(f"config:     {client_config_path()}")
    print(f"hub:        {config.hub_url}")
    print(f"launcher:   {config.host}:{config.port}")
    print(f"telemetry:  {'enabled' if config.telemetry_enabled else 'disabled'} every {config.telemetry_interval_seconds}s")
    print(f"moonlight:  {detect_tool('moonlight').detail}")
    print(f"tailscale:  {detect_tool('tailscale').detail}")
    try:
        status = _fetch_json(f"{base_url}/api/status")
        print(f"service:    reachable ({status['viewer_platform']})")
    except SystemExit as exc:
        print(f"service:    unreachable ({exc})")
    capabilities_command(argparse.Namespace())


def client_service_install_command(args: argparse.Namespace) -> None:
    del args
    _install_service(role="client", label="dev.omv.client", description="OMV native client launcher", command=[resolve_omv_executable(), "client", "start"])


def client_service_uninstall_command(args: argparse.Namespace) -> None:
    del args
    _uninstall_service(role="client", label="dev.omv.client", description="OMV native client launcher", command=[resolve_omv_executable(), "client", "start"])


def host_init_command(args: argparse.Namespace) -> None:
    selected_protocols = [ProtocolKind(item) for item in args.protocol] if args.protocol else None
    config = default_host_config(
        hub_url=args.hub_url,
        node_id=args.node_id,
        name=args.name,
        overlay_ip=args.overlay_ip,
        location=args.location,
        description=args.description,
        tags=args.tag,
        headless=args.headless,
        protocols=selected_protocols,
    )
    config = config.model_copy(
        update={
            "report_interval_seconds": args.report_interval,
            "screenshot_interval_seconds": args.screenshot_interval,
            "screenshots_enabled": not args.no_screenshots,
        }
    )
    path = save_host_config(config)
    print(f"Wrote host config to {path}")
    print(f"Node ID: {config.node_id}")
    print(f"Overlay: {config.overlay_ip}")
    if any(protocol.kind is ProtocolKind.MOONLIGHT for protocol in config.protocols):
        print("Recommended: omv host install sunshine")
    print("Optional: omv host install tailscale")
    print("Then: omv host start")
    print("Optional: omv host service-install")


def host_start_command(args: argparse.Namespace) -> None:
    del args
    agent = HostAgent(load_host_config())
    agent.run_forever()


def host_report_command(args: argparse.Namespace) -> None:
    agent = HostAgent(load_host_config())
    report = agent.post_once(dry_run=args.dry_run)
    payload = report.model_dump(mode="json", exclude_none=True)
    print(json.dumps(payload, indent=2))
    if not args.dry_run:
        print("Telemetry posted successfully.")


def host_doctor_command(args: argparse.Namespace) -> None:
    del args
    config = load_host_config()
    configured_protocols = ", ".join(protocol.kind.value for protocol in config.protocols) or "-"
    print(f"config:      {host_config_path()}")
    print(f"hub:         {config.hub_url}")
    print(f"node:        {config.node_id} ({config.name})")
    print(f"overlay ip:  {config.overlay_ip}")
    print(f"protocols:   {configured_protocols}")
    if any(protocol.kind is ProtocolKind.MOONLIGHT for protocol in config.protocols):
        print(f"sunshine:    {detect_tool('sunshine').detail}")
    if any(protocol.kind is ProtocolKind.VNC for protocol in config.protocols):
        print("vnc:         Built-in OS service; ensure Screen Sharing or a VNC server is enabled.")
    print(f"tailscale:   {detect_tool('tailscale').detail}")
    try:
        health = _fetch_json(f"{_normalize_base_url(config.hub_url)}/api/health")
        print(f"hub health:  {health['status']}")
    except SystemExit as exc:
        print(f"hub health:  unreachable ({exc})")
    try:
        report = HostAgent(config).build_report().model_dump(mode="json", exclude_none=True)
        metrics = report["telemetry"]["metrics"]
        print(f"metrics:     cpu={metrics['cpu_percent']:.1f}% mem={metrics['memory_percent']:.1f}%")
        print(f"thumbnail:   {'present' if report['telemetry'].get('thumbnail_data_url') else 'missing'}")
    except Exception as exc:  # pragma: no cover - defensive doctor path
        print(f"metrics:     failed ({exc})")


def host_service_install_command(args: argparse.Namespace) -> None:
    del args
    _install_service(role="host", label="dev.omv.host", description="OMV host agent", command=[resolve_omv_executable(), "host", "start"])


def host_service_uninstall_command(args: argparse.Namespace) -> None:
    del args
    _uninstall_service(role="host", label="dev.omv.host", description="OMV host agent", command=[resolve_omv_executable(), "host", "start"])


def install_command(args: argparse.Namespace) -> None:
    try:
        print(install_tool(args.tool))
    except ToolInstallerError as exc:
        raise SystemExit(str(exc)) from exc


def status_command(args: argparse.Namespace) -> None:
    del args
    hub_configured = hub_config_path().exists()
    hub = load_hub_config()
    hub_health = _probe_status(f"http://127.0.0.1:{hub.port}/api/health", lambda payload: payload.get("status", "ok"))
    print(
        "hub:        "
        f"configured={'yes' if hub_configured else 'no '} "
        f"listen={hub.host}:{hub.port} "
        f"health={hub_health}"
    )

    client_configured = client_config_path().exists()
    client = load_client_config()
    client_health = _probe_status(
        f"http://{client.host}:{client.port}/api/status",
        lambda payload: payload.get("viewer_platform", "ok"),
    )
    print(
        "client:     "
        f"configured={'yes' if client_configured else 'no '} "
        f"listen={client.host}:{client.port} "
        f"hub={client.hub_url} "
        f"service={client_health}"
    )

    host_configured = host_config_path().exists()
    if host_configured:
        host = load_host_config()
        protocols = ",".join(protocol.kind.value for protocol in host.protocols) or "-"
        print(
            "host:       "
            f"configured=yes node={host.node_id} overlay={host.overlay_ip} protocols={protocols}"
        )
    else:
        print("host:       configured=no")

    print(
        "tools:      "
        f"moonlight={'yes' if detect_tool('moonlight').installed else 'no '} "
        f"sunshine={'yes' if detect_tool('sunshine').installed else 'no '} "
        f"tailscale={'yes' if detect_tool('tailscale').installed else 'no '}"
    )


def nodes_command(args: argparse.Namespace) -> None:
    nodes = _fetch_json(f"{_normalize_base_url(_default_base_url(args.base_url))}/api/nodes")
    for node in nodes:
        primary = node["protocols"][0]["kind"] if node["protocols"] else "-"
        print(f'{node["node_id"]:20} {node["status"]:8} {primary:10} {node["overlay_ip"]:15} {node["name"]}')


def capabilities_command(args: argparse.Namespace) -> None:
    del args
    status = LauncherService(get_launcher_settings()).status()
    print(f"platform: {status.viewer_platform}")
    print(f"config:   {status.config_path}")
    for capability in status.protocols:
        state = "yes" if capability.available else "no"
        strategy = capability.strategy or "-"
        print(f"{capability.kind.value:10} available={state:3} strategy={strategy:20} detail={capability.detail}")


def launch_command(args: argparse.Namespace) -> None:
    node = _fetch_json(f"{_normalize_base_url(_default_base_url(args.base_url))}/api/nodes/{parse.quote(args.node_id)}")
    protocol = _select_protocol(node, override=args.protocol)
    launcher = LauncherService(get_launcher_settings())

    payload = LaunchRequest(
        node_id=node["node_id"],
        node_name=node["name"],
        overlay_ip=node["overlay_ip"],
        platform=node.get("platform"),
        protocol=ProtocolKind(protocol["kind"]),
        label=protocol.get("label"),
        host=protocol.get("host"),
        port=protocol.get("port"),
        username=protocol.get("username"),
        path=protocol.get("path"),
        app_name=protocol.get("app_name"),
        launch_uri=protocol.get("launch_uri"),
        dry_run=args.dry_run,
    )

    try:
        result = launcher.launch(payload)
    except LauncherUnsupportedError as exc:
        raise SystemExit(str(exc)) from exc

    print(result.detail)
    if result.command:
        print("command:", json.dumps(result.command))


def _select_protocol(node: dict[str, Any], *, override: str | None) -> dict[str, Any]:
    protocols = node.get("protocols", [])
    if not protocols:
        raise SystemExit(f'Node "{node["node_id"]}" has no configured protocols.')

    if override is None:
        return protocols[0]

    for protocol in protocols:
        if protocol["kind"] == override:
            return protocol

    raise SystemExit(f'Node "{node["node_id"]}" does not support protocol "{override}".')


def _fetch_json(url: str, *, timeout_seconds: float = 5.0) -> Any:
    try:
        with request.urlopen(request.Request(url, headers={"Accept": "application/json"}), timeout=timeout_seconds) as response:
            return json.load(response)
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise SystemExit(f"Request failed with HTTP {exc.code}: {detail or exc.reason}") from exc
    except error.URLError as exc:
        raise SystemExit(f"Unable to reach {url}: {exc.reason}") from exc
    except TimeoutError as exc:
        raise SystemExit(f"Unable to reach {url}: timed out") from exc


def _normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def _settings_from_hub_config(config: HubConfig) -> Settings:
    base = get_settings()
    return Settings(
        api_title=base.api_title,
        online_ttl_seconds=base.online_ttl_seconds,
        stale_ttl_seconds=base.stale_ttl_seconds,
        poll_interval_seconds=base.poll_interval_seconds,
        cors_origins=tuple(config.cors_origins),
        frontend_dist=base.frontend_dist,
    )


def _default_base_url(candidate: str | None) -> str:
    if candidate:
        return candidate
    config = load_hub_config()
    return f"http://127.0.0.1:{config.port}"


def _package_version() -> str:
    try:
        return version("omv")
    except PackageNotFoundError:
        pass
    return "0.0.0"


def _probe_status(url: str, extractor) -> str:
    try:
        payload = _fetch_json(url, timeout_seconds=1.5)
    except SystemExit:
        return "unreachable"
    return str(extractor(payload))


def _install_service(*, role: str, label: str, description: str, command: list[str]) -> None:
    try:
        path = install_user_service(ServiceDefinition(role=role, label=label, description=description, command=command))
    except ServiceManagerUnsupported as exc:
        raise SystemExit(str(exc)) from exc
    print(f"Installed {role} service at {path}")


def _uninstall_service(*, role: str, label: str, description: str, command: list[str]) -> None:
    try:
        path = uninstall_user_service(ServiceDefinition(role=role, label=label, description=description, command=command))
    except ServiceManagerUnsupported as exc:
        raise SystemExit(str(exc)) from exc
    print(f"Removed {role} service at {path}")
