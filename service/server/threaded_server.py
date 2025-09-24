import json
import struct
import socket
import logging
import threading
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor
import cv2
import numpy as np
from .yolo_handler import YoloHandler
from .ocr_handler import OCRHandler
from .config_manager import settings  # 新增：集中配置
import time
from collections import defaultdict, deque

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class ThreadedServer:
    """多线程图像处理服务器"""

    def __init__(self, host=None, port=None):
        self.server_address = (host or settings.host, port or settings.port)
        self.task_queue = Queue(maxsize=settings.task_queue_size)
        self.running = False
        self._listen_sock = None
        self._executor = None
        self._stop_event = threading.Event()
        # 共享模型模式（当 per_thread_models 为 False）
        self._shared_yolo = None
        self._shared_ocr = None
        self._model_lock = threading.Lock()
        if not settings.per_thread_models:
            # 提前加载共享模型
            dummy = np.zeros((640, 640, 3), dtype=np.uint8) if settings.model_warmup else None
            try:
                self._shared_yolo = YoloHandler(warmup_image=dummy)
            except Exception as e:
                print(f"共享 YOLO 初始化失败: {e}")
            try:
                self._shared_ocr = OCRHandler(debug=False)
            except Exception as e:
                print(f"共享 OCR 初始化失败: {e}")
            print("共享模型初始化完成")
        self._metrics_thread = None
        self._stats_lock = threading.Lock()
        self._req_count = 0
        self._err_count = 0
        self._req_count_by_type = defaultdict(int)
        self._latencies_by_type: dict[str, deque] = defaultdict(lambda: deque(maxlen=200))
        self._start_time = time.time()
        self._report_interval = 10  # 秒

    def start(self):
        """启动服务器"""
        self.running = True
        print(f"以 {'独立' if settings.per_thread_models else '共享'} 模型模式启动，线程数: {settings.max_workers}")
        try:
            with ThreadPoolExecutor(max_workers=settings.max_workers) as executor:
                self._executor = executor
                for _ in range(settings.max_workers):
                    executor.submit(self._worker)
                listener_thread = threading.Thread(target=self._listen, name="Listener", daemon=True)
                listener_thread.start()
                self._metrics_thread = threading.Thread(target=self._metrics_loop, name="Metrics", daemon=True)
                self._metrics_thread.start()
                print(f"服务器已启动在 {self.server_address[0]}:{self.server_address[1]}")
                # 主循环等待停止信号而不是直接 join (允许 stop 更快退出)
                while self.running and not self._stop_event.is_set():
                    time.sleep(0.2)
        except KeyboardInterrupt:
            print("收到中断信号，正在关闭...")
            self.stop()
        finally:
            self.running = False

    def stop(self):
        # 外部调用优雅关闭
        if not self.running and self._stop_event.is_set():
            return
        self.running = False
        self._stop_event.set()
        # 关闭监听 socket 以打断 accept
        if self._listen_sock:
            try:
                self._listen_sock.close()
            except Exception:
                pass
        # 向队列投递哨兵，唤醒阻塞的 worker
        for _ in range(settings.max_workers * 2):  # 多投递几次确保唤醒
            try:
                self.task_queue.put_nowait((None, None))
            except Exception:
                break
        # 尝试非阻塞关闭线程池
        if self._executor:
            try:
                self._executor.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass
        print("停止信号已发送")

    def _listen(self):
        """监听客户端连接"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            self._listen_sock = sock
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(self.server_address)
            sock.listen(10)
            while self.running:
                try:
                    conn, addr = sock.accept()
                    if not self.running:
                        conn.close()
                        break
                    self.task_queue.put((conn, addr))
                except OSError:
                    # 监听 socket 关闭
                    break
                except Exception as e:
                    print(f"监听线程异常: {e}")
            print("监听线程结束")

    def _worker(self):
        """处理客户端请求"""
        # 根据模式创建或使用共享模型
        yolo_handler = None
        ocr_handler = None
        if settings.per_thread_models:
            dummy_image = np.zeros((640, 640, 3), dtype=np.uint8) if settings.model_warmup else None
            try:
                yolo_handler = YoloHandler(warmup_image=dummy_image)
            except Exception as e:
                print(f"线程 {threading.current_thread().name} 初始化 YOLO 失败: {e}")
            try:
                ocr_handler = OCRHandler(debug=False)
            except Exception as e:
                print(f"线程 {threading.current_thread().name} 初始化 OCR 失败: {e}")
            print(f"线程 {threading.current_thread().name} 的模型预热完成")
        else:
            # 共享模型直接引用
            yolo_handler = self._shared_yolo
            ocr_handler = self._shared_ocr

        while self.running and not self._stop_event.is_set():
            try:
                item = self.task_queue.get(timeout=0.5)
            except Empty:
                continue
            if not item or item == (None, None) or not self.running:
                break
            conn, addr = item
            try:
                self._handle_client(conn, addr, yolo_handler, ocr_handler)
            except Exception as e:
                print(f"工作线程异常: {e}")
        print(f"线程 {threading.current_thread().name} 退出")

    def _handle_client(self, conn, addr, yolo_handler, ocr_handler):
        """处理单个客户端请求"""
        try:
            with conn:
                print(f"新连接: {addr}")
                while self.running:
                    header, image = self._receive_message(conn)
                    if not header:
                        break

                    req_type = header.get("type")
                    start_ts = time.perf_counter()
                    try:
                        if req_type == "game_windows":
                            if yolo_handler is None:
                                result = {"error": "YOLO 未初始化"}
                                self._record_metric(req_type or 'unknown', 0.0, False, True)
                            else:
                                result = yolo_handler.process(image)
                                self._record_metric(req_type, time.perf_counter()-start_ts, True, False)
                        elif req_type == "ocr":
                            if ocr_handler is None:
                                result = {"error": "OCR 未初始化"}
                                self._record_metric(req_type or 'unknown', 0.0, False, True)
                            else:
                                result = ocr_handler.process(image)
                                self._record_metric(req_type, time.perf_counter()-start_ts, True, False)
                        else:
                            result = {"error": "无效的请求类型"}
                            self._record_metric(req_type or 'unknown', 0.0, False, True)
                    except Exception as e:
                        result = {"error": f"处理异常: {e}"}
                        self._record_metric(req_type or 'unknown', 0.0, False, True)

                    self._send_response(conn, result, req_type)
        except Exception as e:
            print(f"客户端 {addr} 处理异常: {e}")

    def _receive_message(self, conn):
        """接收客户端消息"""
        try:
            header_len = conn.recv(4)
            if len(header_len) < 4:
                return None, None

            header_size = struct.unpack("!I", header_len)[0]
            header_data = conn.recv(header_size)
            header = json.loads(header_data.decode("utf-8"))

            image_size = header.get("image_size", 0)
            received = 0
            chunks = []
            while received < image_size:
                chunk = conn.recv(min(4096, image_size - received))
                if not chunk:
                    break
                chunks.append(chunk)
                received += len(chunk)

            image = None
            if chunks:
                image = cv2.imdecode(np.frombuffer(b"".join(chunks), dtype=np.uint8), cv2.IMREAD_COLOR)
            return header, image
        except Exception as e:
            print(f"接收消息失败: {e}")
            return None, None

    def _send_response(self, conn, data, msg_type):
        """发送响应给客户端"""
        try:
            json_data = json.dumps(data, ensure_ascii=False).encode("utf-8")
            header = json.dumps({"type": msg_type, "data_size": len(json_data)}, ensure_ascii=False).encode("utf-8")
            conn.sendall(struct.pack("!I", len(header)))
            conn.sendall(header)
            conn.sendall(json_data)
        except BrokenPipeError:
            print("客户端连接已中断")

    def _metrics_loop(self):
        while self.running and not self._stop_event.is_set():
            time.sleep(self._report_interval)
            if not self.running or self._stop_event.is_set():
                break
            with self._stats_lock:
                uptime = time.time() - self._start_time
                lines = [
                    f"[统计] 运行 {uptime:.1f}s | 总请求 {self._req_count} | 错误 {self._err_count} | 队列 {self.task_queue.qsize()}/{self.task_queue.maxsize}",
                ]
                for t, lat_q in self._latencies_by_type.items():
                    if lat_q:
                        lat_list = list(lat_q)
                        lat_list.sort()
                        avg = sum(lat_list) / len(lat_list)
                        p95 = lat_list[int(len(lat_list)*0.95)-1] if len(lat_list) >= 20 else lat_list[-1]
                        lines.append(f"  - {t}: {self._req_count_by_type[t]} 次 | 平均 {avg*1000:.1f}ms | P95 {p95*1000:.1f}ms | 最近样本 {len(lat_list)}")
                print("\n".join(lines))

    def _record_metric(self, req_type: str, duration: float, success: bool, error: bool):
        with self._stats_lock:
            self._req_count += 1
            self._req_count_by_type[req_type] += 1
            if error:
                self._err_count += 1
            else:
                self._latencies_by_type[req_type].append(duration)