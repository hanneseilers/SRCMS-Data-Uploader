"""Tests for srcms_uploader.main module (GUI launcher)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from srcms_uploader.main import main


class TestMain:
    def test_main_launches_gui(self, tmp_path):
        """main() should instantiate UploaderApp and call run()."""
        mock_app = MagicMock()
        with patch("srcms_uploader.main.UploaderApp", return_value=mock_app) as mock_cls:
            result = main(config_path="/some/path.yaml")

        mock_cls.assert_called_once_with(config_path="/some/path.yaml")
        mock_app.run.assert_called_once()
        assert result == 0

    def test_main_default_config(self):
        """main() with no config_path passes None to UploaderApp."""
        mock_app = MagicMock()
        with patch("srcms_uploader.main.UploaderApp", return_value=mock_app) as mock_cls:
            result = main()

        mock_cls.assert_called_once_with(config_path=None)
        assert result == 0
