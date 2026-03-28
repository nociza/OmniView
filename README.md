# OMV

OMV is a self-hosted control plane for personal machines. One CLI installs everything a user needs to run the three roles in the system:

- `hub`: the central FastAPI server and embedded web UI
- `client`: the native-client launcher that opens Moonlight, VNC, SSH, or browser fallbacks on the machine you are sitting at, and reports viewer-machine telemetry back to the hub
- `host`: the reporting agent that pushes telemetry, screenshots, and protocol metadata to the hub

The PyPI package is the product. End users install only the CLI:

```bash
uv tool install omv
```

That gives them the `omv` command with the backend, embedded frontend, launcher service, and host agent bundled inside the same package.

## User model

There are three machine roles:

1. Central hub
   Hosts the website and API. Usually one stable machine on your tailnet or home network.
2. Native client
   Runs on the device that should launch native apps like Moonlight, Screen Sharing, or a terminal. This can be the same machine as the hub.
3. Hosts
   The machines you want to watch and connect to. Each host runs a lightweight agent and advertises the protocols it supports.

Typical layout:

- Home mini PC: `hub` + `client`
- Workstation: `host`
- Mac Mini: `host`
- Laptop on the road: `client`

## Install

### CLI only

```bash
uv tool install omv
omv --help
```

### Upgrade later

```bash
uv tool upgrade omv
```

### Remove

```bash
uv tool uninstall omv
```

## Quick start

### 1. Set up the hub

On the machine that should host the dashboard:

```bash
omv hub init --port 8000
omv hub start
```

`omv hub start` is the normal path. It installs or refreshes the user service and returns immediately.

Foreground debug:

```bash
omv hub run
```

`omv hub init` now generates:

- a secure default bind address: Tailscale IP when available, otherwise `127.0.0.1`
- an admin token for the dashboard and CLI read access
- an agent token for hosts and clients to report telemetry
- public-bind guardrails: wildcard or public binds require TLS unless you explicitly opt out

Bootstrap another machine with:

```bash
omv hub enroll host
omv hub enroll client
omv hub enroll browser
```

The browser session is protected. Open the hub URL and sign in with the admin token printed by `omv hub init` or `omv hub enroll browser`.

If you need to bind the hub publicly, configure TLS at init time:

```bash
    omv hub init --host 0.0.0.0 --tls-cert /path/to/fullchain.pem --tls-key /path/to/privkey.pem
    omv hub start
```

If you intentionally want plain HTTP on a wildcard or public bind, you must opt into it:

```bash
omv hub init --host 0.0.0.0 --allow-insecure-public-http
```

### 2. Set up a native client

On any machine that should open native apps when you click `Launch` in the dashboard:

```bash
omv client init --hub-url http://YOUR-HUB:8000 --hub-token YOUR_AGENT_TOKEN
omv client install moonlight
omv client start
```

`omv client start` is the normal path. It installs or refreshes the user service and returns immediately.

Foreground debug:

```bash
omv client run
```

If the hub and the viewing machine are the same box, `omv client init` can reuse the local hub agent token automatically.

The client service now reports viewer-side telemetry to the hub: CPU, memory, load average, network throughput, latency to the hub, best-effort GPU/power data, and recent launcher errors/logs.

The local launcher is now locked down by default:

- loopback bind by default
- strict browser origin allowlist derived from the hub URL
- no wildcard CORS
- launcher token required automatically if you bind it to a non-loopback address

### 3. Set up a host

On each machine you want to monitor:

```bash
omv host init --hub-url http://YOUR-HUB:8000 --hub-token YOUR_AGENT_TOKEN
omv host start
```

`omv host start` is the normal path. It installs or refreshes the user service and returns immediately.

Foreground debug:

```bash
omv host run
```

If the host machine is also the hub machine, `omv host init` can reuse the local hub agent token automatically.

For Linux hosts that should stream over Moonlight:

```bash
omv host install sunshine
```

Stop it without uninstalling the unit:

```bash
omv host stop
```

## Common workflows

### All-in-one machine

One machine can run both the hub and the native client:

```bash
omv hub init
omv client init --hub-url http://127.0.0.1:8000
omv hub start
omv client start
```

### Check local status

```bash
omv status
```

Example output:

```text
hub:        configured=yes listen=100.x.y.z:8000 health=ok
client:     configured=yes listen=127.0.0.1:32145 service=darwin
host:       configured=no
tools:      moonlight=yes sunshine=no tailscale=yes
```

### Inspect a specific role

```bash
omv hub doctor
omv client doctor
omv host doctor
```

### Rotate hub secrets

```bash
omv hub rotate-tokens
omv hub rotate-tokens agent
omv hub rotate-tokens admin
```

Rotating the agent token automatically rewrites local `client.toml` and `host.toml` when they point at the same hub. Remote machines must be re-enrolled with `omv hub enroll host` or `omv hub enroll client`.

### List nodes from the hub

```bash
omv nodes --base-url http://127.0.0.1:8000 --admin-token YOUR_ADMIN_TOKEN
```

### Launch a node from the terminal

```bash
omv launch atlas-bot-lab --base-url http://127.0.0.1:8000 --admin-token YOUR_ADMIN_TOKEN
```

### Dry-run a launch

```bash
omv launch atlas-bot-lab --base-url http://127.0.0.1:8000 --admin-token YOUR_ADMIN_TOKEN --dry-run
```

## Config files

OMV writes role-specific config files under `~/.config/omv/` on macOS and Linux.

- `~/.config/omv/hub.toml`
- `~/.config/omv/client.toml`
- `~/.config/omv/host.toml`

Use the CLI to create them instead of hand-writing them:

```bash
omv hub init
omv client init --hub-url http://127.0.0.1:8000
omv host init --hub-url http://127.0.0.1:8000
```

## Native protocol support

The hub only orchestrates. Real sessions are handed off to native tools on the current viewing device.

- `moonlight`: launches the local Moonlight binary
- `vnc`: opens the local OS handler for `vnc://...`
- `ssh`: opens a terminal on the current machine and runs `ssh`
- `guacamole`: opens a browser fallback URL

This boundary is deliberate: browsers cannot directly spawn arbitrary local applications.

## Dependency install commands

Install external tools from the CLI:

```bash
omv install moonlight
omv install sunshine
omv install tailscale
```

Role-scoped variants are also available:

```bash
omv client install moonlight
omv client install tailscale
omv host install sunshine
omv host install tailscale
```

## Operational notes

A few steps still depend on the target platform and cannot be fully automated away:

- Tailscale still needs user authentication, usually via `tailscale up`
- OMV now avoids `curl | sh` and unsigned release downloads in its install path. The CLI only uses system package managers such as Homebrew, winget, `apt-get`, `dnf`, or `pacman`.
- The hub API is authenticated by default. Hosts and clients use the agent token; dashboards and CLI reads use the admin token.
- Config files are written with restricted permissions on POSIX systems.
- The hub enforces request-size limits and caps the number of tracked nodes and clients in memory.
- Sunshine still needs its own permissions and pairing flow with Moonlight
- macOS VNC requires Screen Sharing or Remote Management to be enabled
- macOS screenshot capture may require Screen Recording permission for the host agent

The CLI surfaces these boundaries through `omv client doctor` and `omv host doctor` instead of pretending everything is finished when it is only installed.

## Service management

User-level services are supported on:

- macOS via `launchd`
- Linux via `systemd --user`

Commands:

```bash
omv hub start
omv hub stop
omv hub service-uninstall
omv client start
omv client stop
omv client service-uninstall
omv host start
omv host stop
omv host service-uninstall
```

## Development

End users do not need Node or `pnpm`. They only need `uv tool install omv`.

For repo development:

```bash
uv sync
cd frontend && pnpm install
cd frontend && pnpm build
uv run --with pytest --with httpx pytest
```

## Verification

Useful smoke checks:

```bash
omv --version
omv status
omv capabilities
omv hub doctor
omv client doctor
omv host report --dry-run
```
