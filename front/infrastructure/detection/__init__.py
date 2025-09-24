# -*- coding: utf-8 -*-
"""Detection infrastructure package.

包含：
- 协议接口 (protocols)
- 具体实现 (facade / adapters)
- 未来可扩展：缓存层、熔断器、Mock/Fake 实现
"""
from .protocols import IDetector
from .facade import DetectionFacade

__all__ = ["IDetector", "DetectionFacade"]
