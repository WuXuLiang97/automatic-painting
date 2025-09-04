import base64
import logging


def encrypt_password(password):
    """简单的密码加密（Base64编码）"""
    return base64.b64encode(password.encode()).decode()


def decrypt_password(encrypted):
    """解密密码"""
    try:
        return base64.b64decode(encrypted.encode()).decode()
    except:
        logging.error("密码解密失败")
        return ""
