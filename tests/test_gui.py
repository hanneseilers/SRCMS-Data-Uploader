"""Tests for srcms_uploader.gui module."""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from srcms_uploader.config import RemoteApp


@pytest.fixture
def mock_tk():
    """Patch the gui module's tk import so tests run without a display."""
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

    @patch("srcms_uploader.gui.ttk")
    @patch("srcms_uploader.gui.AdbUploader")
    def test_refresh_remote_browser_lists_entries(self, mock_uploader_cls, mock_ttk, mock_tk, config_file):
        """refresh should list remote files/directories in the listbox."""
        from srcms_uploader.gui import UploaderApp

        app = UploaderApp(config_path=str(config_file))
        app._ip_var = MagicMock()
        app._ip_var.get.return_value = "192.168.1.5"
        app._app_var = MagicMock()
        app._app_var.get.return_value = "SRCMS"
        app._remote_listbox = MagicMock()
        app._remote_path_var = MagicMock()

        mock_uploader = mock_uploader_cls.return_value
        mock_uploader.list_directory.return_value = [("a.txt", False), ("docs", True)]

        app._refresh_remote_browser()

        mock_uploader.connect.assert_called_once()
        mock_uploader.list_directory.assert_called_once_with("/sdcard/SRCMS/uploads")
        app._remote_listbox.insert.assert_any_call("end", "a.txt")
        app._remote_listbox.insert.assert_any_call("end", "[DIR] docs")

    @patch("srcms_uploader.gui.ttk")
    @patch("srcms_uploader.gui.AdbUploader")
    def test_open_selected_remote_entry_changes_directory(self, mock_uploader_cls, mock_ttk, mock_tk, config_file):
        """open should move into selected remote subdirectory."""
        from srcms_uploader.gui import UploaderApp

        app = UploaderApp(config_path=str(config_file))
        app._ip_var = MagicMock()
        app._ip_var.get.return_value = "192.168.1.5"
        app._app_var = MagicMock()
        app._app_var.get.return_value = "SRCMS"
        app._remote_listbox = MagicMock()
        app._remote_listbox.curselection.return_value = (0,)
        app._remote_path_var = MagicMock()
        app._remote_entries = [("docs", True)]
        app._current_remote_dir = "/sdcard/SRCMS/uploads"

        mock_uploader = mock_uploader_cls.return_value
        mock_uploader.list_directory.return_value = []

        app._open_selected_remote_entry()

        assert app._current_remote_dir == "/sdcard/SRCMS/uploads/docs"
        mock_uploader.list_directory.assert_called_once_with("/sdcard/SRCMS/uploads/docs")

    @patch("srcms_uploader.gui.ttk")
    @patch("srcms_uploader.gui.messagebox.showinfo")
    @patch("srcms_uploader.gui.messagebox.askyesno", return_value=True)
    @patch("srcms_uploader.gui.AdbUploader")
    def test_delete_selected_remote_entry_calls_adb_delete(
        self, mock_uploader_cls, mock_askyesno, mock_showinfo, mock_ttk, mock_tk, config_file
    ):
        """delete should call adb deletion for the selected remote item."""
        from srcms_uploader.gui import UploaderApp

        app = UploaderApp(config_path=str(config_file))
        app._ip_var = MagicMock()
        app._ip_var.get.return_value = "192.168.1.5"
        app._app_var = MagicMock()
        app._app_var.get.return_value = "SRCMS"
        app._remote_listbox = MagicMock()
        app._remote_listbox.curselection.return_value = (0,)
        app._remote_path_var = MagicMock()
        app._remote_entries = [("old", True)]
        app._current_remote_dir = "/sdcard/SRCMS/uploads"

        mock_uploader = mock_uploader_cls.return_value
        mock_uploader.list_directory.return_value = []

        app._delete_selected_remote_entry()

        mock_uploader.delete_remote_path.assert_called_once_with("/sdcard/SRCMS/uploads/old")

    @patch("srcms_uploader.gui.ttk")
    @patch("srcms_uploader.gui.AdbUploader")
    def test_connect_and_browse_resets_to_app_root(self, mock_uploader_cls, mock_ttk, mock_tk, config_file):
        """connect_and_browse should always start at the app root path."""
        from srcms_uploader.gui import UploaderApp

        app = UploaderApp(config_path=str(config_file))
        app._ip_var = MagicMock()
        app._ip_var.get.return_value = "192.168.1.5"
        app._app_var = MagicMock()
        app._app_var.get.return_value = "SRCMS"
        app._remote_listbox = MagicMock()
        app._remote_path_var = MagicMock()
        # Pre-set a deeper dir to ensure it is reset to root
        app._current_remote_dir = "/sdcard/SRCMS/uploads/subdir"

        mock_uploader = mock_uploader_cls.return_value
        mock_uploader.list_directory.return_value = [("file.txt", False)]

        app._connect_and_browse()

        assert app._current_remote_dir == "/sdcard/SRCMS/uploads"
        mock_uploader.list_directory.assert_called_once_with("/sdcard/SRCMS/uploads")

    @patch("srcms_uploader.gui.ttk")
    @patch("srcms_uploader.gui.messagebox.showerror")
    @patch("srcms_uploader.gui.AdbUploader")
    def test_connect_and_browse_shows_error_on_failed_connection(
        self, mock_uploader_cls, mock_showerror, mock_ttk, mock_tk, config_file
    ):
        """connect_and_browse should show an error dialog if the connection fails."""
        from srcms_uploader.gui import UploaderApp

        app = UploaderApp(config_path=str(config_file))
        app._ip_var = MagicMock()
        app._ip_var.get.return_value = "192.168.1.5"
        app._app_var = MagicMock()
        app._app_var.get.return_value = "SRCMS"
        app._remote_listbox = MagicMock()
        app._remote_path_var = MagicMock()

        mock_uploader = mock_uploader_cls.return_value
        mock_uploader.list_directory.side_effect = RuntimeError("No such file or directory")

        app._connect_and_browse()

        # An error dialog should appear so the user knows the connection failed
        mock_showerror.assert_called_once()
        # Listbox cleared, entries empty
        assert app._remote_entries == []
        app._remote_listbox.delete.assert_called()
