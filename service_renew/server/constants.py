# -*- coding: utf-8 -*-
"""
服务器常量定义
集中管理所有硬编码值，便于维护和配置
"""

# ==================== 网络和安全限制 ====================

# 图像大小限制（50MB，防止内存溢出攻击）
MAX_IMAGE_SIZE = 50 * 1024 * 1024

# JSON 头部最大大小（1MB）
MAX_HEADER_SIZE = 1024 * 1024

# 最大并发连接数
MAX_CONNECTIONS = 100

# 有效的请求类型
VALID_REQUEST_TYPES = {"game_windows", "min_map", "ocr"}

# Socket 接收块大小（字节）
SOCKET_CHUNK_SIZE = 8192

# Socket 接收超时时间（秒）
SOCKET_RECV_TIMEOUT = None  # 默认无超时

# ==================== 统计指标 ====================

# 统计报告间隔（秒）
METRICS_REPORT_INTERVAL = 10

# P95 计算的最小样本数
METRICS_P95_MIN_SAMPLES = 20

# P95 百分位数
METRICS_P95_PERCENTILE = 0.95

# 延迟统计的最大样本数（deque maxlen）
METRICS_MAX_SAMPLES = 200

# ==================== OCR 相关常量 ====================

# 检测阶段二值化阈值
OCR_DET_BIN_THRESH = 0.2

# 检测阶段框阈值
OCR_DET_BOX_THRESH = 0.50

# 检测阶段外扩比例
OCR_DET_UNCLIP_RATIO = 1.60

# Paddle 风格评分阈值（低于此值的文本可忽略）
OCR_PADDLE_SCORE_THRESH = 0.85

# 识别阶段最大宽度（保护性限制，防极宽文本占用内存）
OCR_MAX_REC_WIDTH = 320

# 检测阶段最小边长度（小于此值的图片先放大，避免过小导致丢字）
OCR_MIN_DET_SIDE = 256

# 检测阶段最大边长度限制
OCR_DET_LIMIT_SIDE_LEN = 960

# 识别阶段图像高度
OCR_REC_IMG_HEIGHT = 48

# 图像对齐倍数（DB 模型通常下采样 32）
OCR_ALIGN_MULTIPLE = 32

# ==================== 图像处理 ====================

# 图像归一化均值（ImageNet 标准）
IMAGE_NORMALIZE_MEAN = [0.485, 0.456, 0.406]

# 图像归一化标准差（ImageNet 标准）
IMAGE_NORMALIZE_STD = [0.229, 0.224, 0.225]

# ==================== 服务器主循环 ====================

# 主循环休眠时间（秒）
MAIN_LOOP_SLEEP = 0.2

# ==================== 线程池和队列 ====================

# 默认最大工作线程数（如果配置文件中未指定）
DEFAULT_MAX_WORKERS = 4

# 默认任务队列大小（如果配置文件中未指定）
DEFAULT_TASK_QUEUE_SIZE = 50
