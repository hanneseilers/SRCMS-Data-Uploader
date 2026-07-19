"""Tests for srcms_uploader.adb module."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from srcms_uploader.adb import AdbUploader, ADB_DEFAULT_PORT


@pytest.fixture()
def uploader():
    """Return an AdbUploader with adb discovery mocked out."""
    with patch("srcms_uploader.adb._find_adb", return_value="/usr/bin/adb"):
        yield AdbUploader(host="192.168.1.100")


# ---------------------------------------------------------------------------
# _find_adb
# ---------------------------------------------------------------------------

class TestFindAdb:
    def test_found(self):
        with patch("shutil.which", return_value="/usr/bin/adb"):
            from srcms_uploader.adb import _find_adb
            assert _find_adb() == "/usr/bin/adb"

    def test_not_found(self):
        with patch("shutil.which", return_value=None):
            from srcms_uploader.adb import _find_adb
            with pytest.raises(FileNotFoundError, match="adb"):
                _find_adb()


# ---------------------------------------------------------------------------
# AdbUploader.connect
# ---------------------------------------------------------------------------

class TestConnect:
    def _make_result(self, returncode=0, stdout="connected", stderr=""):
        result = MagicMock(spec=subprocess.CompletedProcess)
        result.returncode = returncode
        result.stdout = stdout
        result.stderr = stderr
        return result

    def test_connect_success(self, uploader):
        with patch("srcms_uploader.adb._run", return_value=self._make_result()) as mock_run:
            uploader.connect()
            assert uploader._connected is True
            mock_run.assert_called_once_with(
                ["/usr/bin/adb", "connect", f"192.168.1.100:{ADB_DEFAULT_PORT}"],
                check=False,
            )

    def test_connect_failure_returncode(self, uploader):
        with patch(
            "srcms_uploader.adb._run",
            return_value=self._make_result(returncode=1, stderr="failed to connect"),
        ):
            with pytest.raises(RuntimeError, match="Failed to connect"):
                uploader.connect()
            assert uploader._connected is False

    def test_connect_failure_output_contains_failed(self, uploader):
        with patch(
            "srcms_uploader.adb._run",
            return_value=self._make_result(returncode=0, stdout="failed to connect"),
        ):
            with pytest.raises(RuntimeError, match="Failed to connect"):
                uploader.connect()

    def test_connect_failure_output_contains_error(self, uploader):
        with patch(
            "srcms_uploader.adb._run",
            return_value=self._make_result(returncode=0, stdout="error: device not found"),
        ):
            with pytest.raises(RuntimeError, match="Failed to connect"):
                uploader.connect()


# ---------------------------------------------------------------------------
# AdbUploader.disconnect
# ---------------------------------------------------------------------------

class TestDisconnect:
    def test_disconnect_when_connected(self, uploader):
        uploader._connected = True
        with patch("srcms_uploader.adb._run") as mock_run:
            uploader.disconnect()
            assert uploader._connected is False
            mock_run.assert_called_once()

    def test_disconnect_when_not_connected(self, uploader):
        uploader._connected = False
        with patch("srcms_uploader.adb._run") as mock_run:
            uploader.disconnect()
            mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# AdbUploader.push
# ---------------------------------------------------------------------------

class TestPush:
    def _make_result(self, returncode=0, stdout="1 file pushed", stderr=""):
        result = MagicMock(spec=subprocess.CompletedProcess)
        result.returncode = returncode
        result.stdout = stdout
        result.stderr = stderr
        return result

    def test_push_file_success(self, uploader, tmp_path):
        local_file = tmp_path / "data.txt"
        local_file.write_text("content")
        with patch("srcms_uploader.adb._run", return_value=self._make_result()) as mock_run:
            uploader.push(local_file, "/sdcard/SRCMS/uploads")
            mock_run.assert_called_once_with(
                [
                    "/usr/bin/adb",
                    "-s",
                    f"192.168.1.100:{ADB_DEFAULT_PORT}",
                    "push",
                    str(local_file),
                    "/sdcard/SRCMS/uploads/",
                ],
                check=False,
            )

    def test_push_appends_trailing_slash(self, uploader, tmp_path):
        local_file = tmp_path / "data.txt"
        local_file.write_text("content")
        with patch("srcms_uploader.adb._run", return_value=self._make_result()) as mock_run:
            uploader.push(local_file, "/sdcard/SRCMS/uploads/")  # already has slash
            args = mock_run.call_args[0][0]
            assert args[-1] == "/sdcard/SRCMS/uploads/"

    def test_push_nonexistent_local_raises(self, uploader, tmp_path):
        with pytest.raises(FileNotFoundError, match="does not exist"):
            uploader.push(tmp_path / "ghost.txt", "/sdcard/SRCMS/uploads")

    def test_push_failure_raises(self, uploader, tmp_path):
        local_file = tmp_path / "data.txt"
        local_file.write_text("content")
        with patch(
            "srcms_uploader.adb._run",
            return_value=self._make_result(returncode=1, stderr="push failed"),
        ):
            with pytest.raises(RuntimeError, match="ADB push failed"):
                uploader.push(local_file, "/sdcard/SRCMS/uploads")


# ---------------------------------------------------------------------------
# AdbUploader.push_many
# ---------------------------------------------------------------------------

class TestPushMany:
    def test_push_many_calls_push_for_each(self, uploader, tmp_path):
        files = []
        for name in ("a.txt", "b.txt", "c.txt"):
            f = tmp_path / name
            f.write_text("data")
            files.append(f)

        with patch.object(uploader, "push") as mock_push:
            uploader.push_many(files, "/sdcard/SRCMS/uploads")
            assert mock_push.call_count == 3
            mock_push.assert_any_call(files[0], "/sdcard/SRCMS/uploads")
            mock_push.assert_any_call(files[1], "/sdcard/SRCMS/uploads")
            mock_push.assert_any_call(files[2], "/sdcard/SRCMS/uploads")

    def test_push_many_stops_on_first_error(self, uploader, tmp_path):
        files = [tmp_path / "a.txt", tmp_path / "b.txt"]
        for f in files:
            f.write_text("data")

        def side_effect(path, remote):
            raise RuntimeError("push failed")

        with patch.object(uploader, "push", side_effect=side_effect):
            with pytest.raises(RuntimeError):
                uploader.push_many(files, "/sdcard/path")


class TestRemoteFileManagement:
    def _make_result(self, returncode=0, stdout="", stderr=""):
        result = MagicMock(spec=subprocess.CompletedProcess)
        result.returncode = returncode
        result.stdout = stdout
        result.stderr = stderr
        return result

    def test_list_directory_success(self, uploader):
        with patch(
            "srcms_uploader.adb._run",
            return_value=self._make_result(
                stdout="total 2\n-rw-rw---- 1 u0_a130 sdcard_rw 0 2024-12-20 14:26 alpha.txt\n"
                       "drwxrwx--x 1 u0_a130 sdcard_rw 0 2024-12-20 14:26 subdir\n"
            ),
        ) as mock_run:
            entries = uploader.list_directory("/sdcard/SRCMS/uploads")
            assert entries == [("alpha.txt", False), ("subdir", True)]
            mock_run.assert_called_once_with(
                [
                    "/usr/bin/adb",
                    "-s",
                    f"192.168.1.100:{ADB_DEFAULT_PORT}",
                    "shell",
                    "ls -l /sdcard/SRCMS/uploads",
                ],
                check=False,
            )

    def test_list_directory_failure_raises(self, uploader):
        with patch(
            "srcms_uploader.adb._run",
            return_value=self._make_result(returncode=1, stderr="Permission denied"),
        ):
            with pytest.raises(RuntimeError, match="Failed to list remote directory"):
                uploader.list_directory("/sdcard/SRCMS/uploads")

    def test_delete_remote_path_success(self, uploader):
        with patch("srcms_uploader.adb._run", return_value=self._make_result()) as mock_run:
            uploader.delete_remote_path("/sdcard/SRCMS/uploads/stale.txt")
            mock_run.assert_called_once_with(
                [
                    "/usr/bin/adb",
                    "-s",
                    f"192.168.1.100:{ADB_DEFAULT_PORT}",
                    "shell",
                    "rm -rf -- /sdcard/SRCMS/uploads/stale.txt",
                ],
                check=False,
            )

    def test_delete_remote_path_failure_raises(self, uploader):
        with patch(
            "srcms_uploader.adb._run",
            return_value=self._make_result(returncode=1, stderr="No such file"),
        ):
            with pytest.raises(RuntimeError, match="Failed to delete remote path"):
                uploader.delete_remote_path("/sdcard/SRCMS/uploads/stale.txt")
