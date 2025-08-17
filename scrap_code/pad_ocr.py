import json
import socket
import struct
import time
import traceback

import cv2
# from rapidocr_onnxruntime import RapidOCR
from utils.logging_setup import logger
from core import capture
from core.get_hwnd import hwnd

# from paddleocr import PaddleOCR

from utils.screenshot_util import screenshot_util

# ocr = PaddleOCR(
#     lang='ch',
#     det_model_dir='ch_PP-OCRv4_det_infer',  # 检测模型路径
#     rec_model_dir='ch_PP-OCRv4_rec_infer',  # 识别模型路径
# )  # need to run only once to load model into memory

server_address = ("192.168.1.125", 12345)
logger.info(server_address)
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(server_address)
sock.settimeout(1)
sock_connect_flags = True
logger.info(sock)


def get_text(x1, y1, x2, y2, img_numpy=None, amplify=False):
    try:
        logger.info(f"进入 ocr")
        if img_numpy is not None:
            game_image = img_numpy[y1:y2, x1:x2]

        else:
            img_numpy = screenshot_util.get_game_screenshot()
            game_image = img_numpy[y1:y2, x1:x2]
        if amplify:
            # 定义缩放比例（例如放大2倍）
            scale_factor = 1.5

            # 计算新尺寸
            new_width = int(game_image.shape[1] * scale_factor)
            new_height = int(game_image.shape[0] * scale_factor)
            new_size = (new_width, new_height)

            # 按比例放大图像
            game_image = cv2.resize(game_image, new_size, interpolation=cv2.INTER_LINEAR)
        # cv2.imshow("a", game_image)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()
        _image_rgb = cv2.cvtColor(game_image, cv2.COLOR_BGR2GRAY)
        # 1. 转换图片为二进制
        img_bytes = cv2.imencode('.jpg', _image_rgb)[1].tobytes()
        image_size = len(img_bytes)

        # 2. 创建消息头
        header_data = json.dumps({"type": "ocr", "width": 1, "height": 1, "image_size": image_size  # 添加图片大小到header
                                  }).encode('utf-8')

        # 3. 打包消息头长度（4字节）
        header_length = struct.pack('!I', len(header_data))

        # 4. 发送数据（带自动重试）
        if not send_with_retry(header_length, "消息头长度"):
            return False

        if not send_with_retry(header_data, "消息头内容"):
            return False

        if not send_with_retry(img_bytes, f"图片数据({image_size}字节)"):
            return False

        # 接收服务端的返回信息
        # 假设这里已经连接到服务端，并且sock是socket对象
        header, response = receive_message_from_server()
        if header["type"] == "ocr":
            logger.info(f"ocr 已获取识别数据: {response}")

        logger.info(f"退出 ocr")

    except Exception as e:
        logger.exception(f"发送过程中发生未处理异常:{e}")
        traceback.print_exc()
        return ''

    return response


def send_with_retry(data, message):
    """封装发送逻辑，带自动重连"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            sock.sendall(data)
            logger.info(f"成功发送 {message}")
            return True
        except socket.error as e:
            logger.info(f"发送失败（尝试 {attempt + 1}/{max_retries}）: {e}")
            traceback.print_exc()
            time.sleep(3)
    return False


def receive_message_from_server():
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
        header_len_buf = _recv_exact(4)
        header_len = struct.unpack('!I', header_len_buf)[0]

        # 接收并解析消息头
        header_data = _recv_exact(header_len)
        header = json.loads(header_data.decode('utf-8'))

        # 验证必要字段
        if 'type' not in header or 'data_size' not in header:
            raise ValueError("无效的协议头格式")

        # 接收实际数据
        data_size = header['data_size']
        data_buf = _recv_exact(data_size)
        data = json.loads(data_buf.decode('utf-8'))

        return header, data

    except (OSError, json.JSONDecodeError) as e:
        logger.exception(f"接收消息失败:{e}")
        traceback.print_exc()
        raise ConnectionError("连接异常")


def _recv_exact(n):
    """确保接收指定长度的数据"""
    buf = bytearray(n)
    received = 0
    while received < n:
        chunk = sock.recv(min(n - received, 4096))
        if not chunk:
            raise ConnectionError("连接意外关闭")
        buf[received:received + len(chunk)] = chunk
        received += len(chunk)
    return bytes(buf)


def ocr_get_text(x1, y1, x2, y2, img_numpy=None):
    """

    :param x1:
    :param y1:
    :param x2:
    :param y2:
    :return: str
    """

    det = None
    if img_numpy is not None:
        image_bgr = img_numpy
    else:
        image_bgr = capture.Capture(hwnd, 0, 0, 1067, 600)
    image_bgr = image_bgr[y1:y2, x1:x2]
    cv2.imshow("a", image_bgr)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    # 将BGR图像转换为RGB图像
    # _image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    _image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    result = ocr.ocr(_image_rgb, det=False, cls=False)
    for idx in range(len(result)):
        res = result[idx]
        for line in res:
            print(f"ocr识别结果为：{line}")
            det = line[0]
            # print(type(line))
    # result, elapse = engine(_image_rgb)
    # if result:
    #     det = result[0][1]
    #     print(f"ocr识别结果为：{det}")

    return det


def has_two_common_chars(input_str, target_set):
    input_set = set(input_str)

    for target_str in target_set:
        # 计算当前目标字符串与输入字符串的交集
        common_chars = input_set & set(target_str)
        if len(common_chars) >= 2:
            return True
    return False


# # 测试用例
# print(has_two_common_chars("apple", "banana"))  # True (a, p)
# print(has_two_common_chars("hello", "world"))  # False
# print(has_two_common_chars("algorithm", "log"))  # True (l, o)

if __name__ == "__main__":
    image_bgr = capture.Capture(hwnd, 0, 0, 1067, 600)
    results = get_text(498, 548, 582, 576, image_bgr, False)
    # match = int(re.search(r'\d+', results).group(0))
    print(results)
    # try:
    #     # 初始化PaddleOCR包装类
    #     # ocr_wrapper = PaddleOCRWrapper(model_dir=r'D:\dnf-ai-master-fengbao\ocr\ch_PP-OCRv4_rec_infer', cls_model_dir=r"D:\dnf-ai-master-fengbao\ocr\ch_ppocr_mobile_v2.0_cls_infer")
    #     st = time.time()
    #     # # 将BGR图像转换为RGB图像
    #     # image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    #     # cv2.imshow('123', image_bgr)
    #     # cv2.waitKey(0)
    #     # cv2.destroyAllWindows()
    #     # 对图片进行文字识别
    #
    #
    #     #
    #     # time.sleep(3)
    #     # results = recognize_text(933, 690, 1033, 709)
    #     # pl_int = re.search(r'(\d+)/', results).group(1)
    #     # if pl_int:
    #     #     pl_int = int(pl_int)
    #     #     print("当前疲劳值：", pl_int)
    #     # else:
    #     #     print("ocr疲劳没有找到匹配项")
    #     # print(f"耗时：{time.time() - st}秒")
    #     # # 提示用户按任意键后回车退出
    #     # input("请按任意键后回车退出...")
    #     # print("程序已退出。")
    #
    # except Exception as e:
    #     print(e)
