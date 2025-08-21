# -*- coding: utf-8 -*-
# 导入必要的库
import os  # 用于文件路径处理
import queue  # 用于处理队列相关异常
import struct  # 用于二进制数据的打包/解包（网络通信格式处理）
import socket  # 用于TCP网络通信
import time  # 用于计时（计算处理耗时）
import traceback  # 用于捕获和打印异常堆栈信息
import cv2  # OpenCV库，用于图像处理（解码、格式转换等）
import json  # 用于数据的序列化和反序列化（请求/响应格式）
import numpy as np  # 用于图像数据的数组表示和处理
from datetime import datetime  # 用于记录时间（连接时间、日志时间）
import threading  # 用于多线程处理（实现并发）
from queue import Queue  # 用于创建任务队列（缓冲客户端请求）
from paddleocr import PaddleOCR  # 百度PaddleOCR库，用于文字识别
from yolo.yolo_main import YoloV8  # 自定义YOLOv8模型封装，用于目标检测
from root_dir import root_path  # 项目根路径配置（统一管理文件路径）
import tkinter as tk  # 用于创建GUI窗口（显示服务器日志）
from tkinter import scrolledtext  # 带滚动条的文本框组件（显示大量日志）
import sys  # 用于重定向标准输出（将print内容显示到GUI）

# 全局配置参数
MAX_WORKERS = 4  # 工作线程数量（根据CPU核心数调整，控制并发处理能力）
TASK_QUEUE_SIZE = 20  # 任务队列的最大缓冲容量（防止请求过多导致内存溢出）
MODEL_WARMUP = True  # 启用模型预热（提前加载模型到内存/GPU，减少首次请求延迟）

# OCR模型路径（旧版本配置，当前已注释，保留用于对比）
det_model_dir = os.path.join(root_path, 'ch_PP-OCRv4_det_infer')  # 文字检测模型路径
rec_model_dir = os.path.join(root_path, 'ch_PP-OCRv4_rec_infer')  # 文字识别模型路径


