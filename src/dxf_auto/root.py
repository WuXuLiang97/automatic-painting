# ...new file...
"""Unified project root path utility.
All legacy `from root_dir import root_path` imports will be migrated to:
    from dxf_auto.root import root_path
The root_path here resolves to the repository root (parent of `src/`).
Handles PyInstaller frozen mode as well.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

_DEF = Path(__file__).resolve()
# src/dxf_auto/root.py -> project root is parent of parent of parent
_project_root = _DEF.parents[2]

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    # In a frozen bundle use the extraction directory
    root_path: str = sys._MEIPASS  # type: ignore
else:
    root_path = str(_project_root)


def get_root_path() -> str:
    return root_path

__all__ = ["root_path", "get_root_path"]
