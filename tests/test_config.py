"""Tests for srcms_uploader.config module."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from srcms_uploader.config import RemoteApp, load_config


# ---------------------------------------------------------------------------
# RemoteApp
# ---------------------------------------------------------------------------

class TestRemoteApp:
    def test_valid_creation(self):
        app = RemoteApp(name="SRCMS", path="/sdcard/SRCMS/uploads")
        assert app.name == "SRCMS"
        assert app.path == "/sdcard/SRCMS/uploads"

    def test_strips_whitespace(self):
        app = RemoteApp(name="  SRCMS  ", path="  /sdcard/path  ")
        assert app.name == "SRCMS"
        assert app.path == "/sdcard/path"

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            RemoteApp(name="", path="/sdcard/path")

    def test_empty_path_raises(self):
        with pytest.raises(ValueError, match="path"):
            RemoteApp(name="App", path="")

    def test_whitespace_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            RemoteApp(name="   ", path="/sdcard/path")


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------

class TestLoadConfig:
    def _write_config(self, tmp_path: Path, content: str) -> Path:
        cfg = tmp_path / "config.yaml"
        cfg.write_text(textwrap.dedent(content))
        return cfg

    def test_valid_config(self, tmp_path):
        cfg = self._write_config(
            tmp_path,
            """
            apps:
              - name: "SRCMS"
                path: "/sdcard/SRCMS/uploads"
              - name: "Music"
                path: "/sdcard/Music"
            """,
        )
        apps = load_config(cfg)
        assert len(apps) == 2
        assert apps[0].name == "SRCMS"
        assert apps[0].path == "/sdcard/SRCMS/uploads"
        assert apps[1].name == "Music"
        assert apps[1].path == "/sdcard/Music"

    def test_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / "nonexistent.yaml")

    def test_missing_apps_key(self, tmp_path):
        cfg = self._write_config(tmp_path, "foo: bar\n")
        with pytest.raises(ValueError, match="apps"):
            load_config(cfg)

    def test_empty_apps_list(self, tmp_path):
        cfg = self._write_config(tmp_path, "apps: []\n")
        with pytest.raises(ValueError, match="non-empty"):
            load_config(cfg)

    def test_entry_missing_name(self, tmp_path):
        cfg = self._write_config(
            tmp_path,
            """
            apps:
              - path: "/sdcard/foo"
            """,
        )
        with pytest.raises(ValueError, match="name"):
            load_config(cfg)

    def test_entry_missing_path(self, tmp_path):
        cfg = self._write_config(
            tmp_path,
            """
            apps:
              - name: "App"
            """,
        )
        with pytest.raises(ValueError, match="path"):
            load_config(cfg)

    def test_entry_not_a_mapping(self, tmp_path):
        cfg = self._write_config(
            tmp_path,
            """
            apps:
              - "not a mapping"
            """,
        )
        with pytest.raises(ValueError, match="mapping"):
            load_config(cfg)

    def test_no_default_config_raises(self, tmp_path, monkeypatch):
        """When no default config exists, FileNotFoundError should be raised."""
        # Patch DEFAULT_CONFIG_PATHS to point to non-existent files
        import srcms_uploader.config as cfg_module
        monkeypatch.setattr(
            cfg_module,
            "DEFAULT_CONFIG_PATHS",
            [tmp_path / "does_not_exist.yaml"],
        )
        with pytest.raises(FileNotFoundError, match="No config file found"):
            load_config()
