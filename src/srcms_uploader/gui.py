"""SRCMS Data Uploader – Graphical User Interface (tkinter).

Provides a simple GUI with:
  - Text input for the remote Android device IP address
  - File chooser dialog for selecting files / directories to upload
  - Dropdown to select the remote app (from config.yaml)
  - Progress feedback during upload
"""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path, PurePosixPath
from typing import List, Optional, Tuple

if __package__:
    from .adb import AdbUploader, ADB_DEFAULT_PORT
    from .config import RemoteApp, load_config
else:
    from srcms_uploader.adb import AdbUploader, ADB_DEFAULT_PORT
    from srcms_uploader.config import RemoteApp, load_config


class UploaderApp:
    """Main GUI application window."""

    def __init__(self, config_path: Optional[str] = None) -> None:
        self._config_path = config_path
        self._apps: List[RemoteApp] = []
        self._selected_paths: List[Path] = []
        self._remote_entries: List[Tuple[str, bool]] = []
        self._current_remote_dir: Optional[str] = None

        self._root = tk.Tk()
        self._root.title("SRCMS Data Uploader")
        self._root.resizable(False, False)

        self._load_config()
        self._build_ui()

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def _load_config(self) -> None:
        try:
            self._apps = load_config(self._config_path)
        except (FileNotFoundError, ValueError) as exc:
            messagebox.showerror("Configuration Error", str(exc))
            self._apps = []

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = self._root
        pad = {"padx": 10, "pady": 5}

        # --- IP Address ---
        frame_ip = ttk.LabelFrame(root, text="Device IP Address", padding=10)
        frame_ip.pack(fill="x", **pad)

        self._ip_var = tk.StringVar(master=root)
        ip_entry = ttk.Entry(frame_ip, textvariable=self._ip_var, width=40)
        ip_entry.pack(fill="x")

        # --- File Selection ---
        frame_files = ttk.LabelFrame(root, text="Files / Directories to Upload", padding=10)
        frame_files.pack(fill="x", **pad)

        btn_frame = ttk.Frame(frame_files)
        btn_frame.pack(fill="x")

        ttk.Button(btn_frame, text="Add Files…", command=self._add_files).pack(side="left", padx=(0, 5))
        ttk.Button(btn_frame, text="Add Directory…", command=self._add_directory).pack(side="left", padx=(0, 5))
        ttk.Button(btn_frame, text="Clear", command=self._clear_paths).pack(side="left")

        self._paths_listbox = tk.Listbox(frame_files, height=6, width=60)
        self._paths_listbox.pack(fill="x", pady=(5, 0))

        # --- Remote App ---
        frame_app = ttk.LabelFrame(root, text="Remote App", padding=10)
        frame_app.pack(fill="x", **pad)

        self._app_var = tk.StringVar(master=root)
        app_names = [app.name for app in self._apps]
        self._app_combo = ttk.Combobox(
            frame_app, textvariable=self._app_var, values=app_names,
            state="readonly", width=37,
        )
        self._app_combo.pack(fill="x")
        if app_names:
            self._app_combo.current(0)

        # --- Upload Button ---
        self._upload_btn = ttk.Button(root, text="Upload", command=self._start_upload)
        self._upload_btn.pack(**pad)

        # --- Progress ---
        self._progress_var = tk.StringVar(master=root, value="")
        self._progress_label = ttk.Label(root, textvariable=self._progress_var)
        self._progress_label.pack(**pad)

        self._progressbar = ttk.Progressbar(root, mode="determinate", length=400)
        self._progressbar.pack(**pad)

        # --- Remote Explorer ---
        frame_remote = ttk.LabelFrame(root, text="Remote Files", padding=10)
        frame_remote.pack(fill="x", **pad)

        self._remote_path_var = tk.StringVar(master=root, value="")
        ttk.Label(frame_remote, textvariable=self._remote_path_var).pack(fill="x")

        remote_btn_frame = ttk.Frame(frame_remote)
        remote_btn_frame.pack(fill="x", pady=(5, 0))

        ttk.Button(remote_btn_frame, text="Refresh", command=self._refresh_remote_browser).pack(
            side="left", padx=(0, 5)
        )
        ttk.Button(remote_btn_frame, text="Open", command=self._open_selected_remote_entry).pack(
            side="left", padx=(0, 5)
        )
        ttk.Button(remote_btn_frame, text="Up", command=self._go_remote_parent).pack(
            side="left", padx=(0, 5)
        )
        ttk.Button(remote_btn_frame, text="Delete Selected", command=self._delete_selected_remote_entry).pack(
            side="left"
        )

        self._remote_listbox = tk.Listbox(frame_remote, height=8, width=60)
        self._remote_listbox.pack(fill="x", pady=(5, 0))

    # ------------------------------------------------------------------
    # File chooser actions
    # ------------------------------------------------------------------

    def _add_files(self) -> None:
        files = filedialog.askopenfilenames(title="Select files to upload")
        for f in files:
            p = Path(f)
            if p not in self._selected_paths:
                self._selected_paths.append(p)
                self._paths_listbox.insert(tk.END, str(p))

    def _add_directory(self) -> None:
        directory = filedialog.askdirectory(title="Select directory to upload")
        if directory:
            p = Path(directory)
            if p not in self._selected_paths:
                self._selected_paths.append(p)
                self._paths_listbox.insert(tk.END, str(p))

    def _clear_paths(self) -> None:
        self._selected_paths.clear()
        self._paths_listbox.delete(0, tk.END)

    # ------------------------------------------------------------------
    # Remote explorer actions
    # ------------------------------------------------------------------

    def _selected_remote_app(self) -> Optional[RemoteApp]:
        selected_name = self._app_var.get()
        return next((a for a in self._apps if a.name == selected_name), None)

    def _refresh_remote_browser(self) -> None:
        ip = self._ip_var.get().strip()
        if not ip:
            messagebox.showwarning("Missing Input", "Please enter the device IP address.")
            return

        remote_app = self._selected_remote_app()
        if remote_app is None:
            messagebox.showwarning("Missing Input", "Please select a remote app.")
            return

        if not self._current_remote_dir:
            self._current_remote_dir = remote_app.path

        uploader = AdbUploader(host=ip)
        try:
            uploader.connect()
            self._remote_entries = uploader.list_directory(self._current_remote_dir)
        except RuntimeError as exc:
            messagebox.showerror("Remote Explorer Error", str(exc))
            return
        finally:
            uploader.disconnect()

        self._remote_listbox.delete(0, tk.END)
        for name, is_dir in self._remote_entries:
            label = f"[DIR] {name}" if is_dir else name
            self._remote_listbox.insert(tk.END, label)
        self._remote_path_var.set(f"Current remote path: {self._current_remote_dir}")

    def _open_selected_remote_entry(self) -> None:
        selected = self._get_selected_remote_entry()
        if selected is None:
            return
        name, is_dir = selected
        if not is_dir:
            messagebox.showinfo("Remote Explorer", "Please select a subdirectory to open.")
            return

        base = PurePosixPath(self._current_remote_dir or "")
        self._current_remote_dir = str(base / name)
        self._refresh_remote_browser()

    def _go_remote_parent(self) -> None:
        remote_app = self._selected_remote_app()
        if remote_app is None:
            messagebox.showwarning("Missing Input", "Please select a remote app.")
            return

        if not self._current_remote_dir:
            self._current_remote_dir = remote_app.path
            self._refresh_remote_browser()
            return

        current = PurePosixPath(self._current_remote_dir)
        root = PurePosixPath(remote_app.path)
        if current == root:
            return

        parent = current.parent
        if len(parent.parts) < len(root.parts):
            parent = root
        self._current_remote_dir = str(parent)
        self._refresh_remote_browser()

    def _delete_selected_remote_entry(self) -> None:
        selected = self._get_selected_remote_entry()
        if selected is None:
            return

        name, _ = selected
        remote_path = str(PurePosixPath(self._current_remote_dir or "") / name)
        confirmed = messagebox.askyesno(
            "Confirm Delete",
            f"Delete '{remote_path}' from the remote device?",
        )
        if not confirmed:
            return

        ip = self._ip_var.get().strip()
        if not ip:
            messagebox.showwarning("Missing Input", "Please enter the device IP address.")
            return

        uploader = AdbUploader(host=ip)
        try:
            uploader.connect()
            uploader.delete_remote_path(remote_path)
            messagebox.showinfo("Delete Complete", f"Deleted '{remote_path}'.")
        except RuntimeError as exc:
            messagebox.showerror("Delete Failed", str(exc))
            return
        finally:
            uploader.disconnect()

        self._refresh_remote_browser()

    def _get_selected_remote_entry(self) -> Optional[Tuple[str, bool]]:
        selection = self._remote_listbox.curselection()
        if not selection:
            messagebox.showwarning("Remote Explorer", "Please select a file or subdirectory.")
            return None

        index = selection[0]
        if index >= len(self._remote_entries):
            return None
        return self._remote_entries[index]

    # ------------------------------------------------------------------
    # Upload logic
    # ------------------------------------------------------------------

    def _start_upload(self) -> None:
        # Validate inputs
        ip = self._ip_var.get().strip()
        if not ip:
            messagebox.showwarning("Missing Input", "Please enter the device IP address.")
            return

        if not self._selected_paths:
            messagebox.showwarning("Missing Input", "Please select at least one file or directory.")
            return

        if not self._app_var.get():
            messagebox.showwarning("Missing Input", "Please select a remote app.")
            return

        # Find selected app
        selected_name = self._app_var.get()
        remote_app = next((a for a in self._apps if a.name == selected_name), None)
        if remote_app is None:
            messagebox.showerror("Error", "Selected app not found in configuration.")
            return

        # Disable button and start upload in a thread
        self._upload_btn.config(state="disabled")
        self._progressbar["value"] = 0
        self._progressbar["maximum"] = len(self._selected_paths)
        self._progress_var.set("Connecting…")

        thread = threading.Thread(
            target=self._upload_thread,
            args=(ip, self._selected_paths.copy(), remote_app),
            daemon=True,
        )
        thread.start()

    def _upload_thread(self, ip: str, paths: List[Path], remote_app: RemoteApp) -> None:
        """Run the upload in a background thread to keep the GUI responsive."""
        uploader = AdbUploader(host=ip)
        try:
            uploader.connect()
            total = len(paths)
            for i, path in enumerate(paths, start=1):
                self._root.after(0, self._update_progress, i, total, path.name)
                uploader.push(path, remote_app.path)
            self._root.after(0, self._upload_done, None)
        except (FileNotFoundError, RuntimeError) as exc:
            self._root.after(0, self._upload_done, str(exc))
        finally:
            uploader.disconnect()

    def _update_progress(self, current: int, total: int, filename: str) -> None:
        self._progressbar["value"] = current
        self._progress_var.set(f"Uploading ({current}/{total}): {filename}")

    def _upload_done(self, error: Optional[str]) -> None:
        self._upload_btn.config(state="normal")
        if error:
            self._progressbar["value"] = 0
            self._progress_var.set("Upload failed.")
            messagebox.showerror("Upload Error", error)
        else:
            self._progressbar["value"] = self._progressbar["maximum"]
            self._progress_var.set("Upload complete ✓")
            messagebox.showinfo("Success", "All files uploaded successfully.")

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Start the tkinter main loop."""
        self._root.mainloop()
