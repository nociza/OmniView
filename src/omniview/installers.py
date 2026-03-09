from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess
import sys


@dataclass(frozen=True, slots=True)
class ToolStatus:
    name: str
    installed: bool
    detail: str


class ToolInstallerError(RuntimeError):
    pass


def detect_tool(name: str) -> ToolStatus:
    lower = name.lower()
    if lower == "moonlight":
        candidates = [
            shutil.which("moonlight"),
            shutil.which("moonlight-qt"),
            "/Applications/Moonlight.app/Contents/MacOS/Moonlight" if sys.platform == "darwin" else None,
        ]
        for candidate in candidates:
            if candidate:
                return ToolStatus(name="moonlight", installed=True, detail=f"Found at {candidate}")
        return ToolStatus(name="moonlight", installed=False, detail="Moonlight is not installed.")

    if lower == "sunshine":
        candidates = [
            shutil.which("sunshine"),
            "/Applications/Sunshine.app/Contents/MacOS/sunshine" if sys.platform == "darwin" else None,
        ]
        for candidate in candidates:
            if candidate:
                return ToolStatus(name="sunshine", installed=True, detail=f"Found at {candidate}")
        return ToolStatus(name="sunshine", installed=False, detail="Sunshine is not installed.")

    if lower == "tailscale":
        candidate = shutil.which("tailscale")
        if candidate:
            return ToolStatus(name="tailscale", installed=True, detail=f"Found at {candidate}")
        return ToolStatus(name="tailscale", installed=False, detail="Tailscale is not installed.")

    raise ToolInstallerError(f"Unknown tool '{name}'.")


def install_tool(name: str) -> str:
    lower = name.lower()
    if sys.platform == "darwin":
        return _install_macos(lower)
    if sys.platform.startswith("win"):
        return _install_windows(lower)
    if sys.platform.startswith("linux"):
        return _install_linux(lower)
    raise ToolInstallerError(f"{name} installation is not implemented for this platform.")


def _install_macos(tool: str) -> str:
    brew = shutil.which("brew")
    if not brew:
        raise ToolInstallerError("Secure automated installation on macOS requires Homebrew.")
    formulas = {
        "moonlight": ["install", "--cask", "moonlight"],
        "sunshine": ["tap", "LizardByte/homebrew"],
        "tailscale": ["install", "tailscale"],
    }
    if tool == "sunshine":
        subprocess.run([brew, *formulas["sunshine"]], check=True)
        subprocess.run([brew, "install", "sunshine"], check=True)
        return "Installed Sunshine with Homebrew."
    if tool == "moonlight":
        subprocess.run([brew, *formulas["moonlight"]], check=True)
        return "Installed Moonlight with Homebrew."
    if tool == "tailscale":
        subprocess.run([brew, *formulas["tailscale"]], check=True)
        return "Installed Tailscale with Homebrew."
    raise ToolInstallerError(f"Unknown tool '{tool}'.")


def _install_windows(tool: str) -> str:
    winget = shutil.which("winget")
    if not winget:
        raise ToolInstallerError("Secure automated installation on Windows requires winget.")
    ids = {
        "moonlight": "MoonlightGameStreamingProject.Moonlight",
        "sunshine": "LizardByte.Sunshine",
        "tailscale": "Tailscale.Tailscale",
    }
    package_id = ids.get(tool)
    if not package_id:
        raise ToolInstallerError(f"Unknown tool '{tool}'.")
    subprocess.run(
        [winget, "install", "--accept-package-agreements", "--accept-source-agreements", package_id],
        check=True,
    )
    return f"Installed {tool.title()} with winget."


def _install_linux(tool: str) -> str:
    for manager, args in _linux_install_commands(tool):
        binary = shutil.which(manager)
        if not binary:
            continue
        subprocess.run([binary, *args], check=True)
        return f"Installed {tool.title()} with {manager}."
    raise ToolInstallerError(
        "Secure automated installation on Linux requires a supported system package manager. "
        "Supported managers: apt-get, dnf, pacman."
    )


def _linux_install_commands(tool: str) -> list[tuple[str, list[str]]]:
    packages = {
        "moonlight": {
            "apt-get": ["install", "-y", "moonlight-qt"],
            "dnf": ["install", "-y", "moonlight-qt"],
            "pacman": ["-S", "--noconfirm", "moonlight-qt"],
        },
        "sunshine": {
            "apt-get": ["install", "-y", "sunshine"],
            "dnf": ["install", "-y", "sunshine"],
            "pacman": ["-S", "--noconfirm", "sunshine"],
        },
        "tailscale": {
            "apt-get": ["install", "-y", "tailscale"],
            "dnf": ["install", "-y", "tailscale"],
            "pacman": ["-S", "--noconfirm", "tailscale"],
        },
    }
    selected = packages.get(tool)
    if not selected:
        raise ToolInstallerError(f"Unknown tool '{tool}'.")
    return list(selected.items())
