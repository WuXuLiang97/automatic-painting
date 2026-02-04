import struct
import cv2
import traceback
import time
import socket
import json
from utils.logging_setup import logger
from utils.screenshot_util import screenshot_util


class SocketHandler:
    """
    Socket通信处理类，封装了与服务器的TCP socket通信功能
    包括连接管理、数据发送接收、以及特定的业务功能（如YOLO识别、OCR等）
    """
    def __init__(self, server_ip=None, server_port=None):
        """
        初始化SocketHandler实例
        
        Args:
            server_ip: 服务器IP地址
            server_port: 服务器端口
        """
        self.server_ip = server_ip  # 服务器IP地址
        self.server_port = server_port  # 服务器端口
        self.sock = None  # socket连接对象，初始为None
        
    def connect(self, server_ip=None, server_port=None):
        """
        连接到服务器的方法
        
        Args:
            server_ip: 服务器IP地址（可选，若不提供则使用实例初始化时的地址）
            server_port: 服务器端口（可选，若不提供则使用实例初始化时的端口）
        
        Returns:
            socket.socket or None: 成功连接的socket对象，失败则返回None
        """
        # 如果提供了新的IP或端口，更新实例属性
        if server_ip:
            self.server_ip = server_ip
        if server_port:
            self.server_port = server_port
            
        # 检查是否有有效的服务器地址和端口
        if not self.server_ip or not self.server_port:
            logger.error("缺少服务器地址或端口")
            return None
            
        server_address = (self.server_ip, self.server_port)
        # 创建TCP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(1)  # 设置1秒超时
        try:
            # 连接服务器
            self.sock.connect(server_address)
            logger.info(f"socket连接成功: {server_address}")
            return self.sock
        except Exception as e:
            # 连接失败时记录日志并返回None
            logger.info(f"socket连接失败: {e}")
            traceback.print_exc()
            self.sock = None
            return None
    
    def disconnect(self):
        """
        断开与服务器的连接并释放资源
        """
        if self.sock:
            try:
                # 安全关闭socket连接
                self.sock.close()
                logger.info("socket连接已关闭")
            except:
                # 忽略关闭过程中的异常
                pass
            # 重置socket对象为None
            self.sock = None
    
    def reconnect(self):
        """
        关闭旧连接并建立新连接的便捷方法
        
        Returns:
            socket.socket or None: 成功重新连接的socket对象，失败则返回None
        """
        if not self.server_ip or not self.server_port:
            logger.error("缺少服务器地址或端口，无法重连")
            return None
            
        # 先断开现有连接
        self.disconnect()
        # 然后尝试重新连接
        return self.connect()
    
    def send_with_retry(self, data, message):
        """
        封装发送逻辑，带自动重试机制，提高通信可靠性
        
        Args:
            data: 要发送的数据（bytes类型）
            message: 消息描述（用于日志记录）
            
        Returns:
            bool: 发送是否成功
        """
        # 检查socket是否已连接
        if not self.sock:
            logger.error("socket未连接")
            return False
            
        max_retries = 3  # 最大重试次数
        for attempt in range(max_retries):
            try:
                # 尝试发送数据
                self.sock.sendall(data)
                logger.info(f"成功发送 {message}")
                return True
            except socket.error as e:
                # 发送失败，记录日志并等待重试
                logger.info(f"发送失败（尝试 {attempt + 1}/{max_retries}）: {e}")
                traceback.print_exc()
                # 等待3秒后重试
                time.sleep(3)
        # 达到最大重试次数仍失败
        return False
    
    def _recv_exact(self, n):
        """
        确保接收指定长度的数据的内部辅助方法
        处理TCP可能的分包情况，保证准确接收n字节数据
        
        Args:
            n: 要接收的数据长度
            
        Returns:
            bytes: 接收到的完整数据
            
        Raises:
            ConnectionError: 连接意外关闭
        """
        if not self.sock:
            raise ConnectionError("socket未连接")
            
        buf = bytearray(n)  # 创建指定大小的缓冲区
        received = 0  # 已接收的数据长度
        # 循环接收直到获取完整数据
        while received < n:
            # 每次最多接收4096字节或剩余需要的字节数
            chunk = self.sock.recv(min(n - received, 4096))
            # 如果没有接收到数据，表示连接已关闭
            if not chunk:
                raise ConnectionError("连接意外关闭")
            # 将接收到的数据放入缓冲区
            buf[received:received + len(chunk)] = chunk
            received += len(chunk)
        return bytes(buf)
    
    def receive_message_from_server(self):
        """
        从服务器接收完整消息（含协议头+数据）的标准方法
        遵循固定的消息格式：4字节消息头长度 + 消息头JSON数据 + 实际业务数据
        
        Returns:
            tuple: (header_dict, data)
                   header_dict: 解析后的消息头字典
                   data: 解析后的业务数据（通常为字典）
        
        Raises:
            ConnectionError: 接收过程中连接中断
            ValueError: 协议格式错误
        """
        try:
            # 1. 接收4字节的消息头长度（大端序无符号整数）
            header_len_buf = self._recv_exact(4)
            header_len = struct.unpack('!I', header_len_buf)[0]

            # 2. 接收并解析消息头JSON数据
            header_data = self._recv_exact(header_len)
            header = json.loads(header_data.decode('utf-8'))

            # 3. 验证消息头是否包含必要字段
            if 'type' not in header or 'data_size' not in header:
                raise ValueError("无效的协议头格式")

            # 4. 接收实际业务数据
            data_size = header['data_size']
            data_buf = self._recv_exact(data_size)
            data = json.loads(data_buf.decode('utf-8'))

            return header, data

        except (OSError, json.JSONDecodeError) as e:
            # 记录详细异常信息并抛出连接异常
            logger.exception(f"接收消息失败:{e}")
            traceback.print_exc()
            raise ConnectionError("连接异常")
    
    def get_yolo_res(self, game_image=None, screenshot_util=None, process_detect_message=None):
        """
        发送游戏图像到服务器进行YOLO目标检测，并接收检测结果
        
        Args:
            game_image: 游戏图像（numpy数组，可选）
            screenshot_util: 截图工具（可选，若未提供game_image则需要）
            process_detect_message: 处理检测结果的回调函数（可选）
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 如果没有提供图像但有截图工具，则进行截图
            if game_image is None and screenshot_util:
                game_image = screenshot_util.get_game_screenshot()
            # 1. 将图像转换为JPEG格式的二进制数据
            img_bytes = cv2.imencode('.jpg', game_image)[1].tobytes()
            image_size = len(img_bytes)

            # 2. 创建消息头，指定消息类型和图像信息
            header_data = json.dumps({"type": "game_windows", "width": 1067, "height": 600, "image_size": image_size
                                      }).encode('utf-8')

            # 3. 打包消息头长度（4字节大端序整数）
            header_length = struct.pack('!I', len(header_data))

            # 4. 依次发送消息头长度、消息头和图像数据，带自动重试
            if not self.send_with_retry(header_length, "消息头长度"):
                return False

            if not self.send_with_retry(header_data, "消息头内容"):
                return False

            if not self.send_with_retry(img_bytes, f"图片数据({image_size}字节)"):
                return False

            # 接收并处理服务器返回的检测结果
            header, cls = self.receive_message_from_server()
            if header["type"] == "game_windows" and process_detect_message:
                process_detect_message(cls, game_image)

        except Exception as e:
            # 捕获所有异常并记录
            logger.exception(f"获取YOLO识别结果时发生异常: {e}")
            traceback.print_exc()
            return False

        return True
    
    def get_text(self, x1, y1, x2, y2, img_numpy=None, amplify=False):
        """
        对指定区域进行OCR文本识别
        
        Args:
            x1, y1, x2, y2: 识别区域的坐标（左上角和右下角）
            img_numpy: 原始图像（numpy数组，可选）
            amplify: 是否放大图像以提高识别率（可选，默认为False）
            
        Returns:
            str: 识别的文本，失败则返回空字符串
        """
        try:
            # 获取识别区域的图像
            if img_numpy is not None:
                game_image = img_numpy[y1:y2, x1:x2]
            else:
                # 如果未提供图像，使用全局screenshot_util获取游戏截图
                img_numpy = screenshot_util.get_game_screenshot()
                game_image = img_numpy[y1:y2, x1:x2]
            
            # 根据需要放大图像以提高OCR识别率
            if amplify:
                # 定义缩放比例
                scale_factor = 1.5

                # 计算新尺寸
                new_width = int(game_image.shape[1] * scale_factor)
                new_height = int(game_image.shape[0] * scale_factor)
                new_size = (new_width, new_height)

                # 按比例放大图像
                game_image = cv2.resize(game_image, new_size, interpolation=cv2.INTER_LINEAR)
            
            # 将图像转换为灰度图以提高OCR效果
            _image_rgb = cv2.cvtColor(game_image, cv2.COLOR_BGR2GRAY)
            # 转换为JPEG二进制数据
            img_bytes = cv2.imencode('.jpg', _image_rgb)[1].tobytes()
            image_size = len(img_bytes)

            # 创建并发送OCR请求
            header_data = json.dumps({"type": "ocr", "width": 1, "height": 1, "image_size": image_size
                                      }).encode('utf-8')
            header_length = struct.pack('!I', len(header_data))

            # 依次发送消息头长度、消息头和图像数据
            if not self.send_with_retry(header_length, "OCR消息头长度"):
                return ''

            if not self.send_with_retry(header_data, "OCR消息头内容"):
                return ''

            if not self.send_with_retry(img_bytes, f"OCR图片数据({image_size}字节)"):
                return ''

            # 接收并返回OCR识别结果
            header, response = self.receive_message_from_server()
            if header["type"] == "ocr":
                logger.info(f"OCR已获取识别数据: {response}")

        except Exception as e:
            logger.exception(f"OCR识别过程中发生异常:{e}")
            traceback.print_exc()
            return ''

        return response
    
    def get_min_map_yolo_res(self, miniMapUtil=None, player_map_name=None, min_map_process_detect_message=None):
        """
        发送小地图图像到服务器进行YOLO目标检测，并接收检测结果
        
        Args:
            miniMapUtil: 小地图工具（用于捕获小地图，可选但建议提供）
            player_map_name: 玩家当前地图名称（可选但建议提供）
            min_map_process_detect_message: 处理检测结果的回调函数（可选）
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 捕获小地图图像
            if miniMapUtil and player_map_name:
                min_map = miniMapUtil.min_map_capture(player_map_name)
            else:
                logger.error("缺少必要的小地图捕获参数")
                return False
            
            # 转换小地图图像为二进制数据
            img_bytes = cv2.imencode('.jpg', min_map)[1].tobytes()
            image_size = len(img_bytes)

            # 创建并发送小地图识别请求
            header_data = json.dumps({"type": "min_map", "width": 1, "height": 1, "image_size": image_size
                                      }).encode('utf-8')
            header_length = struct.pack('!I', len(header_data))

            # 依次发送消息头长度、消息头和图像数据
            if not self.send_with_retry(header_length, "小地图消息头长度"):
                return False

            if not self.send_with_retry(header_data, "小地图消息头内容"):
                return False

            if not self.send_with_retry(img_bytes, f"小地图图片数据({image_size}字节)"):
                return False

            # 接收并处理服务器返回的检测结果
            header, cls = self.receive_message_from_server()
            if header["type"] == "min_map" and min_map_process_detect_message:
                logger.info(f"小地图YOLO已获取识别数据: {cls}")
                min_map_process_detect_message(cls)

        except Exception as e:
            logger.exception(f"获取小地图YOLO识别结果时发生异常:{e}")
            traceback.print_exc()
            return False

        return True

