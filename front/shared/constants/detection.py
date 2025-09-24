# -*- coding: utf-8 -*-
"""检测/通信协议相关常量与枚举。"""
from enum import Enum

class DetectionMessageType(str, Enum):
    GAME = "game_windows"
    MINIMAP = "min_map"
    OCR = "ocr"

__all__ = ["DetectionMessageType"]
