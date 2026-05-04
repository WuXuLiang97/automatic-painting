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
import tkinter as tk  # 用于GUI界面（显示服务器日志）
from tkinter import scrolledtext
import sys

# TensorRT 相关导入
import tensorrt as trt
import ctypes

from root_dir import root_path  # 项目根路径配置

# 全局配置
MAX_WORKERS = 4  # 工作线程数量（根据CPU核心数调整，提高并发处理能力）
TASK_QUEUE_SIZE = 20  # 任务队列最大缓冲量（避免请求堆积溢出）
MODEL_WARMUP = True  # 模型预热开关（提前加载模型，减少首次推理延迟）

# 模型路径（OCR的检测/识别模型）
det_model_dir = os.path.join(root_path, 'ch_PP-OCRv4_det_infer')  # OCR检测模型（定位文字区域）
rec_model_dir = os.path.join(root_path, 'ch_PP-OCRv4_rec_infer')  # OCR识别模型（识别文字内容）

# YOLO 模型路径配置
# 游戏窗口检测模型
GAME_WINDOWS_MODEL_PATH = os.path.join(root_path, 'yolo/model_data/1_tensorrt_final.onnx')
GAME_WINDOWS_ENGINE_PATH = os.path.join(root_path, 'yolo/model_data/1_tensorrt_final.engine')
GAME_WINDOWS_CLASS_NAMES = ['player', 'door', 'goods', 'continue', 'reward', 'forward', 'monster', 'monster_frost',
                            'boss_dlsks_klj', 'boss_dlsks_qtzft', 'boss_sy', 'boss_fbnl_phzwh', 'boss_fbnl_phzwh_box',
                            'door_sy', 'boss_sy-zmcbz', 'boss_sy-zmcbz_box', 'attack_boss_sy', 'boss_dlsks_onsblk',
                            'boss_115_1', 'boss_115_1_box', 'boss_115_2', 'boss_115_2_box', 'boss_115_3',
                            'boss_115_3_box', 'boss_115_4', 'boss_115_4_box', 'monster_115_1', 'monster_115_1_box',
                            'monster_115_2', 'monster_115_2_box', 'monster_115_3', 'monster_115_3_box', 'monster_115_4',
                            'monster_115_4_box', 'monster_115_5', 'monster_115_5_box', 'boss_sy_1', 'monster_115_6',
                            'monster_115_6_box']

# 小地图检测模型
MIN_MAP_MODEL_PATH = os.path.join(root_path, 'yolo/model_data/min_map_best.onnx')
MIN_MAP_ENGINE_PATH = os.path.join(root_path, 'yolo/model_data/min_map_best.engine')
MIN_MAP_CLASS_NAMES = ['map_hero', 'map_boss', 'map_query', 'map_elite', 'map_special', 'map_query_1']


def convert_to_serializable(obj):
    """递归转换对象为JSON可序列化的Python原生类型"""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, tuple):
        return tuple(convert_to_serializable(item) for item in obj)
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {convert_to_serializable(key): convert_to_serializable(value) for key, value in obj.items()}
    else:
        return obj