class ThreadedServer:
    """多线程图像处理服务器类

    功能：接收客户端发送的图像数据，根据请求类型调用YOLOv8（目标检测）或PaddleOCR（文字识别）处理，
          并将结果返回给客户端。通过多线程和任务队列实现多客户端并发处理。
    """

    def __init__(self, host='0.0.0.0', port=12345):
        """初始化服务器配置

        参数：
            host: 服务器监听的IP地址（0.0.0.0表示允许所有网络接口连接）
            port: 服务器监听的端口号
        """
        self.server_address = (host, port)  # 服务器监听地址和端口
        self.task_queue = Queue(maxsize=TASK_QUEUE_SIZE)  # 任务队列（存储客户端连接任务）
        self.workers = []  # 工作线程列表（存储所有启动的工作线程）
        self.running = False  # 服务器运行状态标志（控制线程启动/停止）

    def start(self):
        """启动服务器主流程

        步骤：
            1. 启动指定数量的工作线程（处理图像推理任务）
            2. 启动监听线程（接收客户端连接并加入任务队列）
        """
        self.running = True  # 设置服务器为运行状态

        # 启动工作线程（数量由MAX_WORKERS指定）
        for _ in range(MAX_WORKERS):
            # 创建工作线程，目标函数为_worker（处理具体任务）
            worker = threading.Thread(target=self._worker)
            worker.daemon = True  # 设置为守护线程（主程序退出时自动结束）
            worker.start()  # 启动线程
            self.workers.append(worker)  # 加入工作线程列表

        # 启动网络监听线程（单独线程接收连接，避免阻塞主线程）
        listener = threading.Thread(target=self._listen)
        listener.start()  # 启动监听线程
        print(f"服务器已启动在 {self.server_address[0]}:{self.server_address[1]}")  # 打印启动信息
        listener.join()  # 等待监听线程结束（实际运行中会一直阻塞）

    def _listen(self):
        """独立的网络监听线程

        功能：
            - 创建TCP socket并绑定地址端口
            - 持续监听客户端连接请求
            - 将接收到的连接放入任务队列，由工作线程处理
        """
        # 创建TCP socket（AF_INET表示IPv4，SOCK_STREAM表示流式传输）
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 设置socket选项：允许端口复用（避免服务器重启时出现"端口已占用"错误）
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(self.server_address)  # 绑定服务器地址和端口
        sock.listen(10)  # 开始监听，最大等待连接数为10（超过后新连接会被拒绝）

        try:
            # 持续运行，直到服务器停止（running设为False）
            while self.running:
                # 阻塞等待客户端连接（conn为连接对象，addr为客户端地址）
                conn, addr = sock.accept()
                # 将连接放入任务队列，由工作线程处理
                self.task_queue.put((conn, addr))
        finally:
            sock.close()  # 服务器停止时关闭socket

    def _worker(self):
        """工作线程核心逻辑

        功能：
            - 每个工作线程独立初始化YOLO和OCR模型（避免多线程资源竞争）
            - 从任务队列中获取客户端连接并处理请求
        """
        # 初始化YOLOv8目标检测模型
        yolo = YoloV8()  # 创建YOLO模型实例
        yolo.loadModel()  # 加载YOLO模型权重

        # 初始化PaddleOCR文字识别模型（使用最新版本接口）
        # 旧版本配置（已注释）：通过指定本地模型路径加载
        # ocr_engine = PaddleOCR(
        #     lang='ch',
        #     det_model_dir=det_model_dir,
        #     rec_model_dir=rec_model_dir,
        #     use_gpu=True
        # )
        # 最新版本配置：通过模型名称自动下载并加载（PP-OCRv4轻量版）
        ocr_engine = PaddleOCR(
            # lang='ch',  # 默认为中文，可省略
            # text_detection_model_dir=det_model_dir,  # 本地模型路径（当前未使用）
            # text_recognition_model_dir=rec_model_dir,  # 本地模型路径（当前未使用）
            text_detection_model_name='PP-OCRv4_mobile_det',  # 文字检测模型名称（轻量版）
            text_recognition_model_name='PP-OCRv4_mobile_rec',  # 文字识别模型名称（轻量版）
            # use_gpu=True  # 是否使用GPU加速（当前注释表示使用CPU）
        )

        # 模型预热（减少首次推理延迟）
        if MODEL_WARMUP:
            # 生成640x640的空图像（模拟输入，触发模型加载）
            dummy = np.zeros((640, 640, 3), dtype=np.uint8)
            # YOLO模型预热（执行一次检测）
            yolo.detect(dummy)
            # OCR模型预热（转换为灰度图后执行一次识别）
            gray = cv2.cvtColor(dummy, cv2.COLOR_BGR2GRAY)  # BGR转灰度图（OCR常见输入格式）
            ocr_engine.ocr(gray, det=False, cls=False)  # 执行OCR识别（关闭检测和方向分类）

        # 打印线程初始化完成信息（threading.get_ident()获取线程唯一标识）
        print(f"线程 {threading.get_ident()} 模型初始化完成")

        # 持续处理任务队列中的连接
        while self.running:
            try:
                # 从任务队列获取连接（超时1秒，避免线程一直阻塞）
                conn, addr = self.task_queue.get(timeout=1)
                # 处理客户端请求（传入当前线程的模型实例）
                self._handle_client(conn, addr, yolo, ocr_engine)
            except queue.Empty:
                # 队列空时继续循环等待
                continue

    def _handle_client(self, conn, addr, yolo, ocr_engine):
        """处理单个客户端的请求

        功能：
            - 接收客户端发送的图像和请求头
            - 根据请求类型调用对应的模型处理（YOLO目标检测或OCR识别）
            - 将处理结果返回给客户端
            - 记录处理耗时和日志

        参数：
            conn: 客户端连接对象
            addr: 客户端地址（IP:端口）
            yolo: 当前线程的YOLO模型实例
            ocr_engine: 当前线程的OCR模型实例
        """
        try:
            # 使用with语句自动管理连接（退出时自动关闭conn）
            with conn:
                # 记录连接时间并打印日志
                formatted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"{formatted_time}\t新连接: {addr}")

                # 持续处理该客户端的请求（直到客户端断开）
                while True:
                    # 接收客户端发送的消息（包含请求头和图像）
                    header, image = self._receive_message(conn)
                    if not header:  # 若接收失败（客户端断开），退出循环
                        break

                    # 记录处理开始时间（用于计算耗时）
                    start_time = time.time()

                    # 根据请求类型调用对应的处理逻辑
                    if header['type'] == 'game_windows':
                        # 处理"游戏窗口"目标检测（如识别游戏中的角色、道具等）
                        result = yolo.detect(image)
                    elif header['type'] == 'min_map':
                        # 处理"小地图"目标检测（如识别小地图中的点位、路径等）
                        result = yolo.min_map_detect(image)
                    elif header['type'] == 'ocr':
                        # 处理文字识别（如提取图像中的文字内容）
                        result = self._ocr_process(image, ocr_engine)
                    else:
                        # 未知请求类型，抛出异常
                        raise ValueError("无效的请求类型")

                    # 将处理结果发送给客户端
                    self._send_response(conn, result, header['type'])

                    # 计算并打印处理耗时（毫秒）
                    latency = (time.time() - start_time) * 1000
                    print(f"请求处理完成 耗时: {latency:.2f}ms")

        except Exception as e:
            # 捕获并打印异常信息（便于调试）
            traceback.print_exc()
            print(f"客户端 {addr} 处理异常: {str(e)}")

    def _receive_message(self, conn):
        """接收并解析客户端发送的消息

        消息格式（自定义协议）：
            1. 4字节（无符号整数，大端格式）：请求头长度（header_size）
            2. header_size字节：请求头（JSON格式，包含type(请求类型)、image_size(图像大小)等）
            3. image_size字节：图像数据（二进制，JPG/PNG等格式编码）

        返回：
            header: 解析后的请求头字典（若接收失败则为None）
            image: 解码后的OpenCV图像（BGR格式，若接收失败则为None）
        """
        try:
            # 接收请求头长度（固定4字节）
            header_len = conn.recv(4)
            if len(header_len) < 4:  # 未接收到完整的头长度（客户端断开）
                return None, None

            # 解析头长度（!I表示网络字节序的无符号整数）
            header_size = struct.unpack('!I', header_len)[0]
            # 接收请求头数据（长度为header_size）
            header_data = conn.recv(header_size)
            # 解码并解析为字典（JSON字符串→Python字典）
            header = json.loads(header_data.decode('utf-8'))

            # 接收图像数据（根据请求头中的image_size确定长度）
            image_size = header['image_size']
            received = 0  # 已接收的字节数
            chunks = []  # 存储图像数据片段
            # 循环接收直到获取完整图像
            while received < image_size:
                # 每次最多接收4096字节（平衡效率和内存占用）
                chunk = conn.recv(min(4096, image_size - received))
                if not chunk:  # 客户端断开，未收到完整图像
                    break
                chunks.append(chunk)  # 保存数据片段
                received += len(chunk)  # 更新已接收长度

            # 将二进制数据解码为OpenCV图像（BGR格式）
            # np.frombuffer将字节流转为numpy数组，cv2.imdecode解码为图像
            image = cv2.imdecode(np.frombuffer(b''.join(chunks), dtype=np.uint8), cv2.IMREAD_COLOR)
            return header, image

        except (socket.timeout, ConnectionResetError):
            # 捕获连接超时或被客户端强制关闭的异常
            return None, None

    def _send_response(self, conn, data, msg_type):
        """向客户端发送处理结果

        响应格式（自定义协议）：
            1. 4字节：响应头长度（header_size）
            2. header_size字节：响应头（JSON格式，包含type(响应类型)、data_size(结果大小)等）
            3. data_size字节：处理结果（JSON编码的字符串）

        参数：
            conn: 客户端连接对象
            data: 处理结果数据（需可序列化为JSON）
            msg_type: 响应类型（与请求类型一致，便于客户端匹配）
        """
        try:
            # 将处理结果序列化为JSON字符串并转为字节流
            json_data = json.dumps(data).encode('utf-8')
            # 构建响应头（包含类型和结果大小）
            header = json.dumps({
                'type': msg_type,  # 响应类型（与请求类型相同）
                'data_size': len(json_data)  # 结果数据的字节长度
            }).encode('utf-8')  # 转为字节流

            # 发送响应头长度（4字节，大端格式）
            conn.sendall(struct.pack('!I', len(header)))
            # 发送响应头数据
            conn.sendall(header)
            # 发送处理结果数据
            conn.sendall(json_data)
        except BrokenPipeError:
            # 客户端提前断开连接，无法发送响应
            print("客户端连接已中断")

    def _ocr_process(self, image, ocr_engine):
        """OCR文字识别处理流程

        功能：
            - 调用OCR模型识别图像中的文字
            - 拼接识别结果并返回

        参数：
            image: 输入图像（OpenCV的BGR格式）
            ocr_engine: OCR模型实例

        返回：
            拼接后的文字字符串
        """
        # 旧版本OCR处理逻辑（已注释，保留用于对比）
        # gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # 转为灰度图
        # results = ocr_engine.ocr(gray, det=False, cls=False)  # 执行识别（关闭检测和分类）
        # return ''.join(line[0] for page in results for line in page)  # 拼接结果

        # 最新版本OCR处理逻辑（使用predict接口）
        # predict返回结果为列表，其中第一个元素是识别结果字典
        # 'rec_texts'字段存储所有识别到的文字列表
        rec_texts = ocr_engine.predict(image)[0]['rec_texts']
        joined_text = ''.join(rec_texts)  # 拼接所有文字为字符串
        print(joined_text)  # 打印识别结果（用于调试）
        return joined_text  # 返回拼接后的结果


