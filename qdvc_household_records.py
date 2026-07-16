#!/usr/bin/env python3
"""QDVC Household Records — thin backend dispatcher.

Selects the UI toolkit BEFORE importing any GTK, so only the chosen
front-end is loaded. Selection order:
    1. explicit --gtk3 / --gtk4 flag (anywhere in argv)
    2. the `ui_backend` key in the config
    3. default "gtk3"
"""
from __future__ import annotations

import sys


def _pick_backend(argv: list[str]) -> tuple[str, list[str]]:
    backend = None
    rest: list[str] = []
    for arg in argv[1:]:
        if arg == "--gtk3":
            backend = "gtk3"
        elif arg == "--gtk4":
            backend = "gtk4"
        else:
            rest.append(arg)
    if backend is None:
        try:
            from qdvc.config import Config
            backend = Config().ui_backend
        except Exception:
            backend = "gtk3"
    return backend, rest


def main() -> int:
    backend, rest = _pick_backend(sys.argv)
    # GApplication expects a program name in argv[0].
    backend_argv = [sys.argv[0], *rest]

    if backend == "gtk4":
        try:
            from qdvc.gtk4.gtk4_app import main as run
            return run(backend_argv)
        except Exception as exc:  # libadwaita may be absent
            print(f"[qdvc] GTK4 backend unavailable ({exc}); "
                  f"falling back to GTK3.", file=sys.stderr)

    from qdvc.gtk3.gtk3_app import main as run
    return run(backend_argv)


if __name__ == "__main__":
    raise SystemExit(main())
