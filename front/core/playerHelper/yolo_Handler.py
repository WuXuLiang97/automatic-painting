import cv2
import json
import struct
from utils.logging_setup import logger
from utils.screenshot_util import screenshot_util
import socket_Handler

class Yolo_Handler:
    def __init__(self, player_thread):
        self.player_thread = player_thread
        self.socket_Handler = socket_Handler.Socket_Handler(self.player_thread.sock)
        
    def get_yolo_res(self, game_image=None):
        try:
            logger.info(f"进入 get_yolo_res")
            if game_image is None:
                # st = time.time()
                logger.info(f"开始截图")
                game_image = screenshot_util.get_game_screenshot()  # logger.info(f"截图用时：{time.time() - st}")  # game_image = Capture(hwnd, 0, 0, 1067, 600)
                logger.info(f"截图完毕")
            # 1. 转换图片为二进制
            img_bytes = cv2.imencode('.jpg', game_image)[1].tobytes()
            image_size = len(img_bytes)

            # 2. 创建消息头
            header_data = json.dumps({"type": "game_windows", "width": 1067, "height": 600, "image_size": image_size  # 添加图片大小到header
                                      }).encode('utf-8')

            # 3. 打包消息头长度（4字节）
            header_length = struct.pack('!I', len(header_data))

            # 4. 发送数据（带自动重试）
            if not self.send_with_retry(header_length, "消息头长度"):
                return False

            if not self.send_with_retry(header_data, "消息头内容"):
                return False

            if not self.send_with_retry(img_bytes, f"图片数据({image_size}字节)"):
                return False

            # 接收服务端的返回信息
            # 假设这里已经连接到服务端，并且sock是socket对象
            header, cls = self.socket_Handler.receive_message_from_server()
            if header["type"] == "game_windows":
                self.process_detect_message(cls, game_image)
            logger.info(f"退出 get_yolo_res")

        except Exception as e:
            logger.info(f"发送过程中发生未处理异常: {e}")
            traceback.print_exc()
            self._reconnect()
            return False

        return True
