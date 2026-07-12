# SRCMS Data Uploader

An interactive command-line application that uploads local files and directories
to a remote Android device via **ADB over WiFi (TCP/IP)**.  
Supports building standalone executables for **Windows** and **Linux** with PyInstaller.

---

## Features

- Prompts for the remote Android device IP address
- Accepts one or more local files / directories to upload
- Lets you select the destination app / category from a YAML config file
- Connects to the Android device via `adb connect <ip>` and pushes the data

---

## Requirements

- Python ≥ 3.9
- [Android Platform Tools](https://developer.android.com/tools/releases/platform-tools) (`adb` must be on `PATH`)
- ADB over WiFi enabled on the Android device

---

## Installation

```bash
# Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate      # Linux / macOS
.venv\Scripts\activate.bat     # Windows

# Install the application
pip install -e .
```

---

## Configuration

Edit **`config.yaml`** (in the working directory) to define the available remote
apps and their upload paths on the Android device:

```yaml
apps:
  - name: "SRCMS"
    path: "/sdcard/SRCMS/uploads"

  - name: "Photos"
    path: "/sdcard/DCIM/Uploads"

  - name: "Music"
    path: "/sdcard/Music/Uploads"
```

---

## Usage

```bash
srcms-uploader
```

Or run directly:

```bash
python -m srcms_uploader.main
```

The application will guide you through three steps:

1. **Remote IP** – enter the IP address shown by `adb tcpip 5555` on the device  
2. **Local paths** – enter one or more files / directories (one per line, empty line to finish)  
3. **Remote app** – choose the destination category from the numbered list

### Enabling ADB over WiFi on Android

```bash
# Connect the device via USB first, then:
adb tcpip 5555
# Unplug USB – the device IP is shown in Settings → About phone → Status
```

---

## Building a Standalone Executable

Install the build extras and run PyInstaller:

```bash
pip install -e ".[build]"

# Linux
pyinstaller --onefile --name srcms-uploader src/srcms_uploader/main.py

# Windows (run in a Windows environment)
pyinstaller --onefile --name srcms-uploader.exe src/srcms_uploader/main.py
```

The resulting executable is placed in the `dist/` directory.  
Copy `config.yaml` to the same directory as the executable.

---

## Running Tests

```bash
pip install -e ".[dev]"
pytest
```

---

## Project Structure

```
SRCMS-Data-Uploader/
├── config.yaml                  # Remote app definitions (edit as needed)
├── pyproject.toml               # Package metadata & build config
├── src/
│   └── srcms_uploader/
│       ├── __init__.py
│       ├── main.py              # Interactive CLI entry point
│       ├── adb.py               # ADB connection & file-push logic
│       └── config.py            # YAML config loader
└── tests/
    ├── test_config.py
    ├── test_adb.py
    └── test_main.py
```
