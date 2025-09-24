# -*- coding: utf-8 -*-
"""检测相关接口协议 (Ports)。

Application / Domain 层只依赖这些抽象，方便替换实现（本地模型 / 远程服务 / Mock）。
"""
from __future__ import annotations
from typing import Protocol, List, Any
import numpy as np

class IDetector(Protocol):
    """统一检测接口。

    image 参数：可以是 numpy.ndarray (H,W,C) BGR 图像。
    返回结构暂时使用 List / str，后续可替换为数据模型。
    """
    def detect_game(self, image: np.ndarray) -> List[Any]: ...
    def detect_minimap(self, image: np.ndarray) -> List[Any]: ...
    def ocr(self, image: np.ndarray) -> str: ...

__all__ = ["IDetector"]
