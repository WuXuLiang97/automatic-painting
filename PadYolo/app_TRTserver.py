# -*- coding: utf-8 -*-
import os
import queue
import struct
import socket
import time
import traceback
import cv2
import json
import numpy as np
from datetime import datetime
import threading
from queue import Queue
from paddleocr import PaddleOCR
import tkinter as tk
from tkinter import scrolledtext
import sys
import gc
import random

import tensorrt as trt
import ctypes

from root_dir import root_path

# ============ 全局配置 ============
MAX_WORKERS = 1
TASK_QUEUE_SIZE = 5
MODEL_WARMUP = True
BUFFER_SIZE = 4096
HEADER_SIZE = 4
FIXED_PORT = 12345
CONNECTION_TIMEOUT = 30            # 客户端超时 (秒)
ACCEPT_TIMEOUT = 1                 # accept 轮询间隔
WORKER_CRASH_THRESHOLD = 3         # 连续崩溃阈值
CUDA_CLEANUP_INTERVAL = 60         # CUDA 清理间隔 (秒)
CUDA_CLEANUP_COUNT = 1000          # 每 N 次推理后清理 CUDA
MODEL_RELOAD_INTERVAL = 18000       # 模型定期重载间隔 (秒), 300分钟

# OCR模型路径
DET_MODEL_DIR = os.path.join(root_path, 'ch_PP-OCRv4_det_infer')
REC_MODEL_DIR = os.path.join(root_path, 'ch_PP-OCRv4_rec_infer')

# YOLO 模型路径
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

MIN_MAP_MODEL_PATH = os.path.join(root_path, 'yolo/model_data/min_map_best.onnx')
MIN_MAP_ENGINE_PATH = os.path.join(root_path, 'yolo/model_data/min_map_best.engine')
MIN_MAP_CLASS_NAMES = ['map_hero', 'map_boss', 'map_query', 'map_elite', 'map_special', 'map_query_1']


def convert_to_serializable(obj):
    if isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, tuple):
        return tuple(convert_to_serializable(item) for item in obj)
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {convert_to_serializable(key): convert_to_serializable(value) for key, value in obj.items()}
    return obj


