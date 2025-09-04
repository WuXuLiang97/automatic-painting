import json
import logging
import os
from config import BASE_URL, REMEMBER_FILE
from utils.user.pwd import decrypt_password, encrypt_password
import time
import requests


def load_remembered_user():
    """加载记住的用户信息"""
    if not os.path.exists(REMEMBER_FILE):
        logging.debug("没有找到记住密码文件")
        return None
    try:
        with open(REMEMBER_FILE, "r") as f:
            data = json.load(f)
            logging.debug(f"从文件加载记住的用户: {data['username']}")
            data["password"] = decrypt_password(data["password"])
            return data
    except Exception as e:
        logging.error(f"加载记住的用户失败: {str(e)}")
        return None


def save_remembered_user(username, password, remember, auto_login):
    """保存记住的用户信息"""
    try:
        if remember:
            encrypted = encrypt_password(password)
            data = {
                "username": username,
                "password": encrypted,
                "remember": remember,
                "auto_login": auto_login,
            }
            with open(REMEMBER_FILE, "w") as f:
                json.dump(data, f)
            logging.debug(f"保存记住的用户: {username}, 自动登录: {auto_login}")
        else:
            if os.path.exists(REMEMBER_FILE):
                os.remove(REMEMBER_FILE)
                logging.debug("删除记住密码文件")
    except Exception as e:
        logging.error(f"保存记住的用户失败: {str(e)}")


def update_remembered_auto_login(username, new_auto_login_state):
    """仅更新 remember.json 中的 auto_login 字段"""
    if not os.path.exists(REMEMBER_FILE):
        logging.warning("记住密码文件不存在，无法更新 auto_login")
        return False
    try:
        with open(REMEMBER_FILE, "r") as f:
            data = json.load(f)
        if data.get("username") != username:
            logging.warning(f"用户名不匹配，无法更新 {username} 的 auto_login")
            return False
        data["auto_login"] = new_auto_login_state
        with open(REMEMBER_FILE, "w") as f:
            json.dump(data, f)
        logging.debug(f"更新 {username} 的 auto_login 为: {new_auto_login_state}")
        return True
    except Exception as e:
        logging.error(f"更新 auto_login 失败: {str(e)}")
        return False
