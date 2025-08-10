import os
import queue
import struct
import time
import traceback

from yolo.yolo_main import YoloV8
import socket
import cv2
import numpy as np
import json
from datetime import datetime
import threading

# 创建 Event 对象
# STOP_EVENT = threading.Event()
# 创建一个队列用于存储图片数据
# image_queue = queue.Queue()

# 创建一个锁对象
lock = threading.Lock()
# # 消息头格式：1个字节的消息类型 + 4个字节的消息长度
# HEADER_FORMAT = '!BI'
# HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

from paddleocr import PaddleOCR
from root_path import root_path

det_model_dir = os.path.join(root_path, 'ch_PP-OCRv4_det_infer')
rec_model_dir = os.path.join(root_path, 'ch_PP-OCRv4_rec_infer')
ocr = PaddleOCR(
    lang='ch',
    det_model_dir=det_model_dir,  # 检测模型路径
    rec_model_dir=rec_model_dir,  # 识别模型路径
)  # need to run only once to load model into memory


def show_images_thread():
    # 创建一个名为'Image Display'的窗口（但注意函数中的窗口名实际上是'img'）
    cv2.namedWindow(f"Server", cv2.WINDOW_AUTOSIZE)

    # 尝试设置窗口的位置（x, y），但注意cv2.setWindowProperty对于全屏属性的设置可能不是这里想要的
    # 如果你想要设置窗口为非全屏且移动位置，应该确保不设置全屏属性，或者正确设置它之后再移动窗口
    # 这里我们简单地移动窗口到一个指定位置
    cv2.moveWindow(f"Server", 0, 0)  # 将窗口移动到屏幕上的(850, 0)位置

    while True:  # 如果键盘按下F12会退出脚本
        # 从队列中获取图片数据，如果队列为空则阻塞
        frame = image_queue.get()

        # 如果接收到特定的结束信号（例如None），则退出循环
        if frame is None:
            break

        # 显示图片
        cv2.imshow(f"Server", frame)

        # 等待按键，如果是'q'则退出循环（但注意这里的'q'检查可能不是必需的，因为我们已经有了结束信号）
        # 然而，保留这个检查可以让用户通过按键来提前退出显示
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # 销毁窗口（虽然在这个例子中，当线程结束时窗口通常会自动关闭）
    cv2.destroyWindow(f"Server")


def ocr_get_text(img_numpy):
    """
    从BGR格式图像中提取并拼接所有OCR识别结果

    该函数执行以下操作：
    1. 将输入的BGR图像转换为灰度图（增强OCR引擎兼容性）
    2. 使用预配置的OCR引擎进行文本检测与识别
    3. 拼接所有识别到的文本行，按检测顺序返回完整字符串

    参数:
        img_numpy (numpy.ndarray):
            输入图像数组，需为OpenCV标准的BGR格式（shape: [H, W, 3]）

    返回:
        str: 所有识别结果的拼接字符串。若无有效结果，返回空字符串。

    实现细节:
        - 使用灰度转换提升处理效率（COLOR_BGR2GRAY）
        - 禁用方向检测(det=False)和分类(cls=False)以提升速度
        - 按检测顺序拼接文本行（保留原始顺序）

    注意事项:
        * 不同文本行之间无额外分隔符，如需分隔可手动添加
        * 灰度转换可能影响彩色文本的识别准确率
        * 依赖外部OCR引擎的实现（需提前初始化ocr对象）
    """
    # 初始化结果容器
    full_text = []

    # 颜色空间转换
    _image_gray = cv2.cvtColor(img_numpy, cv2.COLOR_BGR2GRAY)

    # 执行OCR识别
    ocr_results = ocr.ocr(_image_gray, det=False, cls=False)

    # 遍历所有检测结果
    for page_results in ocr_results:
        for line_info in page_results:
            # 提取文本内容并添加到结果集
            if line_info:
                full_text.append(line_info[0])

    # 返回拼接后的完整文本
    return ''.join(full_text)


