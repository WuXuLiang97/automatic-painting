# -*- coding: utf-8 -*-
"""
服务器通信协议定义
定义消息类型、协议格式等常量
"""

# ==================== 请求类型 ====================

# 游戏窗口检测请求
REQUEST_TYPE_GAME_WINDOWS = "game_windows"

# 小地图检测请求
REQUEST_TYPE_MIN_MAP = "min_map"

# OCR 识别请求
REQUEST_TYPE_OCR = "ocr"

# 所有有效的请求类型集合
VALID_REQUEST_TYPES = {
    REQUEST_TYPE_GAME_WINDOWS,
    REQUEST_TYPE_MIN_MAP,
    REQUEST_TYPE_OCR,
}

# ==================== 消息字段 ====================

# 请求头字段
HEADER_FIELD_TYPE = "type"  # 请求类型
HEADER_FIELD_IMAGE_SIZE = "image_size"  # 图像大小（字节）

# 响应头字段
RESPONSE_FIELD_TYPE = "type"  # 响应类型（与请求类型相同）
RESPONSE_FIELD_DATA_SIZE = "data_size"  # 响应数据大小（字节）

# 错误字段
ERROR_FIELD_ERROR = "error"  # 错误信息
ERROR_FIELD_SIZE_EXCEEDED = "_size_exceeded"  # 大小超限标志
ERROR_FIELD_ERROR_MSG = "_error"  # 错误消息

# ==================== 协议格式 ====================

# 头部长度字段大小（4 字节，大端序）
HEADER_LENGTH_SIZE = 4

# 协议版本（预留）
PROTOCOL_VERSION = 1

# ==================== 消息结构 ====================

# 请求消息结构：
# [4 bytes: header_length][header_length bytes: JSON header][image_size bytes: image data]
#
# JSON header 格式：
# {
#   "type": "game_windows" | "min_map" | "ocr",
#   "image_size": <integer>
# }

# 响应消息结构：
# [4 bytes: header_length][header_length bytes: JSON header][data_size bytes: JSON data]
#
# JSON header 格式：
# {
#   "type": <request_type>,
#   "data_size": <integer>
# }
#
# JSON data 格式（成功）：
# {
#   "result": <detection_result> | <ocr_text>
# }
#
# JSON data 格式（失败）：
# {
#   "error": "<error_message>"
# }
