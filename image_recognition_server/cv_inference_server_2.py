# -*- coding: utf-8 -*-
import os
import queue
import struct
import socket  # 用于网络通信（客户端-服务器连接）
import time
import traceback
import cv2  # 用于图像处理（解码、格式转换等）
import json  # 用于数据序列化（请求/响应格式处理）
import numpy as np  # 用于图像数据存储（数组形式）
from datetime import datetime
import threading  # 用于多线程处理（提高并发能力）
from queue import Queue  # 用于任务队列（缓冲请求，平衡负载）
from paddleocr import PaddleOCR  # 百度PaddleOCR库（文字识别）
from yolo.yolo_main import YoloV8  # YOLOv8模型（目标检测）
from root_dir import root_path  # 项目根路径配置
import tkinter as tk  # 用于GUI界面（显示服务器日志）
from tkinter import scrolledtext
import sys

# 全局配置
MAX_WORKERS = 4  # 工作线程数量（根据CPU核心数调整，提高并发处理能力）
TASK_QUEUE_SIZE = 20  # 任务队列最大缓冲量（避免请求堆积溢出）
MODEL_WARMUP = True  # 模型预热开关（提前加载模型，减少首次推理延迟）

# 模型路径（OCR的检测/识别模型）
det_model_dir = os.path.join(root_path, 'ch_PP-OCRv4_det_infer')  # OCR检测模型（定位文字区域）
rec_model_dir = os.path.join(root_path, 'ch_PP-OCRv4_rec_infer')  # OCR识别模型（识别文字内容）


