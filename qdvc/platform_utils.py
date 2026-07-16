"""Launch system applications (pure; branches on platform)."""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from urllib.parse import quote


def open_with_default_app(path: str) -> None:
    if sys.platform.startswith("darwin"):
        subprocess.Popen(["open", path])
    elif os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["xdg-open", path])


def open_with_text_editor(path: str) -> None:
    if sys.platform.startswith("darwin"):
        subprocess.Popen(["open", "-t", path])
    elif os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["xdg-open", path])


def _dbus_show_items(path: str) -> bool:
    """Ask the desktop's file manager to show (and select) `path` via the
    freedesktop org.freedesktop.FileManager1 interface. Returns True on success.

    Implemented by Nautilus, Dolphin, Nemo, Caja, Thunar, PCManFM, etc. This is
    the only portable Linux way to highlight a specific file rather than merely
    opening its folder."""
    uri = "file://" + quote(os.path.abspath(path))
    # Prefer gdbus (ships with glib); fall back to dbus-send.
    gdbus = shutil.which("gdbus")
    if gdbus:
        try:
            subprocess.Popen([
                gdbus, "call", "--session",
                "--dest", "org.freedesktop.FileManager1",
                "--object-path", "/org/freedesktop/FileManager1",
                "--method", "org.freedesktop.FileManager1.ShowItems",
                f"['{uri}']", "",
            ])
            return True
        except Exception:
            pass
    dbus_send = shutil.which("dbus-send")
    if dbus_send:
        try:
            subprocess.Popen([
                dbus_send, "--session", "--print-reply",
                "--dest=org.freedesktop.FileManager1",
                "/org/freedesktop/FileManager1",
                "org.freedesktop.FileManager1.ShowItems",
                f"array:string:{uri}", "string:",
            ])
            return True
        except Exception:
            pass
    return False


def reveal_in_file_manager(path: str, template: str = "") -> None:
    """Reveal `path` in the system file manager, selecting the file where the
    platform supports it. Falls back to opening the containing folder."""
    directory = path if os.path.isdir(path) else os.path.dirname(path)

    if template:
        cmd = template.format(dir=directory, file=path)
        subprocess.Popen(shlex.split(cmd))
        return

    if sys.platform.startswith("darwin"):
        # -R reveals the item in Finder with it selected.
        subprocess.Popen(["open", "-R", path])
        return
    if os.name == "nt":
        # explorer /select, highlights the file in its folder.
        subprocess.Popen(["explorer", f"/select,{os.path.normpath(path)}"])
        return

    # Linux/other: try to select via the file-manager D-Bus interface; if that
    # isn't available, just open the containing directory.
    if os.path.isdir(path):
        subprocess.Popen(["xdg-open", path])
        return
    if not _dbus_show_items(path):
        subprocess.Popen(["xdg-open", directory])
