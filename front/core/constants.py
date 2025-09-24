# -*- coding: utf-8 -*-
"""项目级通用常量与配置集中管理。
后续请将散落在代码中的魔法数字/字符串逐步迁移到此文件或其子模块。
"""
from enum import Enum

# 窗口/画面尺寸（统一引用，避免硬编码）
WINDOW_WIDTH = 1067
WINDOW_HEIGHT = 600

# 识别/算法相关阈值
SIMILARITY_THRESHOLD = 0.7  # 字符串相似度阈值
PICKUP_MAX_TIME = 30        # 拾取物品最大持续时间（秒）

# ============ 新增：统一超时/等待配置（A/C 重构提取） ============
DOOR_SEARCH_TIMEOUT = 30         # 找门最大耗时
BOSS_ROOM_TIMEOUT = 120          # BOSS 房最大停留
SKILL_RELEASE_TIMEOUT = 5        # 普通技能释放等待
ULTIMATE_RELEASE_TIMEOUT = 10    # 大招释放等待
PLAYER_RECOVER_SPIRAL_DURATION = 2  # 丢失人物时螺旋搜索时长
MOVEMENT_RECHECK_INTERVAL = 5       # 二次位置检测间隔
GOODS_MOVING_SAMPLES = 3            # 判断物品是否仍在移动采样帧数
GOODS_MOVING_THRESHOLD = 5          # 物品移动阈值像素

# OCR / 图像预处理相关（D amplify 优化）
OCR_BASE_SCALE = 1.5               # 基础放大倍率
OCR_TARGET_MIN_SIDE = 80           # 低于该尺寸的短边放大到目标
OCR_TARGET_SIDE = 180              # 目标短边尺寸
OCR_MAX_SCALE = 3.0                # 最大放大倍数保护
OCR_USE_CLAHE = True               # 是否使用自适应直方图均衡
OCR_BINARY_THRESHOLD = True        # 是否做阈值二值化
OCR_INVERT_IF_DARK = True          # 过暗是否反色

# 高频日志开关（C 日志级别控制示例，可用于动态降噪）
LOG_VERBOSE_DETECTION = False

# 目标物品（示例：从原 player.py 中抽离，可继续扩展/做配置化）
TARGET_ITEMS = [
    "风化的碎骨",
    "破旧的皮革",
    "碎布片",
    "生锈的铁片",
    "最下级硬化剂",
    "最下级砥石",
    "炉岩核",
    "协调结晶体",
    "嘿",
    "嗯",
    "呀",
]


class DetectionMessageType(str, Enum):
    GAME = "game_windows"
    MINIMAP = "min_map"
    OCR = "ocr"


# 以后可扩展：职业、地图、路径、技能冷却等数据驱动配置
# 例如：
# OCCUPATION_EXTRA = {
#     "女魔法师-召唤师": {"buff_sequence": ["a", "b"]}
# }
