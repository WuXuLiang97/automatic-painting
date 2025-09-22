import os

from PyQt5.QtCore import Qt

from root_dir import root_path

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

target_dir = os.path.join(root_path, "json_resources")
CONFIG_PATH = os.path.join(root_path, "json_resources/config.json")# 拼接子目录
key_config_file = os.path.join(target_dir, "key_config.json")

 # 拼接子目录
# 用户数据存储文件
USER_DATA_FILE = os.path.join(target_dir, 'users.json')
# 记住密码的配置文件
REMEMBER_FILE = os.path.join(target_dir, 'remember.json')