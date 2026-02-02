import json
import struct
import socket
import threading
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from typing import Optional, Tuple, Dict, Any
import cv2
import numpy as np
from .yolo_handler import YoloHandler
from .ocr_handler import OCRHandler
from .config_manager import settings
from .logger import get_logger
from .constants import (
    MAX_IMAGE_SIZE,
    MAX_HEADER_SIZE,
    MAX_CONNECTIONS,
    SOCKET_CHUNK_SIZE,
    METRICS_REPORT_INTERVAL,
    METRICS_P95_MIN_SAMPLES,
    METRICS_P95_PERCENTILE,
    METRICS_MAX_SAMPLES,
    MAIN_LOOP_SLEEP,
)
from .protocol import (
    VALID_REQUEST_TYPES,
    REQUEST_TYPE_GAME_WINDOWS,
    REQUEST_TYPE_MIN_MAP,
    REQUEST_TYPE_OCR,
    HEADER_FIELD_TYPE,
    HEADER_FIELD_IMAGE_SIZE,
    RESPONSE_FIELD_TYPE,
    RESPONSE_FIELD_DATA_SIZE,
    ERROR_FIELD_ERROR,
    ERROR_FIELD_SIZE_EXCEEDED,
    ERROR_FIELD_ERROR_MSG,
)
import time
from collections import defaultdict, deque

# 获取日志记录器
logger = get_logger('threaded_server')


