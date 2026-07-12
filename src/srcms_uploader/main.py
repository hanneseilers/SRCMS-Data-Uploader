"""SRCMS Data Uploader – interactive command-line application.

Workflow:
  1. Ask the user for the remote Android device IP address.
  2. Ask for one or more local files / directories to upload.
  3. Show the list of remote apps from the config and ask the user to choose one.
  4. Connect via ADB over WiFi and push the selected paths to the remote location.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Optional

from .adb import AdbUploader, ADB_DEFAULT_PORT
from .config import RemoteApp, load_config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _prompt(message: str, default: Optional[str] = None) -> str:
    """Print *message*, read a line from stdin, and return the stripped value.

    Raises
    ------
    EOFError / KeyboardInterrupt
        Propagated so the caller can handle graceful exit.
    """
    suffix = f" [{default}]" if default else ""
    value = input(f"{message}{suffix}: ").strip()
    if not value and default is not None:
        return default
    return value


def ask_remote_ip() -> str:
    """Interactively ask the user for the remote Android device IP address."""
    while True:
        ip = _prompt("Enter the remote Android device IP address")
        if ip:
            return ip
        print("  ✗ IP address must not be empty. Please try again.")


def ask_local_paths() -> List[Path]:
    """Interactively ask the user for one or more local files / directories.

    The user can keep entering paths until they submit an empty line.
    """
    print(
        "\nEnter the local files or directories to upload."
        " Press ENTER on an empty line when done."
    )
    paths: List[Path] = []
    index = 1
    while True:
        raw = _prompt(f"  Path {index} (or ENTER to finish)").strip()
        if not raw:
            if not paths:
                print("  ✗ At least one path is required.")
                continue
            break
        p = Path(raw)
        if not p.exists():
            print(f"  ✗ '{raw}' does not exist. Please enter a valid path.")
            continue
        paths.append(p)
        index += 1

    return paths


def ask_remote_app(apps: List[RemoteApp]) -> RemoteApp:
    """Interactively ask the user to choose a remote app from the config."""
    print("\nAvailable remote apps:")
    for i, app in enumerate(apps, start=1):
        print(f"  {i}) {app.name}  →  {app.path}")

    while True:
        raw = _prompt(f"Select remote app [1-{len(apps)}]")
        try:
            choice = int(raw)
            if 1 <= choice <= len(apps):
                return apps[choice - 1]
        except ValueError:
            pass
        print(f"  ✗ Please enter a number between 1 and {len(apps)}.")


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

def main(config_path: Optional[str] = None) -> int:
    """Run the interactive SRCMS Data Uploader.

    Parameters
    ----------
    config_path:
        Optional path to the YAML config file.  When *None* the default search
        paths are used (see :func:`srcms_uploader.config.load_config`).

    Returns
    -------
    int
        Exit code – 0 on success, non-zero on error.
    """
    print("=" * 60)
    print("  SRCMS Data Uploader")
    print("=" * 60)
    print()

    # --- Load configuration ------------------------------------------------
    try:
        apps = load_config(config_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[ERROR] Could not load configuration: {exc}", file=sys.stderr)
        return 1

    # --- Gather user inputs ------------------------------------------------
    try:
        remote_ip = ask_remote_ip()
        local_paths = ask_local_paths()
        remote_app = ask_remote_app(apps)
    except (EOFError, KeyboardInterrupt):
        print("\nAborted by user.")
        return 1

    # --- Summary -----------------------------------------------------------
    print()
    print("Upload summary")
    print("-" * 40)
    print(f"  Device IP   : {remote_ip}:{ADB_DEFAULT_PORT}")
    print(f"  Remote app  : {remote_app.name}")
    print(f"  Destination : {remote_app.path}")
    print(f"  Files/dirs  : {len(local_paths)}")
    for p in local_paths:
        print(f"    • {p}")
    print()

    try:
        confirm = _prompt("Proceed with upload? [y/N]", default="N").lower()
    except (EOFError, KeyboardInterrupt):
        print("\nAborted by user.")
        return 1

    if confirm not in ("y", "yes"):
        print("Upload cancelled.")
        return 0

    # --- Upload ------------------------------------------------------------
    uploader = AdbUploader(host=remote_ip)
    try:
        uploader.connect()
        uploader.push_many(local_paths, remote_app.path)
        print()
        print("✓ All files uploaded successfully.")
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"\n[ERROR] {exc}", file=sys.stderr)
        return 1
    finally:
        uploader.disconnect()

    return 0


if __name__ == "__main__":
    sys.exit(main())
