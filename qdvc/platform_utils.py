"""Launch system applications (pure; branches on platform)."""
from __future__ import annotations

import os
import shlex
import subprocess
import sys


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


def reveal_in_file_manager(path: str, template: str = "") -> None:
    directory = path if os.path.isdir(path) else os.path.dirname(path)
    if template:
        cmd = template.format(dir=directory, file=path)
        subprocess.Popen(shlex.split(cmd))
        return
    if sys.platform.startswith("darwin"):
        subprocess.Popen(["open", directory])
    elif os.name == "nt":
        subprocess.Popen(["explorer", directory])
    else:
        subprocess.Popen(["xdg-open", directory])
