# -*- coding: utf-8 -*-
"""
Socket客户端模块
负责处理与服务器的Socket通信
"""
import socket
import json
import struct
import time
from utils.logging_setup import logger

class SocketClient:
    def __init__(self):
        self.sock = None
        self.connected = False
        self.server_ip = None
        self.server_port = None
    
    def connect(self, server_ip, server_port):
        """连接到服务器"""
        try:
            self.server_ip = server_ip
            self.server_port = server_port
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((server_ip, server_port))
            self.sock.settimeout(1)
            self.connected = True
            logger.info(f"已连接到服务器: {server_ip}:{server_port}")
            return True
        except Exception as e:
            logger.error(f"Socket连接失败: {str(e)}")
            self.connected = False
            return False
    
    def disconnect(self):
        """断开连接"""
        try:
            if self.sock:
                self.sock.close()
                self.sock = None
            self.connected = False
            logger.info("Socket连接已断开")
        except Exception as e:
            logger.error(f"断开Socket连接时发生异常: {str(e)}")
    
    def send_message(self, message_type, data):
        """发送消息到服务器"""
        try:
            if not self.connected or not self.sock:
                logger.warning("Socket未连接，无法发送消息")
                return False
            
            # 构建消息体
            message = {
                'type': message_type,
                'data': data
            }
            
            # 序列化并发送
            message_json = json.dumps(message)
            self.sock.sendall(message_json.encode('utf-8'))
            return True
        except Exception as e:
            logger.error(f"发送消息时发生异常: {str(e)}")
            self.connected = False
            return False
    
    def receive_message(self, buffer_size=4096):
        """接收服务器消息"""
        try:
            if not self.connected or not self.sock:
                logger.warning("Socket未连接，无法接收消息")
                return None
            
            data = self.sock.recv(buffer_size)
            if not data:
                self.connected = False
                return None
            
            return json.loads(data.decode('utf-8'))
        except Exception as e:
            logger.error(f"接收消息时发生异常: {str(e)}")
            self.connected = False
            return None

# 提供一个默认的实例
socket_client = SocketClient()