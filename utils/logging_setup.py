import os

from loguru import logger
from root_dir import root_path

app_log_path = os.path.join(root_path, "log", "app.log")
# 确保日志目录存在
log_dir = os.path.dirname(app_log_path)
os.makedirs(log_dir, exist_ok=True)  # 如果路径不存在则创建，exist_ok=True 避免路径已存在时报错

# 配置异步文件日志（自动轮转）
logger.add(
    app_log_path,
    rotation="2 MB",  # 按大小轮转
    enqueue=True,  # 启用异步队列
    compression="zip",  # 压缩旧日志
    format="{time} - {level} - {message}"
)