class YOLOv8TRTInfer:
    """YOLOv8 TensorRT 推理封装"""

    def __init__(self, onnx_path, engine_path, class_names, input_shape=(640, 640),
                 conf_thres=0.25, nms_thres=0.45):
        self.onnx_path = onnx_path
        self.engine_path = engine_path
        self.class_names = class_names
        self.input_shape = input_shape
        self.conf_thres = conf_thres
        self.nms_thres = nms_thres
        self.TRT_LOGGER = trt.Logger(trt.Logger.WARNING)
        self.engine = None
        self.context = None
        self.cuda_mem = self.SimpleCudaMem()
        self._init_lock = threading.Lock()
        self.inference_count = 0
        self._init_engine()

    class SimpleCudaMem:
        def __init__(self):
            _libs = ["nvcuda.dll", "cuda", "nvcuda"]
            self.cuda = None
            for lib in _libs:
                try:
                    self.cuda = ctypes.CDLL(lib)
                    break
                except OSError:
                    continue
            if self.cuda is None:
                raise RuntimeError("无法加载 CUDA 运行时库")
            self.cuda.cuMemAlloc_v2.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_ulonglong]
            self.cuda.cuMemFree_v2.argtypes = [ctypes.c_void_p]
            self.cuda.cuMemcpyHtoD_v2.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulonglong]
            self.cuda.cuMemcpyDtoH_v2.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulonglong]

        def alloc(self, size):
            ptr = ctypes.c_void_p()
            err = self.cuda.cuMemAlloc_v2(ctypes.byref(ptr), size)
            if err != 0:
                raise MemoryError(f"cuMemAlloc 失败, 错误码: {err}")
            return ptr

        def free(self, ptr):
            if ptr:
                self.cuda.cuMemFree_v2(ptr)

        def h2d(self, dst, src, size):
            self.cuda.cuMemcpyHtoD_v2(dst, src, size)

        def d2h(self, dst, src, size):
            self.cuda.cuMemcpyDtoH_v2(dst, src, size)

    def _init_engine(self):
        with self._init_lock:
            if os.path.exists(self.engine_path):
                self.engine = self._load_engine()
            else:
                self._build_engine()
                self.engine = self._load_engine()
            if self.context:
                del self.context
            self.context = self.engine.create_execution_context()

    def _build_engine(self):
        builder = trt.Builder(self.TRT_LOGGER)
        network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
        config = builder.create_builder_config()
        config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, 2 << 30)
        if builder.platform_has_fast_fp16:
            config.set_flag(trt.BuilderFlag.FP16)
        parser = trt.OnnxParser(network, self.TRT_LOGGER)
        with open(self.onnx_path, 'rb') as f:
            if not parser.parse(f.read()):
                raise RuntimeError("ONNX模型解析失败")
        serialized_engine = builder.build_serialized_network(network, config)
        with open(self.engine_path, 'wb') as f:
            f.write(serialized_engine)

    def _load_engine(self):
        with open(self.engine_path, 'rb') as f:
            runtime = trt.Runtime(self.TRT_LOGGER)
            return runtime.deserialize_cuda_engine(f.read())

    def _letterbox(self, img):
        h, w = img.shape[:2]
        ratio = min(self.input_shape[0] / h, self.input_shape[1] / w)
        new_w, new_h = int(round(w * ratio)), int(round(h * ratio))
        top = (self.input_shape[0] - new_h) // 2
        left = (self.input_shape[1] - new_w) // 2
        bottom = self.input_shape[0] - new_h - top
        right = self.input_shape[1] - new_w - left
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114))
        return img, ratio, top, left

    def _preprocess(self, img):
        img, ratio, top, left = self._letterbox(img)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.transpose(2, 0, 1).astype(np.float32) / 255.0
        return np.ascontiguousarray(img[None]), ratio, top, left

    @staticmethod
    def _xywh2xyxy(x):
        y = np.copy(x)
        y[..., 0] = x[..., 0] - x[..., 2] / 2
        y[..., 1] = x[..., 1] - x[..., 3] / 2
        y[..., 2] = x[..., 0] + x[..., 2] / 2
        y[..., 3] = x[..., 1] + x[..., 3] / 2
        return y

    def _nms(self, boxes, scores):
        x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
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
            order = order[inds + 1] if (inds := np.where(ovr <= self.nms_thres)[0]).size > 0 else np.array([], dtype=int)
        return keep

    def _postprocess(self, output, img, ratio, top, left):
        pred = output[0].T
        boxes = self._xywh2xyxy(pred[:, :4])
        cls_scores = pred[:, 4:]
        max_scores = cls_scores.max(axis=1)
        classes = cls_scores.argmax(axis=1)
        mask = max_scores > self.conf_thres
        boxes, scores, classes = boxes[mask], max_scores[mask], classes[mask]
        if len(boxes) == 0:
            return []
        boxes[:, [0, 2]] -= left
        boxes[:, [1, 3]] -= top
        boxes /= ratio
        h, w = img.shape[:2]
        boxes = np.clip(boxes, 0, [w, h, w, h]).astype(np.int32)
        indices = self._nms(boxes, scores)
        res = []
        for i in indices:
            x1, y1, x2, y2 = boxes[i]
            cls_id = int(classes[i])
            label = self.class_names[cls_id] if 0 <= cls_id < len(self.class_names) else "unknown"
            res.append((label, int(x1), int(y1), int(x2), int(y2), float(scores[i])))
        return res

    def predict(self, image):
        d_input, d_output = None, None
        try:
            if isinstance(image, str):
                img = cv2.imread(image)
                if img is None:
                    raise ValueError("图片读取失败")
            else:
                img = image
            input_data, ratio, top, left = self._preprocess(img)
            input_size = input_data.nbytes
            output_shape = self.engine.get_tensor_shape(self.engine.get_tensor_name(1))
            output_size = int(np.prod(output_shape)) * 4

            d_input = self.cuda_mem.alloc(input_size)
            d_output = self.cuda_mem.alloc(output_size)
            self.cuda_mem.h2d(d_input, input_data.ctypes.data, input_size)
            self.context.execute_v2([d_input.value, d_output.value])

            output = np.empty(output_shape, dtype=np.float32)
            self.cuda_mem.d2h(output.ctypes.data, d_output, output_size)

            self.inference_count += 1
            return self._postprocess(output, img, ratio, top, left)

        except Exception:
            # 推理异常时尝试重建引擎
            try:
                self._init_engine()
            except Exception:
                pass
            raise
        finally:
            if d_input:
                try:
                    self.cuda_mem.free(d_input)
                except Exception:
                    pass
            if d_output:
                try:
                    self.cuda_mem.free(d_output)
                except Exception:
                    pass

    def maybe_cleanup_cuda(self):
        """定期清理 CUDA 缓存"""
        if self.inference_count > 0 and self.inference_count % CUDA_CLEANUP_COUNT == 0:
            gc.collect()
            # 不调用 torch.cuda.empty_cache() 因为这里用的是纯 TensorRT + ctypes

    def __del__(self):
        try:
            if hasattr(self, 'context') and self.context:
                del self.context
            if hasattr(self, 'engine') and self.engine:
                del self.engine
        except Exception:
            pass


