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
from root_dir import root_path  # 项目根路径配置
from yolo.yolo_main import YoloV8  # 引入YOLOv8模型（目标检测）
from config import MAX_WORKERS, TASK_QUEUE_SIZE, MODEL_WARMUP  # 全局配置
import paddle  # 新增

# 模型路径（OCR的检测/识别模型）
det_model_dir = os.path.join(
    root_path, "PP-OCRv5_server_det"
)  # OCR检测模型（定位文字区域）
rec_model_dir = os.path.join(
    root_path, "PP-OCRv5_server_rec"
)  # OCR识别模型（识别文字内容）


class ThreadedServer:
    """
    多线程图像处理服务器
    - 支持多客户端并发请求，通过多线程和任务队列实现。
    - 根据客户端请求类型，调用YOLO（目标检测）或OCR（文字识别）模型处理图像。
    - 处理结果通过socket返回给客户端。
    """

    def __init__(self, host="0.0.0.0", port=12345):
        """
        初始化服务器，设置监听地址、任务队列和线程池。
        :param host: 监听IP，默认所有网卡
        :param port: 监听端口
        """
        self.server_address = (host, port)  # 服务器监听地址
        self.task_queue = Queue(maxsize=TASK_QUEUE_SIZE)  # 任务队列
        self.workers = []  # 工作线程列表
        self.running = False  # 服务器运行状态标志

    def start(self):
        """
        启动服务器：初始化工作线程和监听线程
        """
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
        """
        独立监听线程：持续接收客户端连接，将连接放入任务队列
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # 允许端口复用
        sock.bind(self.server_address)
        sock.listen(10)  # 最大等待连接数
        try:
            while self.running:
                conn, addr = sock.accept()  # 阻塞等待客户端连接
                self.task_queue.put((conn, addr))  # 放入任务队列
        finally:
            sock.close()  # 服务器停止时关闭socket

    def _worker(self):
        """
        工作线程：每个线程独立初始化模型，从任务队列取连接并处理
        """
        # 初始化YOLO模型（目标检测）
        yolo = YoloV8()
        yolo.loadModel()

        # 判断CUDA是否可用，自动选择GPU或CPU
        use_gpu = paddle.device.is_compiled_with_cuda()
        # 初始化OCR模型（文字识别）
        ocr_engine = PaddleOCR(
            text_detection_model_dir="PP-OCRv5_server_det",  # 文字检测模型路径
            text_recognition_model_dir="PP-OCRv5_server_rec",  # 文字识别模型路径
            use_doc_orientation_classify=False,  # 不使用方向分类
            use_doc_unwarping=False,  # 不使用文档矫正
            use_textline_orientation=False,  # 不使用文字方向分类
            return_word_box=False,  # 不返回单字位置
            text_rec_score_thresh=0.85,  # 文字检测置信度阈值
            device="GPU" if use_gpu else "CPU",  # 是否使用GPU
        )

        # 模型预热（用空图像触发首次推理，加载权重到内存/GPU，减少后续请求延迟）
        if MODEL_WARMUP:
            dummy = np.zeros((640, 640, 3), dtype=np.uint8)  # 生成空图像
            yolo.detect(dummy)  # YOLO预热
            ocr_engine.predict(dummy)  # OCR预热

        print(f"线程 {threading.get_ident()} 模型初始化完成")

        while self.running:
            try:
                # 从任务队列取连接（超时1秒，避免线程一直阻塞）
                conn, addr = self.task_queue.get(timeout=1)
                self._handle_client(conn, addr, yolo, ocr_engine)  # 处理客户端请求
            except queue.Empty:
                continue  # 队列空时继续等待

    def _handle_client(self, conn, addr, yolo, ocr_engine):
        """
        处理单个客户端请求：接收图像→调用模型处理→返回结果
        """
        try:
            with conn:  # 自动关闭连接
                formatted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"{formatted_time}\t新连接: {addr}")

                while True:
                    # 接收客户端发送的消息（包含图像和请求头）
                    header, image = self._receive_message(conn)
                    if not header:  # 客户端断开连接时退出循环
                        break

                    start_time = time.time()  # 记录处理开始时间

                    # 根据请求类型调用对应模型处理
                    if header["type"] == "game_windows":
                        result = yolo.detect(image)
                    elif header["type"] == "min_map":
                        result = yolo.min_map_detect(image)
                    elif header["type"] == "ocr":
                        result = self._ocr_process(image, ocr_engine)
                    else:
                        raise ValueError("无效的请求类型")

                    # 将处理结果发送给客户端
                    self._send_response(conn, result, header["type"])

                    # 计算并打印处理耗时
                    latency = (time.time() - start_time) * 1000
                    print(f"请求处理完成 耗时: {latency:.2f}ms")

        except Exception as e:
            traceback.print_exc()  # 打印异常堆栈
            print(f"客户端 {addr} 处理异常: {str(e)}")

    def _receive_message(self, conn):
        """
        接收客户端消息：解析消息头→接收图像数据→解码为OpenCV格式
        消息格式：
        1. 4字节（uint32）：消息头长度（header_size）
        2. header_size字节：消息头（JSON格式，包含请求类型、图像大小等）
        3. 图像大小字节：图像数据（二进制，JPG/PNG编码）
        """
        try:
            # 接收消息头长度（4字节，大端格式）
            header_len = conn.recv(4)
            if len(header_len) < 4:  # 未收到完整的头长度
                return None, None

            header_size = struct.unpack("!I", header_len)[0]  # 解析为无符号整数
            header_data = conn.recv(header_size)  # 接收消息头数据
            header = json.loads(header_data.decode("utf-8"))  # 解码为字典

            # 接收图像数据
            image_size = header["image_size"]  # 从消息头获取图像总大小
            received = 0
            chunks = []
            while received < image_size:
                chunk = conn.recv(min(4096, image_size - received))
                if not chunk:  # 客户端断开
                    break
                chunks.append(chunk)
                received += len(chunk)

            # 将二进制数据解码为OpenCV图像（BGR格式）
            image = cv2.imdecode(
                np.frombuffer(b"".join(chunks), dtype=np.uint8), cv2.IMREAD_COLOR
            )
            return header, image

        except (socket.timeout, ConnectionResetError):
            return None, None  # 连接超时或被客户端重置

    def _send_response(self, conn, data, msg_type):
        """
        向客户端发送处理结果：构建响应头→发送头→发送结果数据
        响应格式：
        1. 4字节：响应头长度
        2. 响应头字节：JSON格式（包含响应类型、结果数据大小）
        3. 结果数据字节：JSON编码的处理结果
        """
        try:
            json_data = json.dumps(data).encode("utf-8")  # 结果数据序列化
            header = json.dumps(
                {
                    "type": msg_type,  # 与请求类型一致
                    "data_size": len(json_data),  # 结果数据大小
                }
            ).encode(
                "utf-8"
            )  # 响应头序列化

            # 发送响应头长度→响应头→结果数据
            conn.sendall(struct.pack("!I", len(header)))
            conn.sendall(header)
            conn.sendall(json_data)
        except BrokenPipeError:
            print("客户端连接已中断")  # 客户端提前断开

    def _ocr_process(self, image, ocr_engine):
        """
        OCR处理流程：直接调用OCR模型，拼接所有识别文本
        :param image: 输入图像（BGR格式）
        :param ocr_engine: PaddleOCR实例
        :return: 拼接后的识别文本字符串
        """
        rec_texts = ocr_engine.predict(image)[0]["rec_texts"]
        joined_text = "".join(rec_texts)  # 拼接所有文字为字符串
        print(joined_text)  # 打印识别结果
        return joined_text