# ==================================================
# 以下代码为了保持向后兼容性，提供了全局实例和原函数的包装
# 不建议在新代码中使用这些全局函数，而应该直接实例化SocketHandler类
# ==================================================

# 创建全局的SocketHandler实例
socket_handler = SocketHandler()


# 以下是兼容旧版代码的全局函数包装
def sock_connect(server_ip, server_port):
    """兼容旧版的socket连接函数"""
    return socket_handler.connect(server_ip, server_port)

def send_with_retry(sock, data, message):
    """兼容旧版的带重试发送函数"""
    # 注意：这里使用传入的sock，而不是socket_handler实例的sock
    # 这是为了保持与原函数的兼容性
    temp_handler = SocketHandler()
    temp_handler.sock = sock
    return temp_handler.send_with_retry(data, message)

def _reconnect(sock, server_ip, server_port):
    """兼容旧版的重连函数"""
    handler = SocketHandler(server_ip, server_port)
    handler.sock = sock
    return handler.reconnect()

def _recv_exact(sock, n):
    """兼容旧版的精确接收函数"""
    temp_handler = SocketHandler()
    temp_handler.sock = sock
    return temp_handler._recv_exact(n)

def receive_message_from_server(sock):
    """兼容旧版的接收服务器消息函数"""
    temp_handler = SocketHandler()
    temp_handler.sock = sock
    return temp_handler.receive_message_from_server()

def get_yolo_res(sock, game_image=None, screenshot_util=None, process_detect_message=None):
    """兼容旧版的获取YOLO识别结果函数"""
    temp_handler = SocketHandler()
    temp_handler.sock = sock
    return temp_handler.get_yolo_res(game_image, screenshot_util, process_detect_message)

def get_text(sock, x1, y1, x2, y2, img_numpy=None, amplify=False):
    """兼容旧版的OCR文本识别函数"""
    temp_handler = SocketHandler()
    temp_handler.sock = sock
    return temp_handler.get_text(x1, y1, x2, y2, img_numpy, amplify)

def get_min_map_yolo_res(sock, miniMapUtil=None, player_map_name=None, min_map_process_detect_message=None):
    """兼容旧版的获取小地图YOLO识别结果函数"""
    temp_handler = SocketHandler()
    temp_handler.sock = sock
    return temp_handler.get_min_map_yolo_res(miniMapUtil, player_map_name, min_map_process_detect_message)