from configparser import ConfigParser
import json
import os
from pathlib import Path
from root_dir import root_path


def load_ini_config(config_path):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件 {config_path} 不存在")

    # 初始化配置解析器
    config = ConfigParser()
    config.read(config_path, encoding="utf-8")  # 读取 INI 文件
    return config


def load_json_config(config_path="config.json"):
    """
    读取JSON配置文件，返回解析后的字典（包含列表和嵌套字典）
    :param config_path: JSON配置文件路径
    :return: 配置字典，结构与原数据一致
    """
    try:
        # 检查文件是否存在
        if not Path(config_path).exists():
            raise FileNotFoundError(f"配置文件不存在：{config_path}")

        # 读取并解析JSON
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)  # 直接返回Python字典/列表结构

        # 验证配置是否完整（可选，根据需求添加）
        required_keys = ["map_levels", "map_names", "player_types", "player_jobs"]
        for key in required_keys:
            if key not in config:
                raise ValueError(f"配置文件缺少必要键：{key}")

        return config

    except Exception as e:
        print(f"加载配置失败：{str(e)}")
        return None


# 加载配置
config = load_ini_config("工具人.ini")
json_config = load_json_config(os.path.join(root_path, "json_resources", "game.json"))

OUTPUTLOG = config.get("LOG", "output", fallback=True)
LOG_PATH = config.get("LOG", "log_path", fallback="log/app_log.txt")  # 日志文件路径

FONT_FILE = config.get("UI", "font_file", fallback="Arial.ttf")  # 界面字体文件

BASE_URL = config.get(
    "ENV", "base_url", fallback="http://39.98.46.105:5001"
)  # 服务器地址，默认

CONFIG_PATH = os.path.join(
    root_path,
    config.get("CONFIG", "config_path", fallback="json_resources/config.json"),
)
# 用户数据存储文件
USER_DATA_FILE = os.path.join(
    root_path,
    config.get("CONFIG", "user_data_file", fallback="json_resources/users.json"),
)
# 记住密码的配置文件
REMEMBER_FILE = os.path.join(
    root_path,
    config.get("CONFIG", "login_data_file", fallback="json_resources/remember.json"),
)

MOVE_GOODS = config.get("CONFIG", "move_goods_key", fallback="caplk")  # 移动物品按键

f_program_version = config.get("ENV", "version", fallback="1.0.0.0")  # 程序版本号

map_levels = json_config.get("map_levels", [])
map_names = json_config.get("map_names", [])
player_types = json_config.get("player_types", [])
player_jobs = json_config.get("player_jobs", {})
