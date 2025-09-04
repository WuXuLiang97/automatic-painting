import json
import os

from config import CONFIG_PATH
from static_fields import DEFAULT_GUI_CONFIG


def get_gui_config():
    """获取GUI配置"""
    # 默认配置

    try:
        # 如果配置文件存在，读取它
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as file:
                file_config = json.load(file)
                # 合并默认配置和文件配置
                return {**DEFAULT_GUI_CONFIG, **file_config}

        # 如果配置文件不存在，创建默认配置
        with open(CONFIG_PATH, "w", encoding="utf-8") as file:
            json.dump(DEFAULT_GUI_CONFIG, file, indent=4, ensure_ascii=False)
        return DEFAULT_GUI_CONFIG

    except json.JSONDecodeError:
        print("Warning: Config file is corrupted or not in JSON format.")
        return DEFAULT_GUI_CONFIG
    except Exception as e:
        print(f"Error loading config: {e}")
        return DEFAULT_GUI_CONFIG
