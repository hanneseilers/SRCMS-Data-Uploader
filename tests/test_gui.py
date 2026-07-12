"""Tests for srcms_uploader.gui module."""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from srcms_uploader.config import RemoteApp


@pytest.fixture
def mock_tk():
    """Patch tkinter so tests run without a display."""
    with patch("srcms_uploader.gui.tk") as mock_tk_mod:
        # Make Tk() return a mock root
        mock_root = MagicMock()
        mock_tk_mod.Tk.return_value = mock_root
        # StringVar and Listbox need to return mocks
        mock_tk_mod.StringVar.return_value = MagicMock()
        mock_tk_mod.Listbox.return_value = MagicMock()
        mock_tk_mod.END = "end"
        yield mock_tk_mod, mock_root


@pytest.fixture
def config_file(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        textwrap.dedent(
            """
            apps:
              - name: "SRCMS"
                path: "/sdcard/SRCMS/uploads"
              - name: "Music"
                path: "/sdcard/Music/Uploads"
            """
        )
    )
    return cfg


class TestUploaderApp:
    @patch("srcms_uploader.gui.ttk")
    def test_creates_window(self, mock_ttk, mock_tk, config_file):
        """UploaderApp should create a Tk root window."""
        mock_tk_mod, mock_root = mock_tk
        from srcms_uploader.gui import UploaderApp

        app = UploaderApp(config_path=str(config_file))
        mock_tk_mod.Tk.assert_called_once()

    @patch("srcms_uploader.gui.ttk")
    def test_loads_apps_from_config(self, mock_ttk, mock_tk, config_file):
        """UploaderApp should load apps from config."""
        mock_tk_mod, mock_root = mock_tk
        from srcms_uploader.gui import UploaderApp

        app = UploaderApp(config_path=str(config_file))
        assert len(app._apps) == 2
        assert app._apps[0].name == "SRCMS"
        assert app._apps[1].name == "Music"

    @patch("srcms_uploader.gui.ttk")
    @patch("srcms_uploader.gui.messagebox.showerror")
    def test_handles_missing_config(self, mock_showerror, mock_ttk, mock_tk, tmp_path):
        """UploaderApp should show error if config is missing."""
        mock_tk_mod, mock_root = mock_tk
        from srcms_uploader.gui import UploaderApp

        app = UploaderApp(config_path=str(tmp_path / "nonexistent.yaml"))
        mock_showerror.assert_called_once()
        assert app._apps == []

    @patch("srcms_uploader.gui.ttk")
    def test_run_calls_mainloop(self, mock_ttk, mock_tk, config_file):
        """run() should call mainloop on the Tk root."""
        mock_tk_mod, mock_root = mock_tk
        from srcms_uploader.gui import UploaderApp

        app = UploaderApp(config_path=str(config_file))
        app.run()
        mock_root.mainloop.assert_called_once()
