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
from yolo.yolo_main import YoloV8
from root_dir import root_path
import tkinter as tk
from tkinter import scrolledtext
import sys

# 全局配置
MAX_WORKERS = 4  # 根据CPU核心数调整
TASK_QUEUE_SIZE = 20  # 任务队列缓冲
MODEL_WARMUP = True  # 启用模型预热

# 模型初始化
det_model_dir = os.path.join(root_path, 'ch_PP-OCRv4_det_infer')
rec_model_dir = os.path.join(root_path, 'ch_PP-OCRv4_rec_infer')


class ModelManager:
    """线程安全的模型管理器"""
    _yolo_lock = threading.Lock()
    _ocr_lock = threading.Lock()
    _yolo_instance = None
    _ocr_instance = None

    @classmethod
    def get_yolo(cls):
        with cls._yolo_lock:
            if cls._yolo_instance is None:
                cls._yolo_instance = YoloV8()
                cls._yolo_instance.loadModel()
                if MODEL_WARMUP:
                    dummy = np.zeros((640, 640, 3), dtype=np.uint8)
                    cls._yolo_instance.detect(dummy)
            return cls._yolo_instance

    @classmethod
    def get_ocr(cls):
        with cls._ocr_lock:
            if cls._ocr_instance is None:
                cls._ocr_instance = PaddleOCR(
                    lang='ch',
                    det_model_dir=det_model_dir,
                    rec_model_dir=rec_model_dir,
                    use_gpu=True
                )
            return cls._ocr_instance


class ThreadedServer:
    def __init__(self, host='0.0.0.0', port=12345):
        self.server_address = (host, port)
        self.task_queue = Queue(maxsize=TASK_QUEUE_SIZE)
        self.workers = []
        self.running = False

        # 提前初始化模型
        self.warmup_models()

    def warmup_models(self):
        """预加载模型避免首次请求延迟"""
        if MODEL_WARMUP:
            print("预热模型中...")
            ModelManager.get_yolo()
            ModelManager.get_ocr()
            print("模型预热完成")

    def start(self):
        self.running = True
        # 启动工作线程
        for _ in range(MAX_WORKERS):
            worker = threading.Thread(target=self._worker)
            worker.daemon = True
            worker.start()
            self.workers.append(worker)

        # 启动网络监听线程
        listener = threading.Thread(target=self._listen)
        listener.start()
        print(f"服务器已启动在 {self.server_address[0]}:{self.server_address[1]}")
        listener.join()

    def _listen(self):
        """独立监听线程"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(self.server_address)
        sock.listen(10)

        try:
            while self.running:
                conn, addr = sock.accept()
                self.task_queue.put((conn, addr))
        finally:
            sock.close()

    def _worker(self):
        """工作线程处理逻辑"""
        yo = ModelManager.get_yolo()
        ocr_engine = ModelManager.get_ocr()

        while self.running:
            try:
                conn, addr = self.task_queue.get(timeout=1)
                self._handle_client(conn, addr, yo, ocr_engine)
            except queue.Empty:
                continue

    def _handle_client(self, conn, addr, yolo, ocr_engine):
        """处理客户端请求"""
        try:
            with conn:
                formatted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"{formatted_time}\t新连接: {addr}")

                while True:
                    header, image = self._receive_message(conn)
                    if not header:
                        break

                    start_time = time.time()

                    # 处理请求
                    if header['type'] == 'game_windows':
                        result = yolo.detect(image)
                    elif header['type'] == 'min_map':
                        result = yolo.min_map_detect(image)
                    elif header['type'] == 'ocr':
                        result = self._ocr_process(image, ocr_engine)
                    else:
                        raise ValueError("无效的请求类型")

                    # 发送响应
                    self._send_response(conn, result, header['type'])

                    latency = (time.time() - start_time) * 1000
                    print(f"请求处理完成 耗时: {latency:.2f}ms")

        except Exception as e:
            traceback.print_exc()
            print(f"客户端 {addr} 处理异常: {str(e)}")

    def _receive_message(self, conn):
        """优化后的消息接收方法"""
        try:
            # 接收消息头长度
            header_len = conn.recv(4)
            if len(header_len) < 4:
                return None, None

            header_size = struct.unpack('!I', header_len)[0]
            header_data = conn.recv(header_size)
            header = json.loads(header_data.decode('utf-8'))

            # 接收图片数据
            image_size = header['image_size']
            received = 0
            chunks = []
            while received < image_size:
                chunk = conn.recv(min(4096, image_size - received))
                if not chunk:
                    break
                chunks.append(chunk)
                received += len(chunk)

            image = cv2.imdecode(np.frombuffer(b''.join(chunks), dtype=np.uint8), cv2.IMREAD_COLOR)
            return header, image

        except (socket.timeout, ConnectionResetError):
            return None, None

    def _send_response(self, conn, data, msg_type):
        """优化后的响应发送"""
        try:
            json_data = json.dumps(data).encode('utf-8')
            header = json.dumps({
                'type': msg_type,
                'data_size': len(json_data)
            }).encode('utf-8')

            conn.sendall(struct.pack('!I', len(header)))
            conn.sendall(header)
            conn.sendall(json_data)
        except BrokenPipeError:
            print("客户端连接已中断")

    def _ocr_process(self, image, ocr_engine):
        """优化OCR处理流程"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        results = ocr_engine.ocr(gray, det=False, cls=False)
        return ''.join(line[0] for page in results for line in page)


class PrintRedirector:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, message):
        self.text_widget.insert(tk.END, message)
        self.text_widget.see(tk.END)

    def flush(self):
        pass


if __name__ == '__main__':
    root = tk.Tk()
    root.title("服务器日志")
    root.geometry("800x600")

    text_area = scrolledtext.ScrolledText(root, width=80, height=30)
    # text_area.pack(padx=10, pady=10)
    text_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)  # 文本框会填充整个窗口剩余空间
    sys.stdout = PrintRedirector(text_area)

    server = ThreadedServer()
    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True
    server_thread.start()


    def on_closing():
        server.running = False
        root.destroy()


    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