class YOLOv8TRTInfer:
    """YOLOv8 TensorRT 封装推理类
    功能：高精度TensorRT推理，返回结果与Ultralytics YOLOv8 predict完全一致
    """

    def __init__(self, onnx_path, engine_path, class_names, input_shape=(640, 640),
                 conf_thres=0.25, nms_thres=0.45):
        """
        初始化TensorRT推理类
        :param onnx_path: ONNX模型路径
        :param engine_path: TensorRT引擎保存路径
        :param class_names: 类别名称列表
        :param input_shape: 模型输入尺寸 (w, h)
        :param conf_thres: 置信度阈值
        :param nms_thres: NMS IOU阈值
        """
        # 基础配置
        self.onnx_path = onnx_path
        self.engine_path = engine_path
        self.class_names = class_names
        self.input_shape = input_shape
        self.conf_thres = conf_thres
        self.nms_thres = nms_thres

        # TensorRT 核心对象
        self.TRT_LOGGER = trt.Logger(trt.Logger.WARNING)
        self.engine = None
        self.context = None
        self.cuda_mem = None
        self.input_name = None
        self.output_name = None

        # CUDA内存初始化
        self.cuda_mem = self.SimpleCudaMem()

        # 加载/构建引擎
        self._init_engine()

    class SimpleCudaMem:
        """CUDA内存操作封装（内部类）"""

        def __init__(self):
            self.cuda = ctypes.CDLL('nvcuda')
            self.cuda.cuMemAlloc_v2.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_ulonglong]
            self.cuda.cuMemFree_v2.argtypes = [ctypes.c_void_p]
            self.cuda.cuMemcpyHtoD_v2.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulonglong]
            self.cuda.cuMemcpyDtoH_v2.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulonglong]

        def alloc(self, size):
            ptr = ctypes.c_void_p()
            self.cuda.cuMemAlloc_v2(ctypes.byref(ptr), size)
            return ptr

        def free(self, ptr):
            self.cuda.cuMemFree_v2(ptr)

        def h2d(self, dst, src, size):
            self.cuda.cuMemcpyHtoD_v2(dst, src, size)

        def d2h(self, dst, src, size):
            self.cuda.cuMemcpyDtoH_v2(dst, src, size)

    def _init_engine(self):
        """初始化TensorRT引擎（内部调用）"""
        # 加载已有引擎
        if os.path.exists(self.engine_path):
            self.engine = self._load_engine()
        else:
            # 构建新引擎
            self._build_engine()
            self.engine = self._load_engine()

        # 创建执行上下文
        self.context = self.engine.create_execution_context()
        self.input_name = self.engine.get_tensor_name(0)
        self.output_name = self.engine.get_tensor_name(1)

    def _build_engine(self):
        """构建TensorRT引擎"""
        builder = trt.Builder(self.TRT_LOGGER)
        network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
        config = builder.create_builder_config()
        config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, 4 << 30)
        if builder.platform_has_fast_fp16:
            config.set_flag(trt.BuilderFlag.FP16)

        parser = trt.OnnxParser(network, self.TRT_LOGGER)
        with open(self.onnx_path, 'rb') as f:
            if not parser.parse(f.read()):
                raise RuntimeError("ONNX模型解析失败！")

        serialized_engine = builder.build_serialized_network(network, config)
        with open(self.engine_path, 'wb') as f:
            f.write(serialized_engine)

    def _load_engine(self):
        """加载TensorRT引擎"""
        with open(self.engine_path, 'rb') as f:
            runtime = trt.Runtime(self.TRT_LOGGER)
            return runtime.deserialize_cuda_engine(f.read())

    def _letterbox(self, img):
        """图像等比例缩放+填充"""
        h, w = img.shape[:2]
        ratio = min(self.input_shape[0] / h, self.input_shape[1] / w)
        new_w = int(round(w * ratio))
        new_h = int(round(h * ratio))
        top = (self.input_shape[0] - new_h) // 2
        left = (self.input_shape[1] - new_w) // 2
        bottom = self.input_shape[0] - new_h - top
        right = self.input_shape[1] - new_w - left

        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114))
        return img, ratio, top, left

    def _preprocess(self, img):
        """图像预处理"""
        img, ratio, top, left = self._letterbox(img)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.transpose(2, 0, 1).astype(np.float32) / 255.0
        return np.ascontiguousarray(img[None]), ratio, top, left

    @staticmethod
    def _xywh2xyxy(x):
        """坐标格式转换"""
        y = np.copy(x)
        y[..., 0] = x[..., 0] - x[..., 2] / 2
        y[..., 1] = x[..., 1] - x[..., 3] / 2
        y[..., 2] = x[..., 0] + x[..., 2] / 2
        y[..., 3] = x[..., 1] + x[..., 3] / 2
        return y

    def _nms(self, boxes, scores):
        """非极大值抑制"""
        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]
        areas = (x2 - x1) * (y2 - y1)
        order = scores.argsort()[::-1]
        keep = []

        while order.size > 0:
            i = order[0]
            keep.append(i)
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            w = np.maximum(0.0, xx2 - xx1)
            h = np.maximum(0.0, yy2 - yy1)
            inter = w * h
            ovr = inter / (areas[i] + areas[order[1:]] - inter)
            inds = np.where(ovr <= self.nms_thres)[0]
            order = order[inds + 1]
        return keep

    def _postprocess(self, output, img, ratio, top, left):
        """
        后处理：返回和YOLO一致的结果列表
        :return: [(label, x1, y1, x2, y2, confidence), ...]
        """
        pred = output[0].T
        boxes = self._xywh2xyxy(pred[:, :4])
        cls_scores = pred[:, 4:]
        max_scores = cls_scores.max(axis=1)
        classes = cls_scores.argmax(axis=1)
        mask = max_scores > self.conf_thres

        boxes, scores, classes = boxes[mask], max_scores[mask], classes[mask]
        if len(boxes) == 0:
            return []

        # 坐标还原到原图
        boxes[:, [0, 2]] -= left
        boxes[:, [1, 3]] -= top
        boxes /= ratio

        h, w = img.shape[:2]
        boxes = np.clip(boxes, 0, [w, h, w, h]).astype(np.int32)

        # NMS
        indices = self._nms(boxes, scores)

        # 构造YOLO格式结果（转换为Python原生类型）
        res = []
        for i in indices:
            x1, y1, x2, y2 = boxes[i]
            cls_id = int(classes[i])  # 转换为Python int
            conf = float(scores[i])  # 转换为Python float
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)  # 转换为Python int
            label = self.class_names[cls_id] if 0 <= cls_id < len(self.class_names) else "unknown"
            res.append((label, x1, y1, x2, y2, conf))
        return res

    def predict(self, image):
        """
        对外核心接口：与YOLOv8 predict返回格式完全一致
        :param image: 图片路径 或 cv2读取的BGR图像
        :return: 检测结果列表 [(label, x1, y1, x2, y2, confidence), ...]
        """
        d_input, d_output = None, None
        try:
            # 1. 读取图像
            if isinstance(image, str):
                img = cv2.imread(image)
                if img is None:
                    raise ValueError("图片读取失败！")
            else:
                img = image

            # 2. 预处理
            input_data, ratio, top, left = self._preprocess(img)

            # 3. 分配显存
            input_size = input_data.nbytes
            output_shape = self.engine.get_tensor_shape(self.output_name)
            output_size = np.prod(output_shape) * 4

            d_input = self.cuda_mem.alloc(input_size)
            d_output = self.cuda_mem.alloc(output_size)

            # 4. 推理
            self.cuda_mem.h2d(d_input, input_data.ctypes.data, input_size)
            self.context.execute_v2([d_input.value, d_output.value])

            # 5. 获取结果
            output = np.empty(output_shape, dtype=np.float32)
            self.cuda_mem.d2h(output.ctypes.data, d_output, output_size)

            # 6. 后处理返回结果
            return self._postprocess(output, img, ratio, top, left)

        finally:
            # 释放显存
            if d_input:
                self.cuda_mem.free(d_input)
            if d_output:
                self.cuda_mem.free(d_output)

    def __del__(self):
        """析构函数：释放所有资源"""
        if hasattr(self, 'context') and self.context:
            del self.context
        if hasattr(self, 'engine') and self.engine:
            del self.engine