def send_list_to_client(conn, data, message_type):
    """
    将数据列表打包为带消息头的协议格式并发送给客户端
    协议结构：[4字节消息头长度][JSON消息头][JSON数据]
    """
    try:
        # 验证消息类型
        if message_type not in ["game_windows", "min_map", "ocr"]:
            raise ValueError("无效的消息类型")

        # 数据序列化
        json_data = json.dumps(data).encode('utf-8')

        # 构建消息头（合并冗余分支）
        header = {
            "type": message_type,
            "data_size": len(json_data)  # 直接使用序列化后的长度
        }

        # 序列化并打包消息头
        header_bytes = json.dumps(header).encode('utf-8')
        header_len = struct.pack('!I', len(header_bytes))

        # 定义安全发送函数（保持原有逻辑）
        def safe_send(data_chunk):
            try:
                conn.sendall(data_chunk)
            except OSError as e:
                print(f"发送失败: {e}")
                traceback.print_exc()
                raise ConnectionError(f"网络发送失败: {e}")

        # 分阶段发送（添加注释说明顺序）
        # 1. 发送消息头长度
        safe_send(header_len)
        # 2. 发送消息头内容
        safe_send(header_bytes)
        # 3. 发送实际数据
        safe_send(json_data)

    except (TypeError, json.JSONEncodeError, struct.error) as e:
        print(f"数据打包失败: {e}")
        traceback.print_exc()
        raise ValueError("数据格式错误")


def handle_client(conn, addr):
    # # 启动显示图像的线程
    # display_thread = threading.Thread(target=show_images_thread, daemon=True)
    # display_thread.start()
    try:
        while True:  # 添加一个循环来保持连接
            process_image_message(conn, addr)
            # 可以在这里添加逻辑来处理客户端的关闭信号
            # 例如：如果接收到"exit"或"close"，则跳出循环
    except Exception as e:
        # 获取当前时间并格式化
        formatted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{formatted_time}\t处理客户端 {addr} 时发生错误: {e}")
        traceback.print_exc()
        conn.close()


def receive_message(conn):
    """
    从网络连接接收结构化消息并解码图像数据

    该函数采用两阶段接收协议：
    1. 先接收4字节消息头长度（大端无符号整型）
    2. 再接收指定长度的JSON消息头
    3. 最后根据消息头中的image_size字段接收完整的图像数据

    参数:
        conn: socket.socket
            已建立连接的网络套接字对象，需支持recv方法

    返回:
        tuple: (header, game_image)
            header (dict): 包含消息元数据的字典，必须包含'image_size'字段
            game_image (numpy.ndarray): 解码后的BGR格式图像数组，失败时返回None

    协议规范:
        - 消息头使用UTF-8编码的JSON字符串
        - 图像数据按原始二进制流传输
        - 接收缓冲区自动适配（最大4096字节/次）

    异常处理:
        - 网络中断会触发socket.error
        - 无效JSON会引发json.JSONDecodeError
        - 损坏的图像数据可能导致解码失败（返回None）
    """
    # 接收消息头长度（4字节）
    header_length_buf = conn.recv(4)
    header_length = struct.unpack('!I', header_length_buf)[0]

    # 接收消息头内容
    header_data = conn.recv(header_length)
    header = json.loads(header_data.decode('utf-8'))

    # 预分配内存接收图片
    image_size = header['image_size']
    image_buf = bytearray(image_size)
    received = 0

    while received < image_size:
        chunk = conn.recv(min(4096, image_size - received))
        if not chunk:
            break
        image_buf[received:received + len(chunk)] = chunk
        received += len(chunk)
    # 解码图片
    game_image = cv2.imdecode(np.frombuffer(image_buf, dtype=np.uint8), cv2.IMREAD_COLOR)

    return header, game_image

    # header_data = conn.recv(5)  # 1字节类型 + 4字节长度
    # if not header_data:
    #     raise ConnectionError("客户端可能已经关闭连接")
    # message_type, message_length = struct.unpack('!BI', header_data)
    # print(f"接收到消息：类型={message_type}, 长度={message_length}")
    #
    # message_content = b''
    # while len(message_content) < message_length:
    #     packet = conn.recv(4096)
    #     if not packet:
    #         raise ConnectionError("接收数据时连接中断")
    #     message_content += packet
    #
    # if len(message_content) != message_length:
    #     raise ValueError("接收到的数据长度与预期不符")
    # return message_type, message_content


