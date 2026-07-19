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
        app._remote_uploader = mock_uploader

        app._refresh_remote_browser()

        mock_uploader.list_directory.assert_called_once_with("/sdcard/SRCMS/uploads")
        mock_uploader.disconnect.assert_not_called()
        app._remote_listbox.insert.assert_any_call("end", "   a.txt")
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
        app._remote_uploader = mock_uploader

        app._open_selected_remote_entry()

        assert app._current_remote_dir == "/sdcard/SRCMS/uploads/docs"
        mock_uploader.list_directory.assert_called_once_with("/sdcard/SRCMS/uploads/docs")

    @patch("srcms_uploader.gui.ttk")
    def test_remote_listbox_uses_double_click_binding(self, mock_ttk, mock_tk, config_file):
        """remote entries should open via double click instead of a button."""
        from srcms_uploader.gui import UploaderApp

        app = UploaderApp(config_path=str(config_file))
        app._remote_listbox.bind.assert_any_call("<Double-Button-1>", app._open_selected_remote_entry)

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
        app._remote_uploader = mock_uploader

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

        mock_uploader.connect.assert_called_once()
        assert app._current_remote_dir == "/sdcard/SRCMS/uploads"
        mock_uploader.list_directory.assert_called_once_with("/sdcard/SRCMS/uploads")
        app._btn_connect.config.assert_any_call(state="disabled")
        app._btn_disconnect.config.assert_any_call(state="normal")
        assert app._is_connected is True

    @patch("srcms_uploader.gui.ttk")
    def test_app_selection_updates_remote_root(self, mock_ttk, mock_tk, config_file):
        """changing the selected app should reset the remote browser root."""
        from srcms_uploader.gui import UploaderApp

        app = UploaderApp(config_path=str(config_file))
        app._app_var = MagicMock()
        app._app_var.get.return_value = "Music"
        app._ip_var = MagicMock()
        app._ip_var.get.return_value = ""
        app._selected_app_path_var = MagicMock()
        app._remote_listbox = MagicMock()
        app._remote_path_var = MagicMock()
        app._current_remote_dir = "/sdcard/SRCMS/uploads/subdir"

        app._on_app_changed()

        assert app._current_remote_dir == "/sdcard/Music/Uploads"
        app._selected_app_path_var.set.assert_called_once_with("/sdcard/Music/Uploads")
        app._remote_path_var.set.assert_called_once_with("Current remote path: /sdcard/Music/Uploads")
        app._remote_listbox.delete.assert_called_once_with(0, "end")

    @patch("srcms_uploader.gui.ttk")
    def test_app_selection_without_remote_widgets_does_not_crash(self, mock_ttk, mock_tk, config_file):
        """startup callback should tolerate missing remote explorer widgets."""
        from srcms_uploader.gui import UploaderApp

        app = UploaderApp(config_path=str(config_file))
        app._app_var = MagicMock()
        app._app_var.get.return_value = ""
        del app._remote_path_var
        del app._remote_listbox

        app._on_app_changed()

        assert app._current_remote_dir is None

    @patch("srcms_uploader.gui.ttk")
    @patch("srcms_uploader.gui.AdbUploader")
    def test_refresh_remote_browser_resets_from_previous_app_root(
        self, mock_uploader_cls, mock_ttk, mock_tk, config_file
    ):
        """refresh should ignore stale paths from another app selection."""
        from srcms_uploader.gui import UploaderApp

        app = UploaderApp(config_path=str(config_file))
        app._ip_var = MagicMock()
        app._ip_var.get.return_value = "192.168.1.5"
        app._app_var = MagicMock()
        app._app_var.get.return_value = "Music"
        app._remote_listbox = MagicMock()
        app._remote_path_var = MagicMock()
        app._selected_app_path_var = MagicMock()
        app._current_remote_dir = "/sdcard/SRCMS/uploads/subdir"

        mock_uploader = mock_uploader_cls.return_value
        mock_uploader.list_directory.return_value = []
        app._remote_uploader = mock_uploader

        app._refresh_remote_browser()

        assert app._current_remote_dir == "/sdcard/Music/Uploads"
        mock_uploader.list_directory.assert_called_once_with("/sdcard/Music/Uploads")

    @patch("srcms_uploader.gui.ttk")
    @patch("srcms_uploader.gui.AdbUploader")
    def test_refresh_remote_browser_terminates_connection_on_error(
        self, mock_uploader_cls, mock_ttk, mock_tk, config_file
    ):
        """remote errors should mark the connection as disconnected."""
        from srcms_uploader.gui import UploaderApp

        app = UploaderApp(config_path=str(config_file))
        app._ip_var = MagicMock()
        app._ip_var.get.return_value = "192.168.1.5"
        app._app_var = MagicMock()
        app._app_var.get.return_value = "SRCMS"
        app._remote_listbox = MagicMock()
        app._remote_path_var = MagicMock()

        mock_uploader = mock_uploader_cls.return_value
        mock_uploader.list_directory.side_effect = RuntimeError("connection lost")
        app._remote_uploader = mock_uploader
        app._set_connection_state(True)

        app._refresh_remote_browser()

        mock_uploader.disconnect.assert_called_once()
        assert app._remote_uploader is None
        assert app._is_connected is False
        app._btn_connect.config.assert_any_call(state="normal")
        app._btn_disconnect.config.assert_any_call(state="disabled")

    @patch("srcms_uploader.gui.ttk")
    @patch("srcms_uploader.gui.AdbUploader")
    def test_app_selection_refreshes_remote_browser_when_connected(
        self, mock_uploader_cls, mock_ttk, mock_tk, config_file
    ):
        """changing the app should immediately refresh the file explorer when connected."""
        from srcms_uploader.gui import UploaderApp

        app = UploaderApp(config_path=str(config_file))
        app._app_var = MagicMock()
        app._app_var.get.return_value = "Music"
        app._ip_var = MagicMock()
        app._ip_var.get.return_value = "192.168.1.5"
        app._remote_listbox = MagicMock()
        app._remote_path_var = MagicMock()
        app._selected_app_path_var = MagicMock()
        app._current_remote_dir = "/sdcard/SRCMS/uploads"

        mock_uploader = mock_uploader_cls.return_value
        mock_uploader.list_directory.return_value = [("song.mp3", False)]
        app._remote_uploader = mock_uploader

        app._on_app_changed()

        mock_uploader.list_directory.assert_called_once_with("/sdcard/Music/Uploads")
        app._remote_listbox.insert.assert_called_once_with("end", "   song.mp3")
        mock_uploader.disconnect.assert_not_called()

    @patch("srcms_uploader.gui.ttk")
    @patch("srcms_uploader.gui.AdbUploader")
    def test_disconnect_button_closes_connection_and_resets_state(
        self, mock_uploader_cls, mock_ttk, mock_tk, config_file
    ):
        """disconnect should close the active connection and re-enable connect."""
        from srcms_uploader.gui import UploaderApp

        app = UploaderApp(config_path=str(config_file))
        app._ip_var = MagicMock()
        app._ip_var.get.return_value = "192.168.1.5"
        app._app_var = MagicMock()
        app._app_var.get.return_value = "SRCMS"
        app._remote_listbox = MagicMock()
        app._remote_path_var = MagicMock()

        mock_uploader = mock_uploader_cls.return_value
        app._remote_uploader = mock_uploader
        app._set_connection_state(True)

        app._disconnect_remote()

        mock_uploader.disconnect.assert_called_once()
        assert app._remote_uploader is None
        assert app._is_connected is False
        app._btn_connect.config.assert_any_call(state="normal")
        app._btn_disconnect.config.assert_any_call(state="disabled")
        app._remote_listbox.delete.assert_called_once_with(0, "end")

    @patch("srcms_uploader.gui.ttk")
    def test_connect_and_disconnect_buttons_toggle_states(self, mock_ttk, mock_tk, config_file):
        """connect should disable while connected and disconnect should enable."""
        button_mocks = [MagicMock(name=f"btn{i}") for i in range(10)]
        mock_ttk.Button.side_effect = button_mocks

        from srcms_uploader.gui import UploaderApp

        app = UploaderApp(config_path=str(config_file))

        app._set_connection_state(True)

        button_mocks[0].config.assert_any_call(state="disabled")
        button_mocks[1].config.assert_any_call(state="normal")
        button_mocks[5].config.assert_any_call(state="normal")
        button_mocks[6].config.assert_any_call(state="normal")
        button_mocks[7].config.assert_any_call(state="normal")
        button_mocks[8].config.assert_any_call(state="normal")
        button_mocks[9].config.assert_any_call(state="normal")

        app._set_connection_state(False)

        button_mocks[0].config.assert_any_call(state="normal")
        button_mocks[1].config.assert_any_call(state="disabled")
        button_mocks[5].config.assert_any_call(state="disabled")
        button_mocks[6].config.assert_any_call(state="disabled")
        button_mocks[7].config.assert_any_call(state="disabled")
        button_mocks[8].config.assert_any_call(state="disabled")
        button_mocks[9].config.assert_any_call(state="disabled")

    @patch("srcms_uploader.gui.ttk")
    @patch("srcms_uploader.gui.filedialog.askdirectory", return_value="C:/Downloads")
    @patch("srcms_uploader.gui.messagebox.showinfo")
    @patch("srcms_uploader.gui.AdbUploader")
    def test_download_selected_remote_entry_pulls_file(
        self, mock_uploader_cls, mock_showinfo, mock_askdirectory, mock_ttk, mock_tk, config_file
    ):
        """download should pull the selected remote file into the chosen folder."""
        from srcms_uploader.gui import UploaderApp

        app = UploaderApp(config_path=str(config_file))
        app._ip_var = MagicMock()
        app._ip_var.get.return_value = "192.168.1.5"
        app._app_var = MagicMock()
        app._app_var.get.return_value = "SRCMS"
        app._remote_listbox = MagicMock()
        app._remote_listbox.curselection.return_value = (0,)
        app._remote_path_var = MagicMock()
        app._remote_entries = [("Dancing Queen - Abba.ogg", False)]
        app._current_remote_dir = "/sdcard/SRCMS/uploads"

        mock_uploader = mock_uploader_cls.return_value
        app._remote_uploader = mock_uploader

        app._download_selected_remote_entry()

        mock_askdirectory.assert_called_once()
        mock_uploader.pull.assert_called_once_with("/sdcard/SRCMS/uploads/Dancing Queen - Abba.ogg", "C:/Downloads")
        mock_showinfo.assert_called_once()

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
        mock_uploader.connect.side_effect = RuntimeError("No such file or directory")

        app._connect_and_browse()

        # An error dialog should appear so the user knows the connection failed
        mock_showerror.assert_called_once()
        assert app._remote_uploader is None
        assert app._is_connected is False
