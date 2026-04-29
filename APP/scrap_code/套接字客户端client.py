import socket
import time
import json

import cv2
import win32gui

from core.capture import Capture


def get_hwnd():
    dnf_hwnd = win32gui.FindWindow('地下城与勇士', '地下城与勇士：创新世纪')
    if dnf_hwnd != 0:
        print("地下城与勇士：创新世纪窗口的句柄:", dnf_hwnd)
    return dnf_hwnd


hwnd = get_hwnd()

# def receive_list_from_server(sock):
#     """接收字节数据"""
#     buffer = b''
#     end_marker = b'\n'  # 结束标志
#     while True:
#         part = sock.recv(1024)  # 可以根据需要调整接收缓冲区的大小
#         if not part:
#             break  # 如果没有接收到数据，则跳出循环
#         buffer += part
#
#         # 将字节数据解码为字符串，然后反序列化为列表
#     json_data = buffer.decode('utf-8')
#     data_list = json.loads(json_data)
#
#     return data_list
import json


def receive_list_from_server(sock):
    """从服务器接收以换行符结束标志的字节数据，并解码为列表"""
    buffer = b''
    end_marker = b'\n'  # 结束标志
    try:
        while True:
            part = sock.recv(1024)  # 接收数据块
            if not part:
                raise EOFError("连接被对方关闭且没有接收到有效数据")
            buffer += part  # 将接收到的数据块添加到缓冲区

            # 检查是否包含结束标志
            if end_marker in buffer:
                # 分割出完整数据（不包括结束标志）
                actual_data, _ = buffer.split(end_marker, 1)
                break  # 跳出循环
        # 确保实际数据不是空字符串
        if not actual_data:
            raise ValueError("接收到的数据为空")

        # 尝试将字节数据解码为字符串，并反序列化为列表
        json_data = actual_data.decode('utf-8')
        try:
            data_list = json.loads(json_data)
            # 检查反序列化后的数据是否为列表类型
            if not isinstance(data_list, list):
                raise TypeError("接收到的数据不是JSON格式的列表")
        except json.JSONDecodeError:
            raise ValueError("接收到的数据不是有效的JSON格式")

        return data_list
    except Exception as e:
        # 在发生异常时，可以根据需要处理（例如记录日志、关闭连接等）
        # 这里简单地将异常抛出，以便调用者可以处理
        raise e


def send_image(__server_address):
    # 创建一个 socket 对象
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # 连接到服务器
        sock.connect(__server_address)
        while True:
            game_img = Capture(hwnd, 0, 0, 1067, 600)
            # # 读取图片文件
            # image = cv2.imread(image_path)
            if game_img is None:
                print(f"Error: 图片为空")
                return
            # 将图片转换为二进制数据
            img_bytes = cv2.imencode('.jpg', game_img)[1].tobytes()

            # 发送图片大小（先发送大小，以便服务端知道要接收多少数据）
            image_size = len(img_bytes)
            sock.sendall(str(image_size).encode('utf-8') + b'\n')
            st = time.time()
            # 发送图片数据
            sock.sendall(img_bytes)
            # 接收服务端的返回信息
            # 假设这里已经连接到服务端，并且sock是socket对象
            data_list = receive_list_from_server(sock)
            print(data_list)
            print(f"耗时:{time.time() - st}秒")
            time.sleep(2)

    finally:
        # 关闭连接
        sock.close()

    # 示例用法


if __name__ == '__main__':
    import re


    def is_valid_ip(ip):
        # 使用正则表达式来验证IP地址
        pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
        if pattern.match(ip):
            # 进一步验证每个数字是否在0-255之间（可选）
            parts = ip.split('.')
            for part in parts:
                if not 0 <= int(part) <= 255:
                    return False
            return True
        return False


    try:
        ip = input("请输入服务器的IP地址: ")
        if not is_valid_ip(ip):
            raise ValueError("输入的IP地址无效")
        print(ip)
        server_address = (ip, 12345)

        send_image(server_address)

    except ValueError as e:
        print(e)
    except socket.error as e:
        print(f"无法连接到服务器: {e}")
    except Exception as e:
        print(f"发生了一个错误: {e}")
