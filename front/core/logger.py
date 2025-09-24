import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from front.config import LOG_PATH, OUTPUTLOG, DEBUG_MODE  # 已在 config 中加入 DEBUG_MODE
from root_dir import root_path

_INITIALIZED = False

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(threadName)s | %(name)s:%(lineno)d | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _coerce_bool(v, default=False):
    if isinstance(v, bool):
        return v
    if v is None:
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "on")


def init_logging(force: bool = False, level: int | None = None):
    """初始化全局日志系统（幂等）。
    force=True 时重新初始化（会先清空 root logger handlers）。
    level 可强制覆盖日志级别；否则根据 DEBUG_MODE 自动选择 DEBUG / INFO。
    """
    global _INITIALIZED
    if _INITIALIZED and not force:
        return

    root_logger = logging.getLogger()
    if force:
        for h in list(root_logger.handlers):
            root_logger.removeHandler(h)
    elif root_logger.handlers:
        # 已经外部 basicConfig 过
        _INITIALIZED = True
        return

    # 级别判定
    log_level = level if level is not None else (logging.DEBUG if DEBUG_MODE else logging.INFO)
    root_logger.setLevel(log_level)

    # 处理日志路径
    log_path = LOG_PATH
    if not os.path.isabs(log_path):
        log_path = os.path.join(root_path, log_path)
    log_dir = os.path.dirname(log_path)
    os.makedirs(log_dir, exist_ok=True)

    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)

    # 控制台 Handler（stdout，便于被 GUI 捕获）
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(log_level)
    sh.setFormatter(formatter)
    root_logger.addHandler(sh)

    # 文件 Handler（可滚动）
    if _coerce_bool(OUTPUTLOG, True):
        try:
            fh = RotatingFileHandler(log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8')
            fh.setLevel(log_level)
            fh.setFormatter(formatter)
            root_logger.addHandler(fh)
        except Exception as e:
            root_logger.error("创建文件日志处理器失败: %s", e)

    # 附加：简短启动标记
    root_logger.debug("日志系统初始化完成 | DEBUG_MODE=%s | LOG_PATH=%s", DEBUG_MODE, log_path)

    _INITIALIZED = True


def get_logger(name: str | None = None) -> logging.Logger:
    """获取命名 logger，确保已经初始化。"""
    if not _INITIALIZED:
        init_logging()
    return logging.getLogger(name)


if __name__ == "__main__":
    init_logging(force=True)
    log = get_logger(__name__)
    log.info("Logger self-test OK")
    log.debug("Debug line visible when DEBUG_MODE=True")