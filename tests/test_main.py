"""Tests for srcms_uploader.main module (interactive CLI)."""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from srcms_uploader.config import RemoteApp
from srcms_uploader.main import ask_local_paths, ask_remote_app, ask_remote_ip, main


# ---------------------------------------------------------------------------
# ask_remote_ip
# ---------------------------------------------------------------------------

class TestAskRemoteIp:
    def test_returns_valid_ip(self):
        with patch("builtins.input", return_value="192.168.1.100"):
            assert ask_remote_ip() == "192.168.1.100"

    def test_retries_on_empty_input(self):
        with patch("builtins.input", side_effect=["", "  ", "10.0.0.1"]):
            assert ask_remote_ip() == "10.0.0.1"


# ---------------------------------------------------------------------------
# ask_local_paths
# ---------------------------------------------------------------------------

class TestAskLocalPaths:
    def test_single_file(self, tmp_path):
        local_file = tmp_path / "file.txt"
        local_file.write_text("data")
        with patch("builtins.input", side_effect=[str(local_file), ""]):
            paths = ask_local_paths()
        assert paths == [local_file]

    def test_multiple_paths(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("a")
        f2.write_text("b")
        with patch("builtins.input", side_effect=[str(f1), str(f2), ""]):
            paths = ask_local_paths()
        assert paths == [f1, f2]

    def test_retries_on_nonexistent_path(self, tmp_path):
        real_file = tmp_path / "real.txt"
        real_file.write_text("data")
        with patch("builtins.input", side_effect=["/nonexistent/path", str(real_file), ""]):
            paths = ask_local_paths()
        assert paths == [real_file]

    def test_retries_when_no_path_given(self, tmp_path):
        real_file = tmp_path / "real.txt"
        real_file.write_text("data")
        # First empty press with no paths yet should prompt again
        with patch("builtins.input", side_effect=["", str(real_file), ""]):
            paths = ask_local_paths()
        assert paths == [real_file]


# ---------------------------------------------------------------------------
# ask_remote_app
# ---------------------------------------------------------------------------

class TestAskRemoteApp:
    def _apps(self):
        return [
            RemoteApp("SRCMS", "/sdcard/SRCMS"),
            RemoteApp("Music", "/sdcard/Music"),
        ]

    def test_valid_selection(self):
        with patch("builtins.input", return_value="1"):
            app = ask_remote_app(self._apps())
        assert app.name == "SRCMS"

    def test_second_option(self):
        with patch("builtins.input", return_value="2"):
            app = ask_remote_app(self._apps())
        assert app.name == "Music"

    def test_retries_on_out_of_range(self):
        with patch("builtins.input", side_effect=["0", "3", "99", "1"]):
            app = ask_remote_app(self._apps())
        assert app.name == "SRCMS"

    def test_retries_on_non_numeric(self):
        with patch("builtins.input", side_effect=["abc", "!", "1"]):
            app = ask_remote_app(self._apps())
        assert app.name == "SRCMS"


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

class TestMain:
    def _write_config(self, tmp_path: Path) -> Path:
        cfg = tmp_path / "config.yaml"
        cfg.write_text(
            textwrap.dedent(
                """
                apps:
                  - name: "SRCMS"
                    path: "/sdcard/SRCMS/uploads"
                """
            )
        )
        return cfg

    def test_happy_path(self, tmp_path):
        cfg = self._write_config(tmp_path)
        local_file = tmp_path / "data.txt"
        local_file.write_text("content")

        inputs = iter([
            "192.168.1.100",  # IP
            str(local_file),  # path 1
            "",               # done entering paths
            "1",              # select app
            "y",              # confirm
        ])

        mock_uploader = MagicMock()
        mock_uploader.__enter__ = MagicMock(return_value=mock_uploader)
        mock_uploader.__exit__ = MagicMock(return_value=False)

        with patch("builtins.input", side_effect=inputs), \
             patch("srcms_uploader.main.AdbUploader", return_value=mock_uploader):
            result = main(config_path=str(cfg))

        assert result == 0
        mock_uploader.connect.assert_called_once()
        mock_uploader.push_many.assert_called_once()
        mock_uploader.disconnect.assert_called_once()

    def test_user_cancels_at_confirm(self, tmp_path):
        cfg = self._write_config(tmp_path)
        local_file = tmp_path / "data.txt"
        local_file.write_text("content")

        inputs = iter([
            "192.168.1.100",
            str(local_file),
            "",
            "1",
            "n",  # cancel
        ])

        with patch("builtins.input", side_effect=inputs), \
             patch("srcms_uploader.main.AdbUploader") as mock_cls:
            result = main(config_path=str(cfg))

        assert result == 0
        mock_cls.return_value.connect.assert_not_called()

    def test_bad_config_path(self, tmp_path):
        result = main(config_path=str(tmp_path / "nonexistent.yaml"))
        assert result == 1

    def test_keyboard_interrupt_during_input(self, tmp_path):
        cfg = self._write_config(tmp_path)
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            result = main(config_path=str(cfg))
        assert result == 1

    def test_adb_connect_error(self, tmp_path):
        cfg = self._write_config(tmp_path)
        local_file = tmp_path / "data.txt"
        local_file.write_text("content")

        inputs = iter([
            "192.168.1.100",
            str(local_file),
            "",
            "1",
            "y",
        ])

        mock_uploader = MagicMock()
        mock_uploader.connect.side_effect = RuntimeError("connection refused")

        with patch("builtins.input", side_effect=inputs), \
             patch("srcms_uploader.main.AdbUploader", return_value=mock_uploader):
            result = main(config_path=str(cfg))

        assert result == 1
        mock_uploader.disconnect.assert_called_once()