class ThreadedServer:
    """多线程图像处理服务器"""

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None) -> None:
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
            yolo_init_success = False
            ocr_init_success = False
            
            try:
                self._shared_yolo = YoloHandler(warmup_image=dummy)
                if self._shared_yolo._model_loaded:
                    yolo_init_success = True
                    logger.info("共享 YOLO 模型初始化成功")
                else:
                    logger.error("共享 YOLO 模型初始化失败：模型未加载")
                    self._shared_yolo = None
            except FileNotFoundError as e:
                logger.error(f"共享 YOLO 初始化失败：模型文件未找到: {e}", exc_info=True)
                self._shared_yolo = None
            except Exception as e:
                logger.error(f"共享 YOLO 初始化失败: {e}", exc_info=True)
                self._shared_yolo = None
            
            try:
                self._shared_ocr = OCRHandler(debug=False)
                ocr_init_success = True
                logger.info("共享 OCR 模型初始化成功")
            except FileNotFoundError as e:
                logger.error(f"共享 OCR 初始化失败：模型文件未找到: {e}", exc_info=True)
                self._shared_ocr = None
            except Exception as e:
                logger.error(f"共享 OCR 初始化失败: {e}", exc_info=True)
                self._shared_ocr = None
            
            if yolo_init_success and ocr_init_success:
                logger.info("共享模型初始化完成")
            else:
                failed_models = []
                if not yolo_init_success:
                    failed_models.append("YOLO")
                if not ocr_init_success:
                    failed_models.append("OCR")
                logger.warning(f"共享模型初始化部分失败: {', '.join(failed_models)}。服务器将继续运行，但相关功能可能不可用。")
        self._metrics_thread = None
        self._stats_lock = threading.Lock()
        self._req_count = 0
        self._err_count = 0
        self._req_count_by_type = defaultdict(int)
        self._latencies_by_type: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=METRICS_MAX_SAMPLES)
        )
        self._start_time = time.time()
        self._report_interval = METRICS_REPORT_INTERVAL  # 秒
        self._shutdown_timeout = 10  # 线程池关闭超时（秒）

    def start(self) -> None:
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
                    time.sleep(MAIN_LOOP_SLEEP)
        except KeyboardInterrupt:
            logger.info("收到中断信号，正在关闭...")
            self.stop()
        finally:
            self.running = False

    def reload_config(self) -> Tuple[bool, Optional[str]]:
        """重新加载配置文件
        
        Returns:
            Tuple[bool, Optional[str]]: (是否成功, 错误消息)
        """
        from .config_manager import reload_config
        
        success, error_msg, new_settings = reload_config()
        if not success:
            return False, error_msg
        
        # 注意：某些配置项（如 max_workers, per_thread_models）在运行时无法安全更改
        # 这里只更新可以安全更改的配置项
        logger.info("配置重载成功，部分配置项需要重启服务器才能生效")
        logger.info(f"新配置: max_workers={new_settings.max_workers}, task_queue_size={new_settings.task_queue_size}")
        
        # 可以安全更新的配置项（如果有的话）
        # 例如：可以更新报告间隔等
        
        return True, None

    def stop(self) -> None:
        # 外部调用优雅关闭
        if not self.running and self._stop_event.is_set():
            return
        self.running = False
        self._stop_event.set()
        # 关闭监听 socket 以打断 accept
        if self._listen_sock:
            try:
                self._listen_sock.close()
            except (OSError, socket.error) as e:
                logger.debug(f"关闭监听 socket 时出现异常: {e}")
            finally:
                self._listen_sock = None
        # 向队列投递哨兵，唤醒阻塞的 worker
        for _ in range(settings.max_workers * 2):  # 多投递几次确保唤醒
            try:
                self.task_queue.put_nowait((None, None))
            except Exception:
                break
        # 优雅关闭线程池，等待任务完成
        if self._executor:
            try:
                # 先尝试优雅关闭，等待任务完成
                self._executor.shutdown(wait=True, timeout=self._shutdown_timeout)
                logger.info("线程池已优雅关闭，所有任务已完成")
            except TimeoutError:
                logger.warning(f"线程池关闭超时（{self._shutdown_timeout}秒），强制关闭")
                # 超时后强制关闭
                try:
                    self._executor.shutdown(wait=False, cancel_futures=True)
                except Exception as e:
                    logger.error(f"强制关闭线程池时出现异常: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"关闭线程池时出现异常: {e}", exc_info=True)
                # 尝试强制关闭
                try:
                    self._executor.shutdown(wait=False, cancel_futures=True)
                except Exception:
                    pass
        logger.info("停止信号已发送")

    def _listen(self) -> None:
        """监听客户端连接"""
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._listen_sock = sock
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(self.server_address)
            sock.listen(MAX_CONNECTIONS)
            logger.info(f"服务器已启动在 {self.server_address[0]}:{self.server_address[1]}，最大连接数: {MAX_CONNECTIONS}")
            while self.running:
                try:
                    # 检查活跃连接数
                    with self._connections_lock:
                        if self._active_connections >= MAX_CONNECTIONS:
                            logger.warning(f"达到最大连接数 {MAX_CONNECTIONS}，拒绝新连接。")
                            # 尝试接受并立即关闭以清除积压
                            try:
                                conn, addr = sock.accept()
                                conn.close()
                            except (OSError, socket.error):
                                pass  # Socket 可能已关闭
                            continue

                    conn, addr = sock.accept()
                    if not self.running:
                        try:
                            conn.close()
                        except (OSError, socket.error):
                            pass
                        break
                    with self._connections_lock:
                        self._active_connections += 1
                    self.task_queue.put((conn, addr))
                    logger.debug(f"新连接 {addr} 已接受，当前活跃连接数: {self._active_connections}")
                except OSError:
                    # 监听 socket 关闭
                    logger.debug("监听 socket 已关闭")
                    break
                except socket.error as e:
                    if self.running:
                        logger.error(f"监听线程网络错误: {e}", exc_info=True)
                    break
                except Exception as e:
                    logger.error(f"监听线程异常: {e}", exc_info=True)
        finally:
            # 确保 socket 正确关闭
            if sock:
                try:
                    sock.close()
                except (OSError, socket.error) as e:
                    logger.debug(f"关闭监听 socket 时出现异常: {e}")
            self._listen_sock = None
            logger.debug("监听线程结束")

    def _worker(self) -> None:
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
                if not yolo_handler._model_loaded:
                    logger.error(f"线程 {threading.current_thread().name} YOLO 模型未加载，线程将退出")
                    return  # 独立模式下模型加载失败，终止线程
            except FileNotFoundError as e:
                logger.error(f"线程 {threading.current_thread().name} YOLO 模型文件未找到: {e}，线程将退出", exc_info=True)
                return  # 独立模式下模型文件缺失，终止线程
            except Exception as e:
                logger.error(f"线程 {threading.current_thread().name} 初始化 YOLO 失败: {e}，线程将退出", exc_info=True)
                return  # 独立模式下初始化失败，终止线程
            
            try:
                ocr_handler = OCRHandler(debug=False)
            except FileNotFoundError as e:
                logger.error(f"线程 {threading.current_thread().name} OCR 模型文件未找到: {e}，线程将退出", exc_info=True)
                return  # 独立模式下模型文件缺失，终止线程
            except Exception as e:
                logger.error(f"线程 {threading.current_thread().name} 初始化 OCR 失败: {e}，线程将退出", exc_info=True)
                return  # 独立模式下初始化失败，终止线程
            
            logger.debug(f"线程 {threading.current_thread().name} 的模型预热完成")
        else:
            # 共享模型直接引用（可能为 None，如果初始化失败）
            yolo_handler = self._shared_yolo
            ocr_handler = self._shared_ocr
            if yolo_handler is None or ocr_handler is None:
                logger.warning(f"线程 {threading.current_thread().name} 使用共享模型，但部分模型未初始化")

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

    def _handle_client(
        self,
        conn: socket.socket,
        addr: Tuple[str, int],
        yolo_handler: Optional[YoloHandler],
        ocr_handler: Optional[OCRHandler],
    ) -> None:
        """处理单个客户端请求"""
        try:
            logger.info(f"新连接: {addr}")
            try:
                while self.running:
                    header, image = self._receive_message(conn)
                    if not header:
                        break

                    req_type = header.get(HEADER_FIELD_TYPE)
                    start_ts = time.perf_counter()
                    try:
                        logger.debug(f"收到请求类型: {req_type}，图像尺寸: {image.shape if image is not None else '无'}")

                        if req_type == REQUEST_TYPE_GAME_WINDOWS:
                            if yolo_handler is None or (hasattr(yolo_handler, '_model_loaded') and not yolo_handler._model_loaded):
                                result = {ERROR_FIELD_ERROR: "YOLO 未初始化或模型加载失败"}
                                logger.warning(f"客户端 {addr} 请求 YOLO 处理，但模型未初始化")
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
                        elif req_type == REQUEST_TYPE_MIN_MAP:
                            if yolo_handler is None or (hasattr(yolo_handler, '_model_loaded') and not yolo_handler._model_loaded):
                                result = {ERROR_FIELD_ERROR: "YOLO 未初始化或模型加载失败"}
                                logger.warning(f"客户端 {addr} 请求 YOLO 小地图处理，但模型未初始化")
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
                        elif req_type == REQUEST_TYPE_OCR:
                            if ocr_handler is None:
                                result = {ERROR_FIELD_ERROR: "OCR 未初始化或模型加载失败"}
                                logger.warning(f"客户端 {addr} 请求 OCR 处理，但模型未初始化")
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
                                    cv2.imwrite(f"revice.png", image)
                                    logger.warning(f"OCR 识别结果为空，已保存图像到 revice.png")
                        else:
                            result = {ERROR_FIELD_ERROR: "无效的请求类型"}
                            self._record_metric(req_type or "unknown", 0.0, False, True)
                    except ValueError as e:
                        logger.error(f"参数错误: {e}", exc_info=True)
                        result = {ERROR_FIELD_ERROR: f"参数错误: {e}"}
                        self._record_metric(req_type or "unknown", 0.0, False, True)
                    except RuntimeError as e:
                        logger.error(f"模型推理错误: {e}", exc_info=True)
                        result = {ERROR_FIELD_ERROR: f"模型推理错误: {e}"}
                        self._record_metric(req_type or "unknown", 0.0, False, True)
                    except AttributeError as e:
                        logger.error(f"对象属性错误: {e}", exc_info=True)
                        result = {ERROR_FIELD_ERROR: f"内部错误: {e}"}
                        self._record_metric(req_type or "unknown", 0.0, False, True)
                    except Exception as e:
                        logger.error(f"处理请求时发生未预期错误: {e}", exc_info=True)
                        result = {ERROR_FIELD_ERROR: f"处理异常: {e}"}
                        self._record_metric(req_type or "unknown", 0.0, False, True)

                    self._send_response(conn, result, req_type)
            finally:
                # 确保 socket 正确关闭
                try:
                    conn.close()
                except (OSError, socket.error) as e:
                    logger.debug(f"关闭客户端连接 {addr} 时出现异常: {e}")
        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError) as e:
            logger.debug(f"客户端 {addr} 连接已断开: {e}")
            try:
                conn.close()
            except (OSError, socket.error):
                pass
            with self._connections_lock:
                self._active_connections = max(0, self._active_connections - 1)
        except socket.error as e:
            logger.error(f"客户端 {addr} 网络错误: {e}", exc_info=True)
            try:
                conn.close()
            except (OSError, socket.error):
                pass
            with self._connections_lock:
                self._active_connections = max(0, self._active_connections - 1)
        except Exception as e:
            logger.error(f"客户端 {addr} 处理异常: {e}", exc_info=True)
            try:
                conn.close()
            except (OSError, socket.error):
                pass
            with self._connections_lock:
                self._active_connections = max(0, self._active_connections - 1)
        finally:
            # 确保连接数被减少
            with self._connections_lock:
                self._active_connections = max(0, self._active_connections - 1)
            logger.debug(f"客户端 {addr} 连接处理结束，当前活跃连接数: {self._active_connections}")

    def _receive_message(self, conn: socket.socket) -> Tuple[Optional[Dict[str, Any]], Optional[np.ndarray]]:
        """接收客户端消息"""
        try:
            header_len = conn.recv(4)
            if len(header_len) < 4:
                logger.debug("接收头部长度不足4字节，连接可能已关闭")
                return None, None

            try:
                header_size = struct.unpack("!I", header_len)[0]
            except struct.error as e:
                logger.warning(f"解析头部长度失败: {e}")
                return None, None

            if not (0 < header_size <= MAX_HEADER_SIZE):
                logger.warning(f"无效或过大的头部大小: {header_size} 字节 (限制: {MAX_HEADER_SIZE} 字节)")
                return None, None

            header_data = b""
            while len(header_data) < header_size:
                chunk = conn.recv(header_size - len(header_data))
                if not chunk:
                    logger.warning("接收头部数据不完整，连接可能已断开")
                    return None, None
                header_data += chunk

            try:
                header = json.loads(header_data.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                logger.error(f"解析 JSON 头部失败: {e}", exc_info=True)
                return None, None

            image_size = header.get(HEADER_FIELD_IMAGE_SIZE, 0)
            if not (0 < image_size <= MAX_IMAGE_SIZE):
                logger.warning(f"无效或过大的图像大小: {image_size} 字节 (限制: {MAX_IMAGE_SIZE} 字节)")
                header[ERROR_FIELD_SIZE_EXCEEDED] = True
                header[ERROR_FIELD_ERROR_MSG] = f"图像大小超过限制（最大 {MAX_IMAGE_SIZE / 1024 / 1024:.0f}MB）"
                return header, None
            
            # 使用 BytesIO 优化内存使用，避免多次内存分配
            image_buffer = BytesIO()
            received = 0
            chunk_size = min(SOCKET_CHUNK_SIZE, image_size)  # 使用更大的块大小提高效率
            
            while received < image_size:
                try:
                    remaining = image_size - received
                    chunk = conn.recv(min(chunk_size, remaining))
                    if not chunk:
                        logger.warning(f"接收图像数据不完整: 接收 {received}/{image_size} 字节，连接可能已断开")
                        break
                    image_buffer.write(chunk)
                    received += len(chunk)
                except socket.timeout:
                    logger.warning("接收图像数据超时")
                    break
                except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError) as e:
                    logger.warning(f"接收图像数据时连接中断: {e}")
                    break

            image = None
            if received == image_size:
                try:
                    # 从 BytesIO 获取字节数据并解码
                    image_data = image_buffer.getvalue()
                    image = cv2.imdecode(
                        np.frombuffer(image_data, dtype=np.uint8), cv2.IMREAD_COLOR
                    )
                    if image is None:
                        logger.warning("cv2.imdecode 无法解码图像数据")
                except cv2.error as e:
                    logger.error(f"图像解码失败: {e}", exc_info=True)
                except Exception as e:
                    logger.error(f"图像处理异常: {e}", exc_info=True)
                finally:
                    # 清理缓冲区
                    image_buffer.close()
            elif received != image_size:
                logger.warning(f"图像数据不完整: 接收 {received}/{image_size} 字节")
                image_buffer.close()

            return header, image
        except socket.timeout:
            logger.warning("接收消息超时")
            return None, None
        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError) as e:
            logger.debug(f"接收消息时客户端连接已断开: {e}")
            return None, None
        except socket.error as e:
            logger.error(f"接收消息时网络错误: {e}", exc_info=True)
            return None, None
        except Exception as e:
            logger.error(f"接收消息失败: {e}", exc_info=True)
            return None, None

    def _send_response(self, conn: socket.socket, data: Dict[str, Any], msg_type: str) -> None:
        """发送响应给客户端"""
        try:
            json_data = json.dumps(data).encode("utf-8")
            header = json.dumps({
                                RESPONSE_FIELD_TYPE: msg_type, 
                                 RESPONSE_FIELD_DATA_SIZE: len(json_data)
                                 }).encode("utf-8")
            
            conn.sendall(struct.pack("!I", len(header)))
            conn.sendall(header)
            conn.sendall(json_data)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError) as e:
            logger.debug(f"客户端连接已中断: {e}")
        except socket.error as e:
            logger.error(f"发送响应时网络错误: {e}", exc_info=True)

    def _metrics_loop(self) -> None:
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
                        # 优化：直接使用 deque 的迭代器，避免创建完整列表
                        lat_list = list(lat_q)
                        sample_count = len(lat_list)
                        if sample_count > 0:
                            # 计算平均值（不需要排序）
                            avg = sum(lat_list) / sample_count
                            
                            # 优化 P95 计算：只在需要时排序
                            if sample_count >= METRICS_P95_MIN_SAMPLES:
                                # 对于较大样本，使用部分排序优化
                                sorted_list = sorted(lat_list)
                                p95_idx = int(sample_count * METRICS_P95_PERCENTILE) - 1
                                p95 = sorted_list[p95_idx] if p95_idx >= 0 else sorted_list[-1]
                            else:
                                # 小样本直接使用最大值作为近似
                                p95 = max(lat_list)
                            
                            lines.append(
                                f"  - {t}: {self._req_count_by_type[t]} 次 | 平均 {avg*1000:.1f}ms | P95 {p95*1000:.1f}ms | 最近样本 {sample_count}"
                            )
                logger.info("\n".join(lines))

    def get_health_status(self) -> Dict[str, Any]:
        """获取服务器健康状态
        
        Returns:
            Dict[str, Any]: 包含服务器状态、模型加载状态等信息
        """
        with self._stats_lock:
            uptime = time.time() - self._start_time
            queue_size = self.task_queue.qsize()
            queue_maxsize = self.task_queue.maxsize()
        
        # 检查模型状态
        yolo_status = "unknown"
        ocr_status = "unknown"
        
        if settings.per_thread_models:
            # 独立模式：检查是否有工作线程成功加载模型
            yolo_status = "per_thread"
            ocr_status = "per_thread"
        else:
            # 共享模式：检查共享模型状态
            if self._shared_yolo is not None:
                if hasattr(self._shared_yolo, '_model_loaded') and self._shared_yolo._model_loaded:
                    yolo_status = "loaded"
                else:
                    yolo_status = "failed"
            else:
                yolo_status = "not_initialized"
            
            if self._shared_ocr is not None:
                if hasattr(self._shared_ocr, '_model_loaded') and self._shared_ocr._model_loaded:
                    ocr_status = "loaded"
                else:
                    ocr_status = "failed"
            else:
                ocr_status = "not_initialized"
        
        # 判断整体健康状态
        is_healthy = (
            self.running and
            (yolo_status in ["loaded", "per_thread"]) and
            (ocr_status in ["loaded", "per_thread"])
        )
        
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "running": self.running,
            "uptime_seconds": round(uptime, 2),
            "models": {
                "yolo": {
                    "status": yolo_status,
                    "mode": "per_thread" if settings.per_thread_models else "shared"
                },
                "ocr": {
                    "status": ocr_status,
                    "mode": "per_thread" if settings.per_thread_models else "shared"
                }
            },
            "queue": {
                "current_size": queue_size,
                "max_size": queue_maxsize,
                "usage_percent": round((queue_size / queue_maxsize * 100) if queue_maxsize > 0 else 0, 2)
            },
            "connections": {
                "active": self._active_connections,
                "max": MAX_CONNECTIONS
            },
            "server_address": {
                "host": self.server_address[0],
                "port": self.server_address[1]
            }
        }

    def get_metrics(self) -> Dict[str, Any]:
        """获取服务器性能指标
        
        Returns:
            Dict[str, Any]: 包含请求统计、延迟指标等信息
        """
        with self._stats_lock:
            uptime = time.time() - self._start_time
            total_requests = self._req_count
            total_errors = self._err_count
            error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0.0
            
            metrics_by_type = {}
            for req_type, lat_q in self._latencies_by_type.items():
                if lat_q:
                    lat_list = list(lat_q)
                    sample_count = len(lat_list)
                    if sample_count > 0:
                        avg_latency = sum(lat_list) / sample_count
                        
                        # 计算 P95
                        if sample_count >= METRICS_P95_MIN_SAMPLES:
                            sorted_list = sorted(lat_list)
                            p95_idx = int(sample_count * METRICS_P95_PERCENTILE) - 1
                            p95_latency = sorted_list[p95_idx] if p95_idx >= 0 else sorted_list[-1]
                        else:
                            p95_latency = max(lat_list)
                        
                        metrics_by_type[req_type] = {
                            "request_count": self._req_count_by_type.get(req_type, 0),
                            "sample_count": sample_count,
                            "avg_latency_ms": round(avg_latency * 1000, 2),
                            "p95_latency_ms": round(p95_latency * 1000, 2),
                            "min_latency_ms": round(min(lat_list) * 1000, 2),
                            "max_latency_ms": round(max(lat_list) * 1000, 2),
                        }
            
            return {
                "uptime_seconds": round(uptime, 2),
                "total_requests": total_requests,
                "total_errors": total_errors,
                "error_rate_percent": round(error_rate, 2),
                "requests_per_second": round(total_requests / uptime, 2) if uptime > 0 else 0.0,
                "by_type": metrics_by_type,
                "queue": {
                    "current_size": self.task_queue.qsize(),
                    "max_size": self.task_queue.maxsize(),
                    "usage_percent": round((self.task_queue.qsize() / self.task_queue.maxsize() * 100) if self.task_queue.maxsize() > 0 else 0, 2)
                },
                "connections": {
                    "active": self._active_connections,
                    "max": MAX_CONNECTIONS
                }
            }

    def _record_metric(
        self, req_type: str, duration: float, success: bool, error: bool
    ) -> None:
        with self._stats_lock:
            self._req_count += 1
            self._req_count_by_type[req_type] += 1
            if error:
                self._err_count += 1
            else:
                self._latencies_by_type[req_type].append(duration)
