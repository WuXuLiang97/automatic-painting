# -*- coding: utf-8 -*-
"""拆分后的常量聚合导出层。

逐步用 from shared.constants import X 取代旧 core.constants。
"""
from .screen import WINDOW_WIDTH, WINDOW_HEIGHT
from .detection import DetectionMessageType
from .timeouts import (
    DOOR_SEARCH_TIMEOUT,
    BOSS_ROOM_TIMEOUT,
    SKILL_RELEASE_TIMEOUT,
    ULTIMATE_RELEASE_TIMEOUT,
    PLAYER_RECOVER_SPIRAL_DURATION,
    MOVEMENT_RECHECK_INTERVAL,
)
from .items import TARGET_ITEMS
from .ocr import (
    OCR_BASE_SCALE,
    OCR_TARGET_MIN_SIDE,
    OCR_TARGET_SIDE,
    OCR_MAX_SCALE,
    OCR_USE_CLAHE,
    OCR_BINARY_THRESHOLD,
    OCR_INVERT_IF_DARK,
)
from .thresholds import (
    SIMILARITY_THRESHOLD,
    PICKUP_MAX_TIME,
    GOODS_MOVING_SAMPLES,
    GOODS_MOVING_THRESHOLD,
)
from .logging_flags import LOG_VERBOSE_DETECTION

__all__ = [
    # screen
    "WINDOW_WIDTH","WINDOW_HEIGHT",
    # detection enum
    "DetectionMessageType",
    # timeouts
    "DOOR_SEARCH_TIMEOUT","BOSS_ROOM_TIMEOUT","SKILL_RELEASE_TIMEOUT","ULTIMATE_RELEASE_TIMEOUT",
    "PLAYER_RECOVER_SPIRAL_DURATION","MOVEMENT_RECHECK_INTERVAL",
    # items
    "TARGET_ITEMS",
    # ocr
    "OCR_BASE_SCALE","OCR_TARGET_MIN_SIDE","OCR_TARGET_SIDE","OCR_MAX_SCALE","OCR_USE_CLAHE",
    "OCR_BINARY_THRESHOLD","OCR_INVERT_IF_DARK",
    # thresholds
    "SIMILARITY_THRESHOLD","PICKUP_MAX_TIME","GOODS_MOVING_SAMPLES","GOODS_MOVING_THRESHOLD",
    # logging flag
    "LOG_VERBOSE_DETECTION",
]
