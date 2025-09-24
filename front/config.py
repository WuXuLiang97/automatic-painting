from configparser import ConfigParser
import json
import os
from pathlib import Path
from dataclasses import dataclass
from functools import lru_cache
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


# 加载配置（保持旧的模块级变量以向后兼容）
config = load_ini_config("工具人.ini")
json_config = load_json_config(os.path.join(root_path, "json_resources", "game.json"))

OUTPUTLOG = config.get("LOG", "output", fallback=True)
LOG_PATH = config.get("LOG", "log_path", fallback="log/app_log.txt")  # 日志文件路径

FONT_FILE = config.get("UI", "font_file", fallback="Arial.ttf")  # 界面字体文件

BASE_URL = config.get(
    "ENV", "base_url", fallback=os.environ.get("DXF_BASE_URL", "http://39.98.46.105:5001")
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

# 新增：统一调试开关（供日志模块、性能分析等使用）
# 支持 ini 中 [ENV] debug = True/False
try:
    DEBUG_MODE = config.getboolean("ENV", "debug", fallback=False)
except ValueError:
    # 兼容写成字符串"True"/"False"以外的值
    DEBUG_MODE = str(config.get("ENV", "debug", fallback="False")).lower() in ("1", "true", "yes", "on")

map_levels = json_config.get("map_levels", []) if json_config else []
map_names = json_config.get("map_names", []) if json_config else []
player_types = json_config.get("player_types", []) if json_config else []
player_jobs = json_config.get("player_jobs", {}) if json_config else {}

# ---- New unified configuration access layer ----
@dataclass(frozen=True)
class AppConfig:
    base_url: str
    version: str
    debug: bool
    font_file: str
    log_path: str
    paths: dict
    move_goods_key: str


def _abs(p: str) -> str:
    if os.path.isabs(p):
        return p
    return os.path.join(root_path, p)


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    return AppConfig(
        base_url=BASE_URL,
        version=f_program_version,
        debug=DEBUG_MODE,
        font_file=_abs(FONT_FILE),
        log_path=_abs(LOG_PATH),
        move_goods_key=MOVE_GOODS,
        paths={
            "config_json": _abs(CONFIG_PATH),
            "user_data": _abs(USER_DATA_FILE),
            "remember": _abs(REMEMBER_FILE),
            "root": root_path,
            "json_resources": _abs("json_resources"),
            "images": _abs("Images"),
        },
    )


def resolve_path(*parts: str, create: bool = False) -> str:
    """Resolve a path relative to root_path. Optionally create parent directory."""
    full = os.path.join(root_path, *parts)
    if create:
        os.makedirs(os.path.dirname(full), exist_ok=True)
    return full


__all__ = [
    # legacy exports
    "OUTPUTLOG", "LOG_PATH", "FONT_FILE", "BASE_URL", "CONFIG_PATH", "USER_DATA_FILE", "REMEMBER_FILE",
    "MOVE_GOODS", "f_program_version", "DEBUG_MODE", "map_levels", "map_names", "player_types", "player_jobs",
    # new API
    "AppConfig", "get_config", "resolve_path",
]
