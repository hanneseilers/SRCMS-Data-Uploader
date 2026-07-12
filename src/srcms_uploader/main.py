"""SRCMS Data Uploader – application entry point.

Launches the graphical user interface for uploading files to a remote Android
device via ADB over WiFi.
"""

from __future__ import annotations

import sys
from typing import Optional

from .gui import UploaderApp


def main(config_path: Optional[str] = None) -> int:
    """Launch the SRCMS Data Uploader GUI.

    Parameters
    ----------
    config_path:
        Optional path to the YAML config file.  When *None* the default search
        paths are used (see :func:`srcms_uploader.config.load_config`).

    Returns
    -------
    int
        Exit code – 0 on success.
    """
    app = UploaderApp(config_path=config_path)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
