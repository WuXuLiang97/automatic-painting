import logging
import os
import sys
from logging import Logger

_LOGGERS: dict[str, Logger] = {}

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'log')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'server.log')


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器"""
    COLORS = {
        'DEBUG': '\033[94m',    # Blue
        'INFO': '\033[92m',     # Green
        'WARNING': '\033[93m',  # Yellow
        'ERROR': '\033[91m',    # Red
        'CRITICAL': '\033[95m', # Magenta
        'RESET': '\033[0m'      # Reset color
    }

    def format(self, record):
        log_message = super().format(record)
        return f"{self.COLORS.get(record.levelname, self.COLORS['RESET'])}{log_message}{self.COLORS['RESET']}"


def get_logger(name: str = 'app_server') -> Logger:
    """
    获取日志记录器
    
    Args:
        name: 日志记录器名称
    
    Returns:
        Logger 实例
    """
    if name in _LOGGERS:
        return _LOGGERS[name]

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # 设置为 DEBUG 以捕获所有级别
    logger.propagate = False  # 避免重复输出

    # 控制台/GUI handler -> stdout (PrintRedirector 会接管 stdout)
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.DEBUG)  # 设置为 DEBUG 确保所有级别都传递到 PrintRedirector
    sh.setFormatter(ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s'))

    # 文件 handler
    fh = logging.FileHandler(LOG_FILE, encoding='utf-8')
    fh.setLevel(logging.INFO)  # 文件日志可以是 INFO 或更高
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))

    logger.addHandler(sh)
    logger.addHandler(fh)

    _LOGGERS[name] = logger
    return logger
