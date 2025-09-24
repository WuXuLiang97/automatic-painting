# ...new file...
"""Entry points bridging legacy layout.
Will be refactored in Phase 2 to call internal relocated modules.
"""
from __future__ import annotations
import importlib
import os
import sys
import traceback

LEGACY_GUI_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'front')
LEGACY_SERVICE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'service')


def _prepend_legacy(path: str):
    abs_path = os.path.abspath(path)
    if abs_path not in sys.path:
        sys.path.insert(0, abs_path)


def run_gui():  # console script target
    """Run legacy PyQt5 GUI."""
    _prepend_legacy(LEGACY_GUI_PATH)
    try:
        from front.app import main as _main  # if we later add a main() wrapper
    except Exception:  # front.app currently executes in __main__ only
        try:
            import front.app  # noqa: F401 triggers side effects
        except SystemExit:
            raise
        except Exception as e:  # provide clearer error
            print("Failed to start GUI:", e, file=sys.stderr)
            traceback.print_exc()
            raise SystemExit(1)


def run_service():  # console script target
    """Run legacy threaded server (Tk based)."""
    _prepend_legacy(LEGACY_SERVICE_PATH)
    try:
        import service.app_server  # side-effect start when executed as script? We'll call its main block manually later.
        # If app_server uses if __name__ == '__main__': we replicate minimal logic by exposing a function later (Phase 2).
    except Exception as e:
        print("Failed to start service:", e, file=sys.stderr)
        traceback.print_exc()
        raise SystemExit(1)
