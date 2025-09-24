# -*- coding: utf-8 -*-
"""OCR domain module (Phase 1 scaffolding).

Encapsulates OCR related helpers (delegates to PlayerThread for now).
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from core.player import PlayerThread  # type: ignore


class OCRController:
    def __init__(self, pt: 'PlayerThread') -> None:
        self.pt = pt

    def get_text(self, *args, **kwargs):  # noqa: D401
        return self.pt.get_text(*args, **kwargs)

    def ocr_region(self, *args, **kwargs):  # noqa: D401
        return self.pt.ocr_region(*args, **kwargs)

    def waiting_for_the_text_to_appear(self, *args, **kwargs):  # noqa: D401
        return self.pt.waiting_for_the_text_to_appear(*args, **kwargs)