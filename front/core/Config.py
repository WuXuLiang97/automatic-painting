# -*- coding: utf-8 -*-
import json
import os

from PyQt5.QtCore import Qt

from root_dir import root_path
from utils.logging_setup import logger

DEFAULT_KEY_CONFIG = {
    'one_key_gather': {'key': 'Tab'},
    'move_character': {'key': 'W'},
    'back_to_selia': {'key': 'R'},
    'challenge_again': {'key': 'F10'},
    'skills': [
        ['Q', 'W', 'E', 'R', 'T', 'Y', 'Ctrl'],
        ['A', 'S', 'D', 'F', 'G', 'H', 'Alt']
    ]
}


FORBIDDEN_KEYS = {
    Qt.Key_End: 'End',
    Qt.Key_Home: 'Home',
}

default_config = {
        "ip": "192.168.1.1",
        "yjs": 0,
        "banzhuan": 0,
        "vmware_ip": "127.0.0.1",
        "vmware_prot": "5900",
        "vmware_password": "",
        "tab_index": 0,
        'vid': '',
        'pid': '',
        'identifier': "0",
        'weak_setting': 'gold',  # 添加虚弱设置，默认为金币恢复
        'wait_seconds': 30,  # 添加等待秒数，默认30秒
    }
def get_gui_config():
    """获取GUI配置"""
    # 默认配置

    try:
        # 如果配置文件存在，读取它
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r', encoding='utf-8') as file:
                file_config = json.load(file)
                # 合并默认配置和文件配置
                return {**default_config, **file_config}

        # 如果配置文件不存在，创建默认配置
        with open(CONFIG_PATH, 'w', encoding='utf-8') as file:
            json.dump(default_config, file, indent=4, ensure_ascii=False)
        return default_config

    except json.JSONDecodeError:
        print("Warning: Config file is corrupted or not in JSON format.")
        return default_config
    except Exception as e:
        print(f"Error loading config: {e}")
        return default_config

def get_key_config():
    try:
        if os.path.exists(key_config_file):
            with open(key_config_file, 'r', encoding='utf-8') as f:
                key_config = json.load(f)

                logger.info(f"成功加载键盘配置: {key_config_file}")
        else:
            logger.warning(f"键盘配置文件不存在: {key_config_file}，使用默认配置")
            key_config = DEFAULT_KEY_CONFIG
    except Exception as e:
        logger.error(f"加载键盘配置失败: {e}，使用默认配置")
        key_config = DEFAULT_KEY_CONFIG
    return key_config


target_dir = os.path.join(root_path, "json_resources")
CONFIG_PATH = os.path.join(root_path, "json_resources/config.json")# 拼接子目录
key_config_file = os.path.join(target_dir, "key_config.json")

 # 拼接子目录
# 用户数据存储文件
USER_DATA_FILE = os.path.join(target_dir, 'users.json')
# 记住密码的配置文件
REMEMBER_FILE = os.path.join(target_dir, 'remember.json')