class PrintRedirector:
    """日志重定向工具类

    功能：将标准输出（print内容）重定向到Tkinter的文本框组件，
          实现服务器日志的可视化显示。
    """

    def __init__(self, text_widget):
        """初始化重定向器

        参数：
            text_widget: Tkinter的文本框组件（用于显示日志）
        """
        self.text_widget = text_widget

    def write(self, message):
        """重写write方法，将内容插入文本框

        参数：
            message: 要显示的日志内容
        """
        # 在文本框末尾插入消息
        self.text_widget.insert(tk.END, message)
        # 自动滚动到文本框底部（显示最新内容）
        self.text_widget.see(tk.END)

    def flush(self):
        """重写flush方法（兼容标准输出的flush操作）"""
        pass  # 无需实际操作，仅为满足接口要求


# 程序入口
if __name__ == '__main__':
    # 创建Tkinter主窗口（服务器日志界面）
    root = tk.Tk()
    root.title("服务器日志")  # 窗口标题
    root.geometry("800x600")  # 窗口初始大小（宽x高）

    # 创建带滚动条的文本框（用于显示日志）
    text_area = scrolledtext.ScrolledText(root, width=80, height=30)
    # 设置文本框布局（边距、填充方式）
    text_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
    # 重定向标准输出到文本框（print内容将显示在这里）
    sys.stdout = PrintRedirector(text_area)

    # 创建服务器实例并启动（在独立线程中，避免阻塞GUI）
    server = ThreadedServer()
    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True  # 服务器线程设为守护线程（随窗口关闭而结束）
    server_thread.start()  # 启动服务器线程


    # 定义窗口关闭时的处理函数
    def on_closing():
        server.running = False  # 设置服务器为停止状态（终止所有线程）
        root.destroy()  # 销毁窗口，结束程序


    # 绑定窗口关闭事件（点击右上角关闭按钮时触发on_closing）
    root.protocol("WM_DELETE_WINDOW", on_closing)
    # 启动Tkinter主循环（显示窗口并处理事件）
    root.mainloop()