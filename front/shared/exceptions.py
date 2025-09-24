# -*- coding: utf-8 -*-
"""统一异常层次结构（渐进替换 core.* 中的散乱异常）。

分层：
InfraError: 基础设施（网络/IO/设备/模型服务）
  - DetectionInfraError
  - OCRInfraError
DomainError: 领域逻辑（寻路/状态机/技能）
ApplicationError: 应用编排层（主循环、用例）

保留向后兼容：导出旧 DetectionError 名称
"""
from __future__ import annotations
from typing import Any

class AppBaseError(Exception):
    """根异常，便于统一捕获（不直接使用 Python 内置）。"""

class InfraError(AppBaseError):
    pass

class DetectionInfraError(InfraError):
    pass

class OCRInfraError(InfraError):
    pass

class DomainError(AppBaseError):
    pass

class MovementDomainError(DomainError):
    pass

class SkillDomainError(DomainError):
    pass

class ApplicationError(AppBaseError):
    pass

# 兼容旧名称（后续逐步替换引用）
DetectionError = DetectionInfraError

__all__ = [
    "AppBaseError",
    "InfraError",
    "DetectionInfraError",
    "OCRInfraError",
    "DomainError",
    "MovementDomainError",
    "SkillDomainError",
    "ApplicationError",
    "DetectionError",
]
