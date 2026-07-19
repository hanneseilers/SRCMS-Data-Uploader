"""ADB-based file uploader for SRCMS Data Uploader.

Handles connecting to a remote Android device over WiFi (TCP/IP) and pushing
local files and directories to a specified path on the device.
"""

from __future__ import annotations

import shutil
import shlex
import subprocess
import re
from pathlib import Path
from typing import List, Tuple


# Default ADB TCP port used by Android devices
ADB_DEFAULT_PORT = 5555


def _find_adb() -> str:
    """Return the path to the *adb* executable.

    Raises
    ------
    FileNotFoundError
        When *adb* cannot be found on the system PATH.
    """
    adb = shutil.which("adb")
    if adb is None:
        raise FileNotFoundError(
            "adb executable not found on PATH. "
            "Install Android Platform Tools and make sure 'adb' is available."
        )
    return adb


def _run(args: List[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a subprocess command and return the result."""
    return subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=check,
    )


_LS_L_PATTERN = re.compile(
    r"^(?P<mode>\S+)"
    r"(?:\s+(?P<links>\d+))?"
    r"\s+(?P<user>\S+)"
    r"\s+(?P<group>\S+)"
    r"(?:\s+(?P<size>\d+))?"
    r"\s+(?P<date>\d{4}-\d{2}-\d{2})"
    r"\s+(?P<time>\d{2}:\d{2})"
    r"\s+(?P<name>.+)$"
)


class AdbUploader:
    """Manages an ADB-over-WiFi connection and file uploads to an Android device.

    Parameters
    ----------
    host:
        IP address of the remote Android device.
    port:
        TCP port to connect to (default: 5555).
    """

    def __init__(self, host: str, port: int = ADB_DEFAULT_PORT) -> None:
        self.host = host.strip()
        self.port = port
        self._adb = _find_adb()
        self._connected = False

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Connect to the remote Android device via ADB over TCP/IP.

        Raises
        ------
        RuntimeError
            When ADB reports that the connection failed.
        """
        target = f"{self.host}:{self.port}"
        result = _run([self._adb, "connect", target], check=False)
        output = (result.stdout + result.stderr).strip()
        if result.returncode != 0 or "failed" in output.lower() or "error" in output.lower():
            raise RuntimeError(
                f"Failed to connect to {target} via ADB.\n"
                f"ADB output: {output}\n"
                "Make sure:\n"
                "  • The Android device is on the same network\n"
                "  • ADB over WiFi (TCP/IP) is enabled on the device\n"
                "  • The IP address is correct"
            )
        self._connected = True
        print(f"[ADB] Connected to {target}")

    def disconnect(self) -> None:
        """Disconnect from the remote Android device."""
        if not self._connected:
            return
        target = f"{self.host}:{self.port}"
        _run([self._adb, "disconnect", target], check=False)
        self._connected = False
        print(f"[ADB] Disconnected from {target}")

    # ------------------------------------------------------------------
    # File upload
    # ------------------------------------------------------------------

    def push(self, local_path: str | Path, remote_dir: str) -> None:
        """Push a local file or directory to *remote_dir* on the device.

        Parameters
        ----------
        local_path:
            Path to the local file or directory.
        remote_dir:
            Absolute path to the destination directory on the Android device.

        Raises
        ------
        FileNotFoundError
            When *local_path* does not exist.
        RuntimeError
            When the ADB push command fails.
        """
        local = Path(local_path)
        if not local.exists():
            raise FileNotFoundError(f"Local path does not exist: {local}")

        target = f"{self.host}:{self.port}"
        # Ensure trailing slash so adb push places the item *inside* remote_dir
        dest = remote_dir.rstrip("/") + "/"

        print(f"[ADB] Pushing '{local}' → '{dest}' on {target} …")
        result = _run(
            [self._adb, "-s", target, "push", str(local), dest],
            check=False,
        )
        output = (result.stdout + result.stderr).strip()
        if result.returncode != 0:
            raise RuntimeError(
                f"ADB push failed for '{local}'.\nADB output: {output}"
            )
        print(f"[ADB] ✓ Pushed '{local}'")

    def push_many(self, local_paths: List[str | Path], remote_dir: str) -> None:
        """Push multiple local files or directories to *remote_dir*.

        Each item is pushed individually so that a failure on one item does not
        silently skip the remaining items.

        Parameters
        ----------
        local_paths:
            List of local file/directory paths.
        remote_dir:
            Absolute path to the destination directory on the Android device.
        """
        for path in local_paths:
            self.push(path, remote_dir)

    # ------------------------------------------------------------------
    # Remote file management
    # ------------------------------------------------------------------

    def list_directory(self, remote_dir: str) -> List[Tuple[str, bool]]:
        """List entries in a remote directory.

        Returns
        -------
        list[tuple[str, bool]]
            Tuples of (entry_name, is_directory). Directory names are returned
            without trailing slashes.
        """
        target = f"{self.host}:{self.port}"
        command = f"ls -l {shlex.quote(remote_dir)}"
        result = _run(
            [self._adb, "-s", target, "shell", command],
            check=False,
        )
        output = (result.stdout + result.stderr).strip()
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to list remote directory '{remote_dir}'.\nADB output: {output}"
            )

        entries: List[Tuple[str, bool]] = []
        for raw_line in output.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("total "):
                continue
            match = _LS_L_PATTERN.match(line)
            if match is None:
                continue
            is_dir = match.group("mode").startswith("d")
            name = match.group("name").strip()
            entries.append((name, is_dir))
        return entries

    def delete_remote_path(self, remote_path: str) -> None:
        """Delete a remote file or directory recursively."""
        target = f"{self.host}:{self.port}"
        command = f"rm -rf -- {shlex.quote(remote_path)}"
        result = _run(
            [self._adb, "-s", target, "shell", command],
            check=False,
        )
        output = (result.stdout + result.stderr).strip()
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to delete remote path '{remote_path}'.\nADB output: {output}"
            )

    def pull(self, remote_path: str, local_dir: str | Path) -> None:
        """Download a remote file to a local directory."""
        destination = Path(local_dir)
        if not destination.exists():
            raise FileNotFoundError(f"Local directory does not exist: {destination}")
        if not destination.is_dir():
            raise NotADirectoryError(f"Local path is not a directory: {destination}")

        target = f"{self.host}:{self.port}"
        result = _run(
            [self._adb, "-s", target, "pull", remote_path, str(destination)],
            check=False,
        )
        output = (result.stdout + result.stderr).strip()
        if result.returncode != 0:
            raise RuntimeError(
                f"ADB pull failed for '{remote_path}'.\nADB output: {output}"
            )