class YoloV8TRT:
    """与原 YoloV8 接口兼容的封装"""

    def __init__(self):
        self.game_windows_model = None
        self.min_map_model = None

    def loadModel(self):
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
        return self.game_windows_model.predict(image)

    def min_map_detect(self, image):
        return self.min_map_model.predict(image)


class ThreadedServer:
    """多线程推理服务器 (带健康监控和自动恢复)"""

    def __init__(self, host='0.0.0.0', port=FIXED_PORT):
        self.server_address = (host, port)
        self.task_queue = Queue(maxsize=TASK_QUEUE_SIZE)
        self.workers = []
        self._worker_lock = threading.Lock()
        self.running = False
        self.active_connections = 0
        self._conn_lock = threading.Lock()

    def start(self):
        self.running = True
        self._spawn_all_workers()

        listener = threading.Thread(target=self._listen, daemon=True)
        listener.start()

        # 健康监控线程：检测死 worker 并重启
        monitor = threading.Thread(target=self._health_monitor, daemon=True)
        monitor.start()

        print(f"服务器已启动 {self.server_address[0]}:{self.server_address[1]}")
        print(f"工作线程: {MAX_WORKERS} | 任务队列: {TASK_QUEUE_SIZE}")
        listener.join()

    def _spawn_all_workers(self):
        with self._worker_lock:
            self.workers.clear()
            for i in range(MAX_WORKERS):
                w = threading.Thread(target=self._worker, daemon=True, name=f"Worker-{i}")
                w.start()
                self.workers.append(w)

    def _spawn_one_worker(self):
        """补充一个工作线程"""
        with self._worker_lock:
            alive = [w for w in self.workers if w.is_alive()]
            if len(alive) < MAX_WORKERS:
                idx = len(alive)
                w = threading.Thread(target=self._worker, daemon=True, name=f"Worker-{idx}")
                w.start()
                self.workers.append(w)
                print(f"已补充新 Worker: {w.name} (当前存活: {len(alive) + 1})")

    def _listen(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        sock.bind(self.server_address)
        sock.listen(10)
        sock.settimeout(ACCEPT_TIMEOUT)

        try:
            while self.running:
                try:
                    conn, addr = sock.accept()
                    self._configure_client(conn)
                    # 队列满时拒绝连接，防止内存爆炸
                    if self.task_queue.full():
                        print(f"任务队列已满, 拒绝: {addr}")
                        conn.close()
                        continue
                    self.task_queue.put((conn, addr))
                except socket.timeout:
                    continue
                except OSError:
                    if self.running:
                        traceback.print_exc()
                    break
        finally:
            try:
                sock.close()
            except Exception:
                pass

    def _configure_client(self, conn):
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        conn.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 256 * 1024)
        conn.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 256 * 1024)
        conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 30)
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
        conn.settimeout(CONNECTION_TIMEOUT)

    def _worker(self):
        """工作线程: 独立初始化模型, 处理连接"""
        crash_count = 0
        yolo, ocr_engine = None, None

        while self.running:
            try:
                # 初始化模型
                yolo = YoloV8TRT()
                yolo.loadModel()
                ocr_engine = PaddleOCR(
                    lang='ch',
                    det_model_dir=DET_MODEL_DIR,
                    rec_model_dir=REC_MODEL_DIR,
                    use_gpu=True,
                    use_angle_cls=False,
                    use_space_char=False,
                    show_log=False,
                    enable_mkldnn=False,
                )
                if MODEL_WARMUP:
                    self._warmup_models(yolo, ocr_engine)

                print(f"[{threading.current_thread().name}] 模型初始化完成")
                crash_count = 0

                # 主处理循环
                while self.running:
                    try:
                        conn, addr = self.task_queue.get(timeout=1)
                    except queue.Empty:
                        if self._periodic_cleanup(yolo, ocr_engine):
                            # 需要重载模型, 跳出内循环触发外层重建
                            break
                        continue

                    try:
                        with self._conn_lock:
                            self.active_connections += 1
                        self._handle_client(conn, addr, yolo, ocr_engine)
                    finally:
                        with self._conn_lock:
                            self.active_connections -= 1
                        self.task_queue.task_done()

            except Exception as e:
                crash_count += 1
                print(f"[{threading.current_thread().name}] 崩溃 (第{crash_count}次): {e}")
                traceback.print_exc()

                if crash_count >= WORKER_CRASH_THRESHOLD:
                    print(f"[{threading.current_thread().name}] 连续崩溃{crash_count}次, 放弃该 Worker")
                    break

                backoff = min(30, 2 ** crash_count)
                print(f"[{threading.current_thread().name}] {backoff}秒后重试...")
                time.sleep(backoff)

            # 内循环退出后始终清理旧模型（正常重载 or 异常恢复）
            self._cleanup_models(yolo, ocr_engine)
            yolo, ocr_engine = None, None

    def _warmup_models(self, yolo, ocr_engine):
        dummy = np.zeros((640, 640, 3), dtype=np.uint8)
        yolo.detect(dummy)
        gray = cv2.cvtColor(dummy, cv2.COLOR_BGR2GRAY)
        ocr_engine.ocr(gray, det=False, cls=False)

    def _periodic_cleanup(self, yolo, ocr_engine):
        """定期资源清理。返回 True 表示需要重载模型。"""
        now = time.time()
        if not hasattr(self, '_last_cleanup'):
            self._last_cleanup = now
            self._last_model_reload = now
            yolo.game_windows_model.maybe_cleanup_cuda()
            return False
        # CUDA 碎片清理
        if now - self._last_cleanup > CUDA_CLEANUP_INTERVAL:
            self._last_cleanup = now
            yolo.game_windows_model.maybe_cleanup_cuda()
            gc.collect()
        # 定期重载模型防止 GPU 碎片化
        if now - self._last_model_reload > MODEL_RELOAD_INTERVAL:
            self._last_model_reload = now
            self._cleanup_models(yolo, ocr_engine)
            print(f"[{threading.current_thread().name}] 定期重载模型")
            return True
        return False

    @staticmethod
    def _cleanup_models(yolo, ocr_engine):
        for obj in (yolo, ocr_engine):
            try:
                if obj is not None:
                    del obj
            except Exception:
                pass
        gc.collect()

    def _health_monitor(self):
        """监控 Worker 存活, 自动补充"""
        while self.running:
            time.sleep(5)
            with self._worker_lock:
                alive = [w for w in self.workers if w.is_alive()]
                # 清理死线程引用
                self.workers = alive
                dead = MAX_WORKERS - len(alive)
                if dead > 0:
                    print(f"检测到 {dead} 个 Worker 已死亡, 正在补充...")
                    for _ in range(dead):
                        self._spawn_one_worker()
                # 清理队列中堆积的旧任务
                while not self.task_queue.empty():
                    try:
                        stale = self.task_queue.get_nowait()
                        try:
                            stale[0].close()
                        except Exception:
                            pass
                    except queue.Empty:
                        break

    def _handle_client(self, conn, addr, yolo, ocr_engine):
        try:
            with conn:
                print(f"{datetime.now().strftime('%H:%M:%S')}\t连接: {addr}")
                while self.running:
                    header, image = self._receive_message(conn)
                    if not header:
                        break

                    t0 = time.time()
                    result = self._process(header, image, yolo, ocr_engine)
                    self._send_response(conn, result, header['type'])

                    latency = (time.time() - t0) * 1000
                    print(f"  {header['type']} | {latency:.1f}ms | 活跃连接: {self.active_connections}")
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError, socket.timeout):
            pass  # 客户端断开不算服务器异常

    def _process(self, header, image, yolo, ocr_engine):
        req_type = header['type']
        if req_type == 'game_windows':
            return yolo.detect(image)
        elif req_type == 'min_map':
            return yolo.min_map_detect(image)
        elif req_type == 'ocr':
            return self._ocr_process(image, ocr_engine)
        raise ValueError(f"无效请求类型: {req_type}")

    def _receive_message(self, conn):
        try:
            header_len = self._recv_exact(conn, HEADER_SIZE)
            if not header_len:
                return None, None
            header_size = struct.unpack('!I', header_len)[0]
            header_data = self._recv_exact(conn, header_size)
            if not header_data:
                return None, None
            header = json.loads(header_data.decode('utf-8'))
            image_data = self._recv_exact(conn, header['image_size'])
            if not image_data:
                return None, None
            image = cv2.imdecode(np.frombuffer(image_data, dtype=np.uint8), cv2.IMREAD_COLOR)
            return header, image
        except (socket.timeout, ConnectionResetError, ConnectionAbortedError,
                json.JSONDecodeError, OSError, BrokenPipeError):
            return None, None

    def _recv_exact(self, conn, size):
        data = bytearray()
        while len(data) < size:
            try:
                chunk = conn.recv(min(BUFFER_SIZE, size - len(data)))
                if not chunk:
                    return None
                data.extend(chunk)
            except socket.timeout:
                return None
        return bytes(data)

    def _send_response(self, conn, data, msg_type):
        try:
            json_data = json.dumps(convert_to_serializable(data)).encode('utf-8')
            header = json.dumps({'type': msg_type, 'data_size': len(json_data)}).encode('utf-8')
            conn.sendall(struct.pack('!I', len(header)))
            conn.sendall(header)
            conn.sendall(json_data)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def _ocr_process(self, image, ocr_engine):
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            results = ocr_engine.ocr(gray, det=False, cls=False)
            text_parts = []
            for page in results:
                for line in page:
                    try:
                        text_parts.append(str(line[0]))
                    except (IndexError, TypeError):
                        continue
            return ''.join(text_parts)
        except Exception as e:
            print(f"OCR异常: {e}")
            return ""


class PrintRedirector:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.queue = queue.Queue()
        self.running = True
        self.thread = threading.Thread(target=self._pump, daemon=True)
        self.thread.start()

    def _pump(self):
        while self.running:
            try:
                while not self.queue.empty():
                    msg = self.queue.get_nowait()
                    self.text_widget.insert(tk.END, msg)
                    self.text_widget.see(tk.END)
                time.sleep(0.1)
            except Exception:
                break

    def write(self, message):
        self.queue.put(message)

    def flush(self):
        pass


if __name__ == '__main__':
    root = tk.Tk()
    root.title("TensorRT 推理服务器")
    root.geometry("800x600")

    text_area = scrolledtext.ScrolledText(root, width=80, height=30)
    text_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
    redirector = PrintRedirector(text_area)
    sys.stdout = redirector

    server = ThreadedServer()
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()

    def on_closing():
        server.running = False
        redirector.running = False
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
