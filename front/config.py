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

OUTPUTLOG = config.get("LOG", "output", fallback=True)  # 服务器地址，默认
LOG_PATH = config.get("LOG", "log_path", fallback="logs/app_log.txt")  # 日志文件路径
