"""Configuration loader for SRCMS Data Uploader.

Reads the YAML config file that maps remote app names to their upload paths on
the Android device.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

import yaml


# Default config file location: next to the installed package, or in the
# current working directory.
DEFAULT_CONFIG_PATHS = [
    Path(__file__).parent.parent.parent / "config.yaml",  # repo / development layout
    Path(os.getcwd()) / "config.yaml",  # cwd fallback
    Path(__file__).parent / "config.yaml",  # bundled (PyInstaller)
]


class RemoteApp:
    """Represents a remote application / upload category."""

    def __init__(self, name: str, path: str) -> None:
        if not name or not name.strip():
            raise ValueError("RemoteApp name must not be empty")
        if not path or not path.strip():
            raise ValueError("RemoteApp path must not be empty")
        self.name: str = name.strip()
        self.path: str = path.strip()

    def __repr__(self) -> str:  # pragma: no cover
        return f"RemoteApp(name={self.name!r}, path={self.path!r})"


def load_config(config_path: str | Path | None = None) -> List[RemoteApp]:
    """Load and return the list of remote apps from the YAML config file.

    Parameters
    ----------
    config_path:
        Path to the YAML config file.  When *None* the function searches the
        :data:`DEFAULT_CONFIG_PATHS` list and uses the first file that exists.

    Returns
    -------
    List[RemoteApp]
        Ordered list of configured remote apps.

    Raises
    ------
    FileNotFoundError
        When no config file can be found.
    ValueError
        When the config file is malformed.
    """
    if config_path is not None:
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
    else:
        path = next((p for p in DEFAULT_CONFIG_PATHS if p.exists()), None)
        if path is None:
            searched = ", ".join(str(p) for p in DEFAULT_CONFIG_PATHS)
            raise FileNotFoundError(
                f"No config file found. Searched: {searched}. "
                "Create a config.yaml in the working directory."
            )

    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if not isinstance(data, dict) or "apps" not in data:
        raise ValueError(
            f"Config file {path} must contain a top-level 'apps' list."
        )

    apps_data = data["apps"]
    if not isinstance(apps_data, list) or len(apps_data) == 0:
        raise ValueError(
            f"Config file {path}: 'apps' must be a non-empty list."
        )

    apps: List[RemoteApp] = []
    for i, entry in enumerate(apps_data):
        if not isinstance(entry, dict):
            raise ValueError(
                f"Config file {path}: apps[{i}] must be a mapping with 'name' and 'path'."
            )
        missing = [k for k in ("name", "path") if k not in entry]
        if missing:
            raise ValueError(
                f"Config file {path}: apps[{i}] is missing required keys: {missing}."
            )
        apps.append(RemoteApp(name=str(entry["name"]), path=str(entry["path"])))

    return apps
