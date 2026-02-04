import json
import time
import logging
from PyQt5.QtCore import pyqtSignal, QObject

# 设置日志
logger = logging.getLogger(__name__)

class CommunicationService(QObject):
    """通信服务类，封装所有网络通信逻辑"""
    
    # 定义信号用于消息通知
    connection_established = pyqtSignal()  # 连接建立信号
    connection_lost = pyqtSignal()         # 连接丢失信号
    message_received = pyqtSignal(object)  # 接收到消息信号
    
    def __init__(self, server_ip=None, server_port=None, message_signal=None):
        """
        初始化通信服务
        
        Args:
            server_ip: 服务器IP地址
            server_port: 服务器端口
            message_signal: 可选，用于发送消息的信号
        """
        super().__init__()
        self.server_ip = server_ip
        self.server_port = server_port
        self.message_signal = message_signal
        self.is_connected = False
        self.socket_handler = None
        
    def set_socket_handler(self, socket_handler):
        """设置SocketHandler实例"""
        self.socket_handler = socket_handler
    
    def connect_server(self, server_ip=None, server_port=None):
        """连接到YOLO识别服务器"""
        try:
            # 使用传入的参数或初始化时的参数
            if server_ip:
                self.server_ip = server_ip
            if server_port:
                self.server_port = server_port
            
            if not self.socket_handler:
                logger.error("SocketHandler实例未设置")
                return None
            
            sock = self.socket_handler.connect(self.server_ip, self.server_port)
            if sock:
                self.is_connected = True
                self.connection_established.emit()
                logger.info(f"成功连接到YOLO服务器: {self.server_ip}:{self.server_port}")
                return sock
            else:
                logger.error(f"连接YOLO服务器失败: {self.server_ip}:{self.server_port}")
                return None
        except Exception as e:
            logger.error(f"连接服务器时发生异常: {e}")
            return None
    
    def disconnect_server(self):
        """断开与服务器的连接"""
        try:
            if self.socket_handler and hasattr(self.socket_handler, 'disconnect'):
                self.socket_handler.disconnect()
                self.is_connected = False
                self.connection_lost.emit()
                logger.info("已断开与YOLO服务器的连接")
        except Exception as e:
            logger.error(f"断开连接时发生异常: {e}")
    
    def reconnect(self):
        """重新连接服务器"""
        try:
            if self.socket_handler and hasattr(self.socket_handler, 'reconnect'):
                result = self.socket_handler.reconnect()
                if result:
                    self.is_connected = True
                    self.connection_established.emit()
                    logger.info("成功重新连接到YOLO服务器")
                return result
        except Exception as e:
            logger.error(f"重连时发生异常: {e}")
        return False
    
    def send_with_retry(self, data, message):
        """带重试机制发送数据到服务器"""
        try:
            if self.socket_handler and hasattr(self.socket_handler, 'send_with_retry'):
                return self.socket_handler.send_with_retry(data, message)
            else:
                logger.error("socket_handler没有send_with_retry方法")
                return False
        except Exception as e:
            logger.error(f"发送数据时发生异常: {e}")
            return False
    
    def _recv_exact(self, n):
        """接收指定长度的数据"""
        try:
            if self.socket_handler and hasattr(self.socket_handler, '_recv_exact'):
                return self.socket_handler._recv_exact(n)
            else:
                logger.error("socket_handler没有_recv_exact方法")
                return None
        except Exception as e:
            logger.error(f"接收数据时发生异常: {e}")
            return None
    
    def receive_message_from_server(self):
        """接收来自服务器的完整消息"""
        try:
            if self.socket_handler and hasattr(self.socket_handler, 'receive_message_from_server'):
                result = self.socket_handler.receive_message_from_server()
                if result:
                    # 解包结果（假设返回(header, content)元组）
                    if len(result) >= 2:
                        self.message_received.emit(result[1])
                return result
            else:
                logger.error("socket_handler没有receive_message_from_server方法")
                return (None, None)
        except Exception as e:
            logger.error(f"接收服务器消息时发生异常: {e}")
            return (None, None)
    
    def get_yolo_res(self, game_image=None, screenshot_util=None, process_detect_message=None):
        """获取游戏窗口YOLO识别结果"""
        try:
            if self.socket_handler and hasattr(self.socket_handler, 'get_yolo_res'):
                return self.socket_handler.get_yolo_res(game_image, screenshot_util, process_detect_message)
            else:
                logger.error("socket_handler没有get_yolo_res方法")
                return False
        except Exception as e:
            logger.error(f"获取YOLO识别结果时发生异常: {e}")
            return False
    
    def get_text(self, x1, y1, x2, y2, img_numpy=None, amplify=False):
        """OCR文本识别"""
        try:
            if self.socket_handler and hasattr(self.socket_handler, 'get_text'):
                return self.socket_handler.get_text(x1, y1, x2, y2, img_numpy, amplify)
            else:
                logger.error("socket_handler没有get_text方法")
                return ''
        except Exception as e:
            logger.error(f"OCR文本识别时发生异常: {e}")
            return ''
    
    def get_min_map_yolo_res(self, miniMapUtil=None, player_map_name=None, min_map_process_detect_message=None):
        """获取小地图YOLO识别结果"""
        try:
            if self.socket_handler and hasattr(self.socket_handler, 'get_min_map_yolo_res'):
                return self.socket_handler.get_min_map_yolo_res(miniMapUtil, player_map_name, min_map_process_detect_message)
            else:
                logger.error("socket_handler没有get_min_map_yolo_res方法")
                return False
        except Exception as e:
            logger.error(f"获取小地图YOLO识别结果时发生异常: {e}")
            return False
    
    def check_connection(self):
        """检查连接状态"""
        return self.is_connected
    
    def execute_with_retry(self, func, max_retries=3, delay=1):
        """
        执行函数并在失败时重试
        
        Args:
            func: 要执行的函数
            max_retries: 最大重试次数
            delay: 重试间隔(秒)
        
        Returns:
            函数执行结果或None（如果所有重试都失败）
        """
        retries = 0
        while retries < max_retries:
            try:
                result = func()
                if result:
                    return result
            except Exception as e:
                logger.warning(f"函数执行失败，准备重试 ({retries+1}/{max_retries}): {e}")
            
            retries += 1
            if retries < max_retries:
                time.sleep(delay)
                # 尝试重新连接
                if self.socket_handler and hasattr(self.socket_handler, 'reconnect'):
                    try:
                        self.socket_handler.reconnect()
                    except Exception as e:
                        logger.error(f"重连失败: {e}")
        
        logger.error(f"函数执行失败，已达到最大重试次数 ({max_retries})")
        return None