class ThreadedServer:
    """多线程图像处理服务器

    功能：接收客户端发送的图像数据，根据请求类型调用YOLO（目标检测）或OCR（文字识别）处理，
          并将结果返回给客户端。支持多客户端并发请求（通过多线程和任务队列实现）。
    """

    def __init__(self, host='0.0.0.0', port=12345):
        self.server_address = (host, port)  # 服务器监听地址（0.0.0.0表示允许所有IP连接）
        self.task_queue = Queue(maxsize=TASK_QUEUE_SIZE)  # 任务队列（存储客户端连接任务）
        self.workers = []  # 工作线程列表
        self.running = False  # 服务器运行状态标志

    def start(self):
        """启动服务器：初始化工作线程和监听线程"""
        self.running = True
        # 启动工作线程（负责处理图像推理）
        for _ in range(MAX_WORKERS):
            worker = threading.Thread(target=self._worker)
            worker.daemon = True  # 守护线程（主程序退出时自动结束）
            worker.start()
            self.workers.append(worker)

        # 启动网络监听线程（负责接收客户端连接）
        listener = threading.Thread(target=self._listen)
        listener.start()
        print(f"服务器已启动在 {self.server_address[0]}:{self.server_address[1]}")
        listener.join()

    def _listen(self):
        """独立监听线程：持续接收客户端连接，将连接放入任务队列"""
        # 创建TCP socket（流式传输，保证数据顺序和完整性）
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # 允许端口复用（避免服务器重启时端口占用）
        sock.bind(self.server_address)
        sock.listen(10)  # 最大等待连接数（超过后新连接会被拒绝）

        try:
            while self.running:
                conn, addr = sock.accept()  # 阻塞等待客户端连接（conn是连接对象，addr是客户端IP:端口）
                self.task_queue.put((conn, addr))  # 将连接放入任务队列，由工作线程处理
        finally:
            sock.close()  # 服务器停止时关闭socket

    def _worker(self):
        """工作线程：每个线程独立初始化模型，从任务队列取连接并处理"""
        # 初始化YOLO模型（目标检测，如游戏窗口元素、小地图识别）
        yolo = YoloV8()
        yolo.loadModel()

        # 初始化OCR模型（文字识别，如提取图像中的文字内容）
        ocr_engine = PaddleOCR(
            lang='ch',  # 支持中文识别
            det_model_dir=det_model_dir,  # 文字检测模型路径
            rec_model_dir=rec_model_dir,  # 文字识别模型路径
            use_gpu=True  # 使用GPU加速（需配置CUDA环境）
        )

        # 模型预热（用空图像触发首次推理，加载权重到内存/GPU，减少后续请求延迟）
        if MODEL_WARMUP:
            dummy = np.zeros((640, 640, 3), dtype=np.uint8)  # 生成640x640的空图像（模拟输入）
            yolo.detect(dummy)  # YOLO预热
            gray = cv2.cvtColor(dummy, cv2.COLOR_BGR2GRAY)  # 转为灰度图（OCR常见输入格式）
            ocr_engine.ocr(gray, det=False, cls=False)  # OCR预热

        print(f"线程 {threading.get_ident()} 模型初始化完成")

        while self.running:
            try:
                # 从任务队列取连接（超时1秒，避免线程一直阻塞）
                conn, addr = self.task_queue.get(timeout=1)
                self._handle_client(conn, addr, yolo, ocr_engine)  # 处理客户端请求
            except queue.Empty:
                continue  # 队列空时继续等待

    def _handle_client(self, conn, addr, yolo, ocr_engine):
        """处理单个客户端请求：接收图像→调用模型处理→返回结果"""
        try:
            with conn:  # 自动关闭连接（退出with块时）
                formatted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"{formatted_time}\t新连接: {addr}")  # 记录客户端连接信息

                while True:
                    # 接收客户端发送的消息（包含图像和请求头）
                    header, image = self._receive_message(conn)
                    if not header:  # 客户端断开连接时退出循环
                        break

                    start_time = time.time()  # 记录处理开始时间（用于计算耗时）

                    # 根据请求类型调用对应模型处理
                    if header['type'] == 'game_windows':
                        # 处理"游戏窗口"目标检测（如识别游戏中的角色、道具位置）
                        result = yolo.detect(image)
                    elif header['type'] == 'min_map':
                        # 处理"小地图"目标检测（如识别小地图中的点位、路径）
                        result = yolo.min_map_detect(image)
                    elif header['type'] == 'ocr':
                        # 处理文字识别（如提取游戏中的文字提示、对话框内容）
                        result = self._ocr_process(image, ocr_engine)
                    else:
                        raise ValueError("无效的请求类型")

                    # 将处理结果发送给客户端
                    self._send_response(conn, result, header['type'])

                    # 计算并打印处理耗时（用于性能监控）
                    latency = (time.time() - start_time) * 1000
                    print(f"请求处理完成 耗时: {latency:.2f}ms")

        except Exception as e:
            traceback.print_exc()  # 打印异常堆栈（便于调试）
            print(f"客户端 {addr} 处理异常: {str(e)}")

    def _receive_message(self, conn):
        """接收客户端消息：解析消息头→接收图像数据→解码为OpenCV格式

        消息格式：
        1. 4字节（uint32）：消息头长度（header_size）
        2. header_size字节：消息头（JSON格式，包含请求类型、图像大小等）
        3. 图像大小字节：图像数据（二进制，JPG/PNG编码）
        """
        try:
            # 接收消息头长度（4字节，大端格式）
            header_len = conn.recv(4)
            if len(header_len) < 4:  # 未收到完整的头长度（客户端断开）
                return None, None

            header_size = struct.unpack('!I', header_len)[0]  # 解析为无符号整数（!表示网络字节序，大端）
            header_data = conn.recv(header_size)  # 接收消息头数据
            header = json.loads(header_data.decode('utf-8'))  # 解码为字典

            # 接收图像数据
            image_size = header['image_size']  # 从消息头获取图像总大小
            received = 0
            chunks = []
            while received < image_size:
                # 每次最多接收4096字节（平衡效率和内存）
                chunk = conn.recv(min(4096, image_size - received))
                if not chunk:  # 客户端断开，未收到完整图像
                    break
                chunks.append(chunk)
                received += len(chunk)

            # 将二进制数据解码为OpenCV图像（BGR格式）
            image = cv2.imdecode(np.frombuffer(b''.join(chunks), dtype=np.uint8), cv2.IMREAD_COLOR)
            return header, image

        except (socket.timeout, ConnectionResetError):
            return None, None  # 连接超时或被客户端重置

    def _send_response(self, conn, data, msg_type):
        """向客户端发送处理结果：构建响应头→发送头→发送结果数据

        响应格式：
        1. 4字节：响应头长度
        2. 响应头字节：JSON格式（包含响应类型、结果数据大小）
        3. 结果数据字节：JSON编码的处理结果
        """
        try:
            json_data = json.dumps(data).encode('utf-8')  # 结果数据序列化（转为JSON字符串→二进制）
            header = json.dumps({
                'type': msg_type,  # 与请求类型一致（便于客户端匹配）
                'data_size': len(json_data)  # 结果数据大小
            }).encode('utf-8')  # 响应头序列化

            # 发送响应头长度→响应头→结果数据
            conn.sendall(struct.pack('!I', len(header)))
            conn.sendall(header)
            conn.sendall(json_data)
        except BrokenPipeError:
            print("客户端连接已中断")  # 客户端提前断开，无法发送响应

    def _ocr_process(self, image, ocr_engine):
        """OCR处理流程：转为灰度图→调用OCR→拼接识别结果"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # 转为灰度图（减少计算量，提高OCR精度）
        results = ocr_engine.ocr(gray, det=False, cls=False)  # 仅识别（不检测文字区域，假设输入是纯文字图像）
        # 拼接所有识别结果（PaddleOCR返回格式：[[(文字, 置信度), ...]]）
        return ''.join(line[0] for page in results for line in page)


class PrintRedirector:
    """日志重定向：将print输出到Tkinter的文本框（方便可视化查看服务器日志）"""

    def __init__(self, text_widget):
        self.text_widget = text_widget  # Tkinter的文本框组件

    def write(self, message):
        self.text_widget.insert(tk.END, message)  # 插入日志到文本框末尾
        self.text_widget.see(tk.END)  # 自动滚动到最新内容

    def flush(self):
        pass  # 实现flush方法（兼容print的flush参数）


if __name__ == '__main__':
    # 创建Tkinter窗口（服务器日志界面）
    root = tk.Tk()
    root.title("服务器日志")
    root.geometry("800x600")  # 窗口大小

    # 添加带滚动条的文本框（显示日志）
    text_area = scrolledtext.ScrolledText(root, width=80, height=30)
    text_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
    sys.stdout = PrintRedirector(text_area)  # 重定向stdout到文本框

    # 启动服务器（在独立线程中，避免阻塞GUI）
    server = ThreadedServer()
    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True  # 服务器线程随GUI退出
    server_thread.start()


    # 窗口关闭时的处理（停止服务器）
    def on_closing():
        server.running = False  # 停止服务器运行标志
        root.destroy()  # 关闭GUI窗口


    root.protocol("WM_DELETE_WINDOW", on_closing)  # 绑定窗口关闭事件
    root.mainloop()  # 启动GUI主循环