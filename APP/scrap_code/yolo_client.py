import re
import socket
import struct
import time
import traceback

import cv2
import base64
import requests
import json

from utils.screenshot_util import screenshot_util


def image_to_base64(image_path):
    # 加载图像
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("图像文件无法加载")

        # 将图像转换为RGB（因为cv2默认是BGR）
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # 将图像编码为PNG格式
    # 注意：PNG不需要设置质量参数
    result, img_encoded = cv2.imencode('.png', img_rgb)

    # 将编码后的图像数据转换为Base64
    data = base64.b64encode(img_encoded.tobytes()).decode('utf-8')

    # 构造JSON数据
    json_data = {'image': f'data:image/png;base64,{data}'}

    return json_data


def send_image_to_server(server_url, image_path):
    # 将图像转换为Base64
    json_data = image_to_base64(image_path)
    st = time.time()
    # 发送HTTP POST请求
    response = requests.post(server_url, json=json_data)

    # 打印响应
    print(response.text)
    print(f"发送图片到接受数据耗时{time.time() - st}秒")


# # 使用Flask服务器的URL替换这里的URL
# server_url = 'http://localhost:5000/upload_base64_image'
# # 替换为你的图像文件路径
# image_path = r'D:\dnf-ai-master-fengbao\Images\1897.png'
#
# # 发送图像到服务器
# send_image_to_server(server_url, image_path)
class TEST:
    def __init__(self):
        self.sock_connect_flags = None
        self.sock = None
        self.server_ip = '192.168.248.1'
        self.server_port = 12345
        screenshot_util.init_game_hwnd()

    def sock_connect(self):
        """
        连接socket
        :return:
        """
        server_address = (self.server_ip, self.server_port)
        print(server_address)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(server_address)
        self.sock.settimeout(1)
        self.sock_connect_flags = True
        print(self.sock)

    def get_yolo_res(self, game_image=None):
        try:
            print(f"进入 get_yolo_res")
            if game_image is None:
                # st = time.time()
                game_image = screenshot_util.get_game_screenshot()
                while True:
                    cv2.imshow("game", game_image)
                    # 等待按键
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                # print(f"截图用时：{time.time() - st}")
                # game_image = Capture(hwnd, 0, 0, 1067, 600)
            # 1. 转换图片为二进制
            img_bytes = cv2.imencode('.jpg', game_image)[1].tobytes()
            image_size = len(img_bytes)

            # 2. 创建消息头
            header_data = json.dumps({
                "type": "game_windows",
                "width": 1280,
                "height": 720,
                "image_size": image_size  # 添加图片大小到header
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
            header, cls = self.receive_message_from_server()
            if header["type"] == "game_windows":
                # if game_image is None:
                #     cls = self.yolo.detect()
                # else:
                #     cls = self.yolo.detect_by_img(game_image)
                print(cls)
            print(f"退出 get_yolo_res")

        except Exception as e:
            print(f"发送过程中发生未处理异常: {e}")
            traceback.print_exc()
            self._reconnect()
            return False

        return True

    def send_with_retry(self, data, message):
        """封装发送逻辑，带自动重连"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.sock.sendall(data)
                print(f"成功发送 {message}")
                return True
            except socket.error as e:
                print(f"发送失败（尝试 {attempt + 1}/{max_retries}）: {e}")
                traceback.print_exc()
                self._reconnect()
                time.sleep(3)
        return False

    def _reconnect(self):
        """关闭旧连接并建立新连接"""
        server_address = (self.server_ip, self.server_port)
        print(server_address)
        self.sock.close()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(server_address)
        self.sock.settimeout(5.0)

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
            print(f"接收消息失败: {e}")
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

    def get_text(self, x1, y1, x2, y2, img_numpy=None):
        try:
            print(f"进入 ocr")
            if img_numpy is not None:
                game_image = img_numpy[y1:y2, x1:x2]
            else:
                img_numpy = screenshot_util.get_game_screenshot()
                game_image = img_numpy[y1:y2, x1:x2]

            _image_rgb = cv2.cvtColor(game_image, cv2.COLOR_BGR2GRAY)
            # 1. 转换图片为二进制
            img_bytes = cv2.imencode('.jpg', _image_rgb)[1].tobytes()
            image_size = len(img_bytes)

            # 2. 创建消息头
            header_data = json.dumps({
                "type": "ocr",
                "width": 1,
                "height": 1,
                "image_size": image_size  # 添加图片大小到header
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
            header, response = self.receive_message_from_server()
            if header["type"] == "ocr":
                print(f"ocr 已获取识别数据: {response}")

            print(f"退出 ocr")

        except Exception as e:
            print(f"发送过程中发生未处理异常: {e}")
            traceback.print_exc()
            self._reconnect()
            return ''

        return response


t = TEST()
t.sock_connect()
while True:
    text = t.get_text(383, 179, 475, 204)
    pattern = r'[\u4e00-\u9fa5]+'
    # 使用 re.findall() 找出所有匹配的内容
    matches = re.findall(pattern, text)
    print(matches)
    time.sleep(1)
