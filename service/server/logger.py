import logging
import os
import sys
from logging import Logger

_LOGGER: Logger | None = None

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'log')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'server.log')


def get_logger() -> Logger:
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER

    logger = logging.getLogger('app_server')
    logger.setLevel(logging.INFO)
    logger.propagate = False  # 避免重复输出

    # 控制台/GUI handler -> stdout (PrintRedirector 会接管 stdout)
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    # 文件 handler
    fh = logging.FileHandler(LOG_FILE, encoding='utf-8')
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    logger.addHandler(sh)
    logger.addHandler(fh)

    _LOGGER = logger
    return logger
