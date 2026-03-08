from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from urllib import request

from omniview.paths import local_bin_dir


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
            str(local_bin_dir() / "moonlight") if not sys.platform.startswith("win") else None,
        ]
        for candidate in candidates:
            if candidate and Path(candidate).exists():
                return ToolStatus(name="moonlight", installed=True, detail=f"Found at {candidate}")
        return ToolStatus(name="moonlight", installed=False, detail="Moonlight is not installed.")

    if lower == "sunshine":
        candidates = [
            shutil.which("sunshine"),
            "/Applications/Sunshine.app/Contents/MacOS/sunshine" if sys.platform == "darwin" else None,
            str(local_bin_dir() / "sunshine") if not sys.platform.startswith("win") else None,
        ]
        for candidate in candidates:
            if candidate and Path(candidate).exists():
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
    if lower == "moonlight":
        return _install_moonlight()
    if lower == "sunshine":
        return _install_sunshine()
    if lower == "tailscale":
        return _install_tailscale()
    raise ToolInstallerError(f"Unknown tool '{name}'.")


def _install_moonlight() -> str:
    if sys.platform == "darwin":
        if shutil.which("brew"):
            subprocess.run(["brew", "install", "--cask", "moonlight"], check=True)
            return "Installed Moonlight with Homebrew."
        asset_url = _latest_release_asset("moonlight-stream/moonlight-qt", lambda asset: asset["name"].endswith(".dmg"))
        dmg = _download(asset_url)
        mount_point = Path(tempfile.mkdtemp(prefix="omv-moonlight-"))
        subprocess.run(["hdiutil", "attach", str(dmg), "-mountpoint", str(mount_point), "-nobrowse"], check=True)
        try:
            app = next(mount_point.glob("*.app"))
            subprocess.run(["cp", "-R", str(app), "/Applications/"] , check=True)
        finally:
            subprocess.run(["hdiutil", "detach", str(mount_point)], check=False)
        return "Installed Moonlight from the latest GitHub release."

    if sys.platform.startswith("linux"):
        asset_url = _latest_release_asset("moonlight-stream/moonlight-qt", lambda asset: asset["name"].endswith(".AppImage"))
        target = local_bin_dir() / "moonlight"
        _download_to(asset_url, target)
        target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        return f"Installed Moonlight AppImage to {target}."

    if sys.platform.startswith("win"):
        if shutil.which("winget"):
            subprocess.run(["winget", "install", "--accept-package-agreements", "--accept-source-agreements", "MoonlightGameStreamingProject.Moonlight"], check=True)
            return "Installed Moonlight with winget."
        asset_url = _latest_release_asset("moonlight-stream/moonlight-qt", lambda asset: asset["name"].endswith(".exe"))
        installer = _download(asset_url)
        subprocess.run([str(installer)], check=True)
        return "Launched the Moonlight installer."

    raise ToolInstallerError("Moonlight installation is not implemented for this platform.")


def _install_sunshine() -> str:
    if sys.platform == "darwin":
        if not shutil.which("brew"):
            raise ToolInstallerError("Sunshine installation on macOS currently requires Homebrew.")
        subprocess.run(["brew", "tap", "LizardByte/homebrew"], check=True)
        subprocess.run(["brew", "install", "sunshine"], check=True)
        return "Installed Sunshine with Homebrew."

    if sys.platform.startswith("linux"):
        asset_url = _latest_release_asset("LizardByte/Sunshine", lambda asset: asset["name"] == "sunshine.AppImage")
        target = local_bin_dir() / "sunshine"
        _download_to(asset_url, target)
        target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        return f"Installed Sunshine AppImage to {target}."

    if sys.platform.startswith("win"):
        if shutil.which("winget"):
            subprocess.run(["winget", "install", "--accept-package-agreements", "--accept-source-agreements", "LizardByte.Sunshine"], check=True)
            return "Installed Sunshine with winget."
        asset_url = _latest_release_asset("LizardByte/Sunshine", lambda asset: asset["name"].endswith("installer.exe"))
        installer = _download(asset_url)
        subprocess.run([str(installer)], check=True)
        return "Launched the Sunshine installer."

    raise ToolInstallerError("Sunshine installation is not implemented for this platform.")


def _install_tailscale() -> str:
    if sys.platform == "darwin":
        if shutil.which("brew"):
            subprocess.run(["brew", "install", "tailscale"], check=True)
            return "Installed Tailscale with Homebrew."
        raise ToolInstallerError("Tailscale installation on macOS currently requires Homebrew.")

    if sys.platform.startswith("linux"):
        subprocess.run(["sh", "-c", "curl -fsSL https://tailscale.com/install.sh | sh"], check=True)
        return "Installed Tailscale with the official install script."

    if sys.platform.startswith("win"):
        if shutil.which("winget"):
            subprocess.run(["winget", "install", "--accept-package-agreements", "--accept-source-agreements", "Tailscale.Tailscale"], check=True)
            return "Installed Tailscale with winget."
        raise ToolInstallerError("Tailscale installation on Windows currently requires winget.")

    raise ToolInstallerError("Tailscale installation is not implemented for this platform.")


def _latest_release_asset(repo: str, predicate) -> str:
    api_url = f"https://api.github.com/repos/{repo}/releases/latest"
    with request.urlopen(api_url) as response:
        payload = json.load(response)
    for asset in payload.get("assets", []):
        if predicate(asset):
            return asset["browser_download_url"]
    raise ToolInstallerError(f"Unable to find a compatible asset in the latest release of {repo}.")


def _download(url: str) -> Path:
    target = Path(tempfile.mkdtemp(prefix="omv-download-")) / Path(url).name
    _download_to(url, target)
    return target


def _download_to(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with request.urlopen(url) as response, target.open("wb") as handle:
        shutil.copyfileobj(response, handle)
