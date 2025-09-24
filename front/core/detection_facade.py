# -*- coding: utf-8 -*-
"""(Deprecated) 兼容层: core.detection_facade

原实现已迁移至 front.infrastructure.detection.facade.DetectionFacade。
此模块仅做过渡，后续请统一改为：
    from front.infrastructure.detection import DetectionFacade
或：
    from front.shared.exceptions import DetectionError

迁移完成后可以删除本文件。
"""
from __future__ import annotations
from front.infrastructure.detection.facade import DetectionFacade  # noqa: F401
from front.shared.exceptions import DetectionError  # noqa: F401
from front.shared.constants import DetectionMessageType, WINDOW_WIDTH, WINDOW_HEIGHT  # noqa: F401

__all__ = [
    "DetectionFacade",
    "DetectionError",
    "DetectionMessageType",
    "WINDOW_WIDTH",
    "WINDOW_HEIGHT",
]
