import json
import struct
from utils.logging_setup import logger
import traceback
import socket
import global_variable as gv

class Socket_Handler:
    def __init__(self):
        pass

    def sock_connect(self):
        """
        连接socket
        :return: 
        """
        server_address = (gv.server_ip, gv.server_port)
        logger.info(server_address)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(server_address)
        self.sock.settimeout(1)
        self.sock_connect_flags = True
        logger.info(self.sock)        
        
    def receive_message_from_server(self):
        """
        从服务器接收完整消息（含协议头+数据）

        返回:
            tuple: (header_dict, data_bytes)
                   header_dict: 解析后的消息头字典
                   data_bytes: 原始数据字节流
        异常:
            ConnectionError: 接收过程中连接中断
            ValueError: 协议格式错误
        """

        try:
            # 接收消息头长度
            header_len_buf = self._recv_exact(4)
            header_len = struct.unpack('!I', header_len_buf)[0]

            # 接收并解析消息头
            header_data = self._recv_exact(header_len)
            header = json.loads(header_data.decode('utf-8'))

            # 验证必要字段
            if 'type' not in header or 'data_size' not in header:
                raise ValueError("无效的协议头格式")

            # 接收实际数据
            data_size = header['data_size']
            data_buf = self._recv_exact(data_size)
            data = json.loads(data_buf.decode('utf-8'))

            return header, data

        except (OSError, json.JSONDecodeError) as e:
            logger.exception(f"接收消息失败:{e}")
            traceback.print_exc()
            raise ConnectionError("连接异常")

    def _recv_exact(self, n):
        """确保接收指定长度的数据"""
        buf = bytearray(n)
        received = 0
        while received < n:
            chunk = self.sock.recv(min(n - received, 4096))
            if not chunk:
                raise ConnectionError("连接意外关闭")
            buf[received:received + len(chunk)] = chunk
            received += len(chunk)
        return bytes(buf)
