# -*- coding: utf-8 -*-
"""Detection controller (Phase 1 skeleton).

Provides delegation layer for detection / YOLO / minimap related calls.
Real logic remains in PlayerThread until migrated.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Any, Tuple

if TYPE_CHECKING:  # pragma: no cover
    from core.player import PlayerThread  # type: ignore


class DetectionController:
    def __init__(self, pt: 'PlayerThread') -> None:
        self.pt = pt

    # === Socket / communication wrappers ===
    def send_with_retry(self, data, message):
        return self.pt.send_with_retry(data, message)

    def _reconnect(self):  # noqa: D401
        return self.pt._reconnect()

    def _recv_exact(self, n: int) -> bytes:  # noqa: D401
        return self.pt._recv_exact(n)

    def receive_message_from_server(self) -> Tuple[Any, Any]:  # noqa: D401
        return self.pt.receive_message_from_server()

    # === Detection wrappers ===
    def get_yolo_res(self, *args, **kwargs):
        return self.pt.get_yolo_res(*args, **kwargs)

    def process_detect_message(self, *args, **kwargs):
        return self.pt.process_detect_message(*args, **kwargs)

    def get_min_map_yolo_res(self, *args, **kwargs):
        return self.pt.get_min_map_yolo_res(*args, **kwargs)

    def min_map_process_detect_message(self, *args, **kwargs):
        return self.pt.min_map_process_detect_message(*args, **kwargs)

    # === High level (new) ===
    def detect_frame(self):  # unified frame detection entry
        return self.pt.detect_frame()

    # OCR region (kept here for cross-domain; also exposed in OCRController)
    def ocr_region(self, *args, **kwargs):  # noqa: D401
        return self.pt.ocr_region(*args, **kwargs)