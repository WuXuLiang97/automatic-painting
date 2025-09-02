from configparser import ConfigParser
import os

def load_ini_config(config_path):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件 {config_path} 不存在")
    
    # 初始化配置解析器
    config = ConfigParser()
    config.read(config_path, encoding="utf-8")  # 读取 INI 文件
    return config

# 加载配置
config = load_ini_config("工具人.ini")

SERVER_HOST = config.get("SERVER", "host", fallback="0.0.0.0")  # 服务器地址，默认
SERVER_PORT = config.getint("SERVER", "port", fallback=12345)  # 服务器端口，默认12345


# 全局配置
MAX_WORKERS = 4  # 工作线程数量（根据CPU核心数调整，提高并发处理能力）
TASK_QUEUE_SIZE = 20  # 任务队列最大缓冲量（避免请求堆积溢出）
MODEL_WARMUP = True  # 模型预热开关（提前加载模型，减少首次推理延迟）
