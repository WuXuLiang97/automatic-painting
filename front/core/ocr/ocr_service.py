# -*- coding: utf-8 -*-
"""OCR service (Phase 1 skeleton).

Thin delegation layer over PlayerThread OCR related methods. Real logic
will migrate here later (PaddleOCR / caching / throttling, etc.).
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from core.player import PlayerThread  # type: ignore


class OcrService:
    def __init__(self, pt: 'PlayerThread') -> None:
        self.pt = pt

    def get_text(self, *args, **kwargs):
        return self.pt.get_text(*args, **kwargs)

    def ocr_region(self, *args, **kwargs):
        return self.pt.ocr_region(*args, **kwargs)

    def waiting_for_the_text_to_appear(self, *args, **kwargs):  # legacy API
        return self.pt.waiting_for_the_text_to_appear(*args, **kwargs)
