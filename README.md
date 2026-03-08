# OMV

OMV is a self-hosted control plane for personal machines. One CLI installs everything a user needs to run the three roles in the system:

- `hub`: the central FastAPI server and embedded web UI
- `client`: the native-client launcher that opens Moonlight, VNC, SSH, or browser fallbacks on the machine you are sitting at
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
omv hub init --host 0.0.0.0 --port 8000
omv hub start
```

Optional background service:

```bash
omv hub service-install
```

Open `http://127.0.0.1:8000` locally or the machine's overlay-network IP from another device.

### 2. Set up a native client

On any machine that should open native apps when you click `Launch` in the dashboard:

```bash
omv client init
omv client install moonlight
omv client start
```

Optional background service:

```bash
omv client service-install
```

If the hub and the viewing machine are the same box, run both `hub` and `client` there.

### 3. Set up a host

On each machine you want to monitor:

```bash
omv host init --hub-url http://YOUR-HUB:8000
omv host start
```

For Linux hosts that should stream over Moonlight:

```bash
omv host install sunshine
```

For a persistent agent:

```bash
omv host service-install
```

## Common workflows

### All-in-one machine

One machine can run both the hub and the native client:

```bash
omv hub init
omv client init
omv hub service-install
omv client service-install
```

### Check local status

```bash
omv status
```

Example output:

```text
hub:        configured=yes listen=0.0.0.0:8000 health=ok
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

### List nodes from the hub

```bash
omv nodes --base-url http://127.0.0.1:8000
```

### Launch a node from the terminal

```bash
omv launch atlas-bot-lab --base-url http://127.0.0.1:8000
```

### Dry-run a launch

```bash
omv launch atlas-bot-lab --base-url http://127.0.0.1:8000 --dry-run
```

## Config files

OMV writes role-specific config files under `~/.config/omv/` on macOS and Linux.

- `~/.config/omv/hub.toml`
- `~/.config/omv/client.toml`
- `~/.config/omv/host.toml`

Use the CLI to create them instead of hand-writing them:

```bash
omv hub init
omv client init
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
omv hub service-install
omv hub service-uninstall
omv client service-install
omv client service-uninstall
omv host service-install
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
