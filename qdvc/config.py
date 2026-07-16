"""Application preferences (YAML at the XDG config location).

Holds preferences ONLY — never business data (that lives in the workspace).
Every read supplies a default, so no schema migration is ever needed.
"""
from __future__ import annotations

import os
from typing import Any

import yaml

from . import APP_SHORT

DEFAULTS: dict[str, Any] = {
    "last_workspace": None,
    "recent_workspaces": [],
    "reopen_last": True,
    "window": [1000, 680],
    "toolbar_style": "both",          # "both" (below) | "beside"
    "ui_backend": "gtk3",             # "gtk3" | "gtk4"
    "file_manager": "",               # optional template with {dir}/{file}
    "custom_icon": None,              # optional absolute path to png/svg
}

_VALID_BACKENDS = {"gtk3", "gtk4"}
_VALID_TOOLBAR = {"both", "beside"}


def _config_dir() -> str:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, f"qdvc-{APP_SHORT}")


def _config_path() -> str:
    return os.path.join(_config_dir(), "config.yml")


class Config:
    """Thin get/set wrapper over a YAML file."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self.load()

    # ---- persistence -------------------------------------------------
    def load(self) -> None:
        path = _config_path()
        try:
            with open(path, "r", encoding="utf-8") as fh:
                loaded = yaml.safe_load(fh) or {}
            if isinstance(loaded, dict):
                self._data = loaded
        except FileNotFoundError:
            self._data = {}
        except Exception:
            self._data = {}

    def save(self) -> None:
        path = _config_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            yaml.safe_dump(self._data, fh, sort_keys=True, allow_unicode=True)
        os.replace(tmp, path)

    # ---- generic access ----------------------------------------------
    def get(self, key: str, default: Any = None) -> Any:
        if key in self._data:
            return self._data[key]
        if default is not None:
            return default
        return DEFAULTS.get(key)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()

    # ---- validated accessors -----------------------------------------
    @property
    def ui_backend(self) -> str:
        val = str(self.get("ui_backend", "gtk3")).strip().lower()
        return val if val in _VALID_BACKENDS else "gtk3"

    @ui_backend.setter
    def ui_backend(self, value: str) -> None:
        val = str(value).strip().lower()
        self.set("ui_backend", val if val in _VALID_BACKENDS else "gtk3")

    @property
    def toolbar_style(self) -> str:
        val = str(self.get("toolbar_style", "both")).strip().lower()
        return val if val in _VALID_TOOLBAR else "both"

    @toolbar_style.setter
    def toolbar_style(self, value: str) -> None:
        val = str(value).strip().lower()
        self.set("toolbar_style", val if val in _VALID_TOOLBAR else "both")

    def push_recent(self, path: str, limit: int = 8) -> None:
        recent = [p for p in self.get("recent_workspaces", []) if p != path]
        recent.insert(0, path)
        self.set("recent_workspaces", recent[:limit])
        self.set("last_workspace", path)