def process_image_message(conn, addr):
    global yo, lock
    header, game_image = receive_message(conn)
    message_type = None
    if header['type'] == "game_windows":
        res = yo.detect(game_image)
        message_type = "game_windows"
        print(f"game_windows的推理结果为：{res}\n")
        send_list_to_client(conn, res, message_type)  # 假设这个函数用于将结果发送回客户端
    elif header['type'] == "min_map":
        res = yo.min_map_detect(game_image)
        message_type = "min_map"
        print(f"min_map的推理结果为：{res}\n")
        send_list_to_client(conn, res, message_type)  # 假设这个函数用于将结果发送回客户端
    elif header['type'] == "ocr":
        res = ocr_get_text(game_image)
        message_type = "ocr"
        print(f"min_map的识别结果为：{res}\n")
        send_list_to_client(conn, res, message_type)  # 假设这个函数用于将结果发送回客户端
        # if message_type == 1:  # 假设1表示图像消息
        #     nparr = np.frombuffer(message_content, np.uint8)
        #     img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        #     if img is None:
        #         raise ValueError("无法解码图像数据")
        #     # image_queue.put(img)
        #     h, w, _ = img.shape
        #     with lock:
        #         if h == 720 and w == 1280:
        #             res = yo.detect(img)
        #         else:
        #             res = yo.min_map_detect(img)
        #     print(f"{addr} 的推理结果为：{res}\n")


def receive_image(__server_address):
    host, port = __server_address
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(__server_address)
    sock.listen(5)  # 监听队列大小可以设置为更大的值以容纳更多等待连接的客户端
    print(f"服务器正在监听 {host}:{port}...")

    try:
        while True:
            conn, addr = sock.accept()
            # 获取当前时间并格式化
            formatted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"{formatted_time}\t连接地址:", addr)
            # 为每个连接创建一个新线程
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.start()
    except KeyboardInterrupt:
        print("\nProgram interrupted by user. Closing socket.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        sock.close()


def get_ip():
    def get_local_ips():
        host = socket.gethostname()
        local_ips = []
        try:
            # 获取与主机名关联的所有地址信息
            addr_infos = socket.getaddrinfo(host, None)
            for addr_info in addr_infos:
                # 检查地址族是否为 IPv4
                if addr_info[0] == socket.AF_INET:
                    # 提取 IPv4 地址和端口（如果有的话，但在这里我们不需要端口）
                    ip_address, _ = addr_info[4][:2]  # addr_info[4] 是 (ip, port) 元组
                    local_ips.append(ip_address)
        except socket.gaierror as e:
            print(f"获取本地主机名对应的 IP 地址时出错: {e}")

        return local_ips

    # 获取并打印所有本机的 IPv4 地址
    # print("本机 IPv4 地址列表:", get_local_ips())
    # 获取本机的 IPv4 地址列表
    ips = get_local_ips()

    # 打印地址列表，并让用户选择
    print("本机 IPv4 地址列表:")
    for i, ip in enumerate(ips, start=1):
        print(f"{i}. {ip}")

    # 获取用户输入
    choice = input("设置服务器IP，请输入数字选择 IP 地址（1-{}）: ".format(len(ips)))

    # 检查输入是否有效
    if choice.isdigit() and 1 <= int(choice) <= len(ips):
        # 返回选择的 IP 地址
        selected_ip = ips[int(choice) - 1]
        print("您选择的 IP 地址是:", selected_ip)
        return selected_ip
    else:
        print("无效的选择，请输入一个有效的数字。")


if __name__ == '__main__':

    # ip = get_ip()
    ip = '0.0.0.0'
    print(f"YOLO加载中……")
    yo = YoloV8()
    try:
        yo.loadModel()
        # 测试YOLOv8模型（可选）
        # 设置图像尺寸
        width, height = 640, 640
        # 创建一个全白的图片（白色像素值为255）
        white_image = np.ones((height, width, 3), dtype=np.uint8) * 0
        yo.detect(white_image)
    except Exception as e:
        print(f"加载YOLOv8模型时发生错误: {e}")
        exit(1)
    server_address = (ip, 12345)
    try:
        receive_image(server_address)
    except Exception as e:
        print(f"服务器运行时发生错误: {e}")