class YoloV8TRT:
    """YOLOv8 TensorRT 统一接口类
    提供与原 YoloV8 类相同的接口方法，内部使用 TensorRT 推理
    直接暴露 YOLOv8TRTInfer 实例，保持与 tensorrt_native.py 相同的使用方式
    """

    def __init__(self):
        self.game_windows_model = None
        self.min_map_model = None

    def loadModel(self):
        """加载模型（与原 YoloV8 接口一致）"""
        # 直接使用 YOLOv8TRTInfer 初始化，保持原有方式
        self.game_windows_model = YOLOv8TRTInfer(
            onnx_path=GAME_WINDOWS_MODEL_PATH,
            engine_path=GAME_WINDOWS_ENGINE_PATH,
            class_names=GAME_WINDOWS_CLASS_NAMES,
            input_shape=(640, 640),
            conf_thres=0.25,
            nms_thres=0.45
        )

        self.min_map_model = YOLOv8TRTInfer(
            onnx_path=MIN_MAP_MODEL_PATH,
            engine_path=MIN_MAP_ENGINE_PATH,
            class_names=MIN_MAP_CLASS_NAMES,
            input_shape=(640, 640),
            conf_thres=0.25,
            nms_thres=0.45
        )

    def detect(self, image):
        """游戏窗口目标检测

        返回格式与 YOLOv8TRTInfer.predict 完全一致：
        [(label, x1, y1, x2, y2, confidence), ...]
        """
        return self.game_windows_model.predict(image)

    def min_map_detect(self, image):
        """小地图目标检测

        返回格式与 YOLOv8TRTInfer.predict 完全一致：
        [(label, x1, y1, x2, y2, confidence), ...]
        """
        return self.min_map_model.predict(image)


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
        # 初始化YOLO模型（使用 TensorRT 加速）
        yolo = YoloV8TRT()
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

        print(f"线程 {threading.get_ident()} 模型初始化完成\n")

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
                        # 处理"游戏窗口"目标检测
                        # 返回格式: [(label, x1, y1, x2, y2, confidence), ...]
                        result = yolo.detect(image)
                    elif header['type'] == 'min_map':
                        # 处理"小地图"目标检测
                        # 返回格式: [(label, x1, y1, x2, y2, confidence), ...]
                        result = yolo.min_map_detect(image)
                    elif header['type'] == 'ocr':
                        # 处理文字识别
                        result = self._ocr_process(image, ocr_engine)
                    else:
                        raise ValueError("无效的请求类型")

                    # 将处理结果发送给客户端（转换数据为JSON可序列化格式）
                    self._send_response(conn, result, header['type'])

                    # 计算并打印处理耗时（用于性能监控）
                    latency = (time.time() - start_time) * 1000
                    print(f"{header['type']} 请求处理完成 耗时: {latency:.2f}ms")

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
            # 转换数据为JSON可序列化格式
            serializable_data = convert_to_serializable(data)
            json_data = json.dumps(serializable_data).encode('utf-8')
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

    # def _ocr_process(self, image, ocr_engine):
    #     """OCR处理流程：转为灰度图→调用OCR→拼接识别结果"""
    #     gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # 转为灰度图（减少计算量，提高OCR精度）
    #     results = ocr_engine.ocr(gray, det=False, cls=False)  # 仅识别（不检测文字区域，假设输入是纯文字图像）
    #     # 拼接所有识别结果（PaddleOCR返回格式：[[(文字, 置信度), ...]]）
    #     return ''.join(line[0] for page in results for line in page)

    def _ocr_process(self, image: np.ndarray, ocr_engine: PaddleOCR) -> str:
        """处理OCR请求"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            results = ocr_engine.ocr(gray, det=False, cls=False)

            # 保持原有格式但添加异常处理
            text_parts = []
            for page in results:
                for line in page:
                    try:
                        text_parts.append(str(line[0]))
                    except (IndexError, TypeError):
                        # 跳过有问题的行
                        continue

            return ''.join(text_parts)

        except Exception as e:
            print(f"OCR处理异常: {e}")
            return ""


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