# -*- coding: utf-8 -*-
"""Detector / OCR 抽象服务 (Phase 4)

职责：
- 统一对 DetectionFacade 的调用
- 提供截图+发送+结果解析封装
- 预留缓存 / 指标 / 熔断扩展点
"""
from __future__ import annotations
from typing import List, Optional, Tuple, Any, Callable
import time
import cv2

from .detection_facade import DetectionFacade, DetectionError
from utils.screen.screenshot_util import screenshot_util


class DetectorService:
    def __init__(
        self,
        facade: DetectionFacade,
        logger,
        screenshot_fn: Callable[[], Any] | None = None,
    ) -> None:
        self.facade = facade
        self.logger = logger
        self.screenshot_fn = screenshot_fn or screenshot_util.get_game_screenshot

    def detect_game(self, image=None) -> List:
        if image is None:
            image = self.screenshot_fn()
        return self.facade.detect_game(image)

    def detect_minimap(self, image=None) -> List:
        if image is None:
            # 调用小地图截图逻辑由上层决定（避免循环依赖 miniMapUtil）
            raise ValueError("detect_minimap 需要上层传入截图")
        return self.facade.detect_minimap(image)


class OcrService:
    def __init__(self, facade: DetectionFacade, logger) -> None:
        self.facade = facade
        self.logger = logger

    def ocr_region(self, image) -> str:
        return self.facade.ocr(image)

    def ocr_text(self, image) -> str:
        return self.facade.ocr(image)


# 便捷构建函数
def build_detection_services(server_ip: str, server_port: int, logger) -> Tuple[DetectorService, OcrService]:
    facade = DetectionFacade(server_ip, server_port, logger, timeout=1.0)
    facade.connect()
    detector = DetectorService(facade, logger)
    ocr = OcrService(facade, logger)
    return detector, ocr
