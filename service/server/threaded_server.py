import json
import struct
import socket
import threading
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor
import cv2
import numpy as np
from .yolo_handler import YoloHandler
from .ocr_handler import OCRHandler
from .config_manager import settings  # 新增：集中配置
from .logger import get_logger
import time
from collections import defaultdict, deque

# 获取日志记录器
logger = get_logger('threaded_server')

# 安全限制常量
MAX_IMAGE_SIZE = 50 * 1024 * 1024  # 50MB，防止内存溢出攻击
MAX_HEADER_SIZE = 1024 * 1024  # 1MB，JSON头部最大大小
MAX_CONNECTIONS = 100  # 最大并发连接数
VALID_REQUEST_TYPES = {"game_windows", "min_map", "ocr"}  # 有效的请求类型


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
            dummy = (
                np.zeros((640, 640, 3), dtype=np.uint8)
                if settings.model_warmup
                else None
            )
            try:
                self._shared_yolo = YoloHandler(warmup_image=dummy)
            except Exception as e:
                logger.error(f"共享 YOLO 初始化失败: {e}", exc_info=True)
            try:
                self._shared_ocr = OCRHandler(debug=False)
            except Exception as e:
                logger.error(f"共享 OCR 初始化失败: {e}", exc_info=True)
            logger.info("共享模型初始化完成")
        self._metrics_thread = None
        self._stats_lock = threading.Lock()
        self._req_count = 0
        self._err_count = 0
        self._req_count_by_type = defaultdict(int)
        self._latencies_by_type: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=200)
        )
        self._start_time = time.time()
        self._report_interval = 10  # 秒
        # 连接数限制
        self._active_connections = 0
        self._connections_lock = threading.Lock()

    def start(self):
        """启动服务器"""
        self.running = True
        logger.info(
            f"以 {'独立' if settings.per_thread_models else '共享'} 模型模式启动，线程数: {settings.max_workers}"
        )
        try:
            with ThreadPoolExecutor(max_workers=settings.max_workers) as executor:
                self._executor = executor
                for _ in range(settings.max_workers):
                    executor.submit(self._worker)
                listener_thread = threading.Thread(
                    target=self._listen, name="Listener", daemon=True
                )
                listener_thread.start()
                self._metrics_thread = threading.Thread(
                    target=self._metrics_loop, name="Metrics", daemon=True
                )
                self._metrics_thread.start()
                logger.info(
                    f"服务器已启动在 {self.server_address[0]}:{self.server_address[1]}"
                )
                # 主循环等待停止信号而不是直接 join (允许 stop 更快退出)
                while self.running and not self._stop_event.is_set():
                    time.sleep(0.2)
        except KeyboardInterrupt:
            logger.warning("收到中断信号，正在关闭...")
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
        logger.info("停止信号已发送")

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
                    
                    # 检查连接数限制
                    with self._connections_lock:
                        if self._active_connections >= MAX_CONNECTIONS:
                            logger.warning(f"连接数已达上限 ({MAX_CONNECTIONS})，拒绝新连接: {addr}")
                            conn.close()
                            continue
                        self._active_connections += 1
                    
                    self.task_queue.put((conn, addr))
                except OSError:
                    # 监听 socket 关闭（正常情况，服务器正在关闭）
                    logger.debug("监听 socket 已关闭")
                    break
                except socket.error as e:
                    logger.error(f"监听线程网络错误: {e}", exc_info=True)
                except Exception as e:
                    logger.error(f"监听线程异常: {e}", exc_info=True)
            logger.debug("监听线程结束")

    def _worker(self):
        """处理客户端请求"""
        # 根据模式创建或使用共享模型
        yolo_handler = None
        ocr_handler = None
        if settings.per_thread_models:
            dummy_image = (
                np.zeros((640, 640, 3), dtype=np.uint8)
                if settings.model_warmup
                else None
            )
            try:
                yolo_handler = YoloHandler(warmup_image=dummy_image)
            except Exception as e:
                logger.error(f"线程 {threading.current_thread().name} 初始化 YOLO 失败: {e}", exc_info=True)
            try:
                ocr_handler = OCRHandler(debug=False)
            except Exception as e:
                logger.error(f"线程 {threading.current_thread().name} 初始化 OCR 失败: {e}", exc_info=True)
            logger.debug(f"线程 {threading.current_thread().name} 的模型预热完成")
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
                logger.error(f"工作线程异常: {e}", exc_info=True)
        logger.debug(f"线程 {threading.current_thread().name} 退出")

    def _handle_client(self, conn, addr, yolo_handler, ocr_handler):
        """处理单个客户端请求"""
        try:
            with conn:
                logger.info(f"新连接: {addr}")
                try:
                    while self.running:
                    header, image = self._receive_message(conn)
                    if not header:
                        break

                    req_type = header.get("type")
                    if not req_type:
                        result = {"error": "请求类型缺失"}
                        self._record_metric("unknown", 0.0, False, True)
                        self._send_response(conn, result, "unknown")
                        continue
                    
                    # 验证请求类型有效性
                    if req_type not in VALID_REQUEST_TYPES:
                        logger.warning(f"无效的请求类型: {req_type}")
                        result = {"error": f"无效的请求类型: {req_type}，有效类型: {', '.join(VALID_REQUEST_TYPES)}"}
                        self._record_metric(req_type, 0.0, False, True)
                        self._send_response(conn, result, req_type)
                        continue
                    
                    # 检查是否有错误信息（如图像大小超限）
                    if isinstance(header, dict) and "_size_exceeded" in header:
                        result = {"error": header.get("_error", "图像大小超过限制")}
                        self._record_metric(req_type, 0.0, False, True)
                        self._send_response(conn, result, req_type)
                        continue

                    start_ts = time.perf_counter()
                    try:
                        logger.debug(f"收到请求类型: {req_type}，图像尺寸: {image.shape if image is not None else '无'}")

                        if req_type == "game_windows":
                            if yolo_handler is None:
                                result = {"error": "YOLO 未初始化"}
                                self._record_metric(
                                    req_type or "unknown", 0.0, False, True
                                )
                            else:
                                # 共享模型模式下需要加锁保护
                                if not settings.per_thread_models:
                                    with self._model_lock:
                                        result = yolo_handler.process(image)
                                else:
                                    result = yolo_handler.process(image)
                                self._record_metric(
                                    req_type,
                                    time.perf_counter() - start_ts,
                                    True,
                                    False,
                                )
                        elif req_type == "min_map":
                            if yolo_handler is None:
                                result = {"error": "YOLO 未初始化"}
                                self._record_metric(
                                    req_type or "unknown", 0.0, False, True
                                )
                            else:
                                # 共享模型模式下需要加锁保护
                                if not settings.per_thread_models:
                                    with self._model_lock:
                                        result = yolo_handler.process_minimap(image)
                                else:
                                    result = yolo_handler.process_minimap(image)
                                self._record_metric(
                                    req_type,
                                    time.perf_counter() - start_ts,
                                    True,
                                    False,
                                )
                        elif req_type == "ocr":
                            if ocr_handler is None:
                                result = {"error": "OCR 未初始化"}
                                self._record_metric(
                                    req_type or "unknown", 0.0, False, True
                                )
                            else:
                                # 共享模型模式下需要加锁保护
                                if not settings.per_thread_models:
                                    with self._model_lock:
                                        result = ocr_handler.process(image)
                                else:
                                    result = ocr_handler.process(image)
                                self._record_metric(
                                    req_type,
                                    time.perf_counter() - start_ts,
                                    True,
                                    False,
                                )

                                if result:
                                    logger.debug(f"识别结果：{result}")
                                else:
                                    cv2.imwrite(f"revice.png",image)
                                    logger.warning(f"OCR 识别结果为空，已保存图像到 revice.png")
                        else:
                            result = {"error": f"无效的请求类型: {req_type}"}
                            self._record_metric(req_type, 0.0, False, True)
                    except ValueError as e:
                        logger.error(f"参数错误: {e}", exc_info=True)
                        result = {"error": f"参数错误: {e}"}
                        self._record_metric(req_type, 0.0, False, True)
                    except RuntimeError as e:
                        logger.error(f"模型推理错误: {e}", exc_info=True)
                        result = {"error": f"模型推理错误: {e}"}
                        self._record_metric(req_type, 0.0, False, True)
                    except AttributeError as e:
                        logger.error(f"对象属性错误: {e}", exc_info=True)
                        result = {"error": f"内部错误: {e}"}
                        self._record_metric(req_type, 0.0, False, True)
                    except Exception as e:
                        logger.error(f"处理请求时发生未预期错误: {e}", exc_info=True)
                        result = {"error": f"处理异常: {e}"}
                        self._record_metric(req_type, 0.0, False, True)

                    self._send_response(conn, result, req_type)
                finally:
                    # 减少活跃连接数
                    with self._connections_lock:
                        self._active_connections = max(0, self._active_connections - 1)
        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError) as e:
            logger.debug(f"客户端 {addr} 连接已断开: {e}")
            # 减少活跃连接数
            with self._connections_lock:
                self._active_connections = max(0, self._active_connections - 1)
        except socket.error as e:
            logger.error(f"客户端 {addr} 网络错误: {e}", exc_info=True)
            # 减少活跃连接数
            with self._connections_lock:
                self._active_connections = max(0, self._active_connections - 1)
        except Exception as e:
            logger.error(f"客户端 {addr} 处理异常: {e}", exc_info=True)
            # 减少活跃连接数
            with self._connections_lock:
                self._active_connections = max(0, self._active_connections - 1)

    def _receive_message(self, conn):
        """接收客户端消息"""
        try:
            # 接收头部长度
            header_len = conn.recv(4)
            if len(header_len) < 4:
                return None, None

            # 解析头部大小
            try:
                header_size = struct.unpack("!I", header_len)[0]
            except struct.error as e:
                logger.warning(f"解析头部长度失败: {e}")
                return None, None

            # 验证头部大小
            if header_size > MAX_HEADER_SIZE:
                logger.warning(f"头部大小超过限制: {header_size} > {MAX_HEADER_SIZE}")
                return None, None
            if header_size == 0:
                logger.warning("头部大小为0")
                return None, None

            # 接收头部数据
            header_data = b""
            while len(header_data) < header_size:
                chunk = conn.recv(header_size - len(header_data))
                if not chunk:
                    logger.warning("接收头部数据不完整，连接可能已断开")
                    return None, None
                header_data += chunk

            # 解析 JSON 头部
            try:
                header = json.loads(header_data.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                logger.error(f"解析 JSON 头部失败: {e}", exc_info=True)
                return None, None

            # 接收图像数据
            image_size = header.get("image_size", 0)
            if image_size <= 0:
                logger.warning(f"无效的图像大小: {image_size}")
                return header, None
            
            # 验证图像大小限制（防止内存溢出攻击）
            if image_size > MAX_IMAGE_SIZE:
                logger.warning(f"图像大小超过限制: {image_size / 1024 / 1024:.2f}MB > {MAX_IMAGE_SIZE / 1024 / 1024:.2f}MB")
                # 返回特殊标记，让调用者知道这是大小超限错误
                header["_size_exceeded"] = True
                header["_error"] = f"图像大小超过限制（最大 {MAX_IMAGE_SIZE / 1024 / 1024:.0f}MB）"
                return header, None

            received = 0
            chunks = []
            while received < image_size:
                try:
                    chunk = conn.recv(min(4096, image_size - received))
                    if not chunk:
                        logger.warning(f"接收图像数据不完整: {received}/{image_size}")
                        break
                    chunks.append(chunk)
                    received += len(chunk)
                except socket.timeout:
                    logger.warning("接收图像数据超时")
                    break

            # 解码图像
            image = None
            if chunks and received == image_size:
                try:
                    image = cv2.imdecode(
                        np.frombuffer(b"".join(chunks), dtype=np.uint8), cv2.IMREAD_COLOR
                    )
                    if image is None:
                        logger.warning("图像解码失败，数据可能已损坏")
                except Exception as e:
                    logger.error(f"图像解码异常: {e}", exc_info=True)
            elif chunks:
                logger.warning(f"图像数据不完整: 接收 {received}/{image_size} 字节")

            return header, image

        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError) as e:
            logger.debug(f"客户端连接已断开: {e}")
            return None, None
        except socket.timeout:
            logger.warning("接收消息超时")
            return None, None
        except socket.error as e:
            logger.error(f"网络错误: {e}", exc_info=True)
            return None, None
        except ValueError as e:
            logger.error(f"数据格式错误: {e}", exc_info=True)
            return None, None
        except Exception as e:
            logger.error(f"接收消息时发生未预期错误: {e}", exc_info=True)
            return None, None

    def _send_response(self, conn, data, msg_type):
        """发送响应给客户端"""
        try:
            json_data = json.dumps(data).encode("utf-8")
            header = json.dumps({
                                "type": msg_type, 
                                 "data_size": len(json_data)
                                 }).encode("utf-8")
            
            conn.sendall(struct.pack("!I", len(header)))
            conn.sendall(header)
            conn.sendall(json_data)
        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError) as e:
            logger.debug(f"客户端连接已中断: {e}")
        except socket.timeout:
            logger.warning("发送响应超时")
        except socket.error as e:
            logger.error(f"发送响应时网络错误: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"发送响应时发生未预期错误: {e}", exc_info=True)

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
                        p95 = (
                            lat_list[int(len(lat_list) * 0.95) - 1]
                            if len(lat_list) >= 20
                            else lat_list[-1]
                        )
                        lines.append(
                            f"  - {t}: {self._req_count_by_type[t]} 次 | 平均 {avg*1000:.1f}ms | P95 {p95*1000:.1f}ms | 最近样本 {len(lat_list)}"
                        )
                logger.info("\n".join(lines))

    def _record_metric(
        self, req_type: str, duration: float, success: bool, error: bool
    ):
        with self._stats_lock:
            self._req_count += 1
            self._req_count_by_type[req_type] += 1
            if error:
                self._err_count += 1
            else:
                self._latencies_by_type[req_type].append(duration)
