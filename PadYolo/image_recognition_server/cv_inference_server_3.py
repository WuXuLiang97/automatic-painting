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
from yolo.yolo_main import YoloV8
from root_dir import root_path
import tkinter as tk
from tkinter import scrolledtext, messagebox
import sys
from paddleocr import PaddleOCR
from typing import Optional, Tuple, Dict, Any, List
import gc
import torch

# 全局配置
MAX_WORKERS = 100
TASK_QUEUE_SIZE = 20
MODEL_WARMUP = True
BUFFER_SIZE = 4096
HEADER_SIZE = 4  # 4 bytes for header length
#FIXED_PORT = 34717  # 固定端口号
FIXED_PORT = 12345 # 固定端口号
PRE_WARM_MODEL_COUNT = 2  # 预热模型数量
MAX_MODEL_INSTANCES = 100  # 最大模型实例数量，防止无限增长

# 模型初始化
DET_MODEL_DIR = os.path.join(root_path, 'ch_PP-OCRv4_det_infer')
REC_MODEL_DIR = os.path.join(root_path, 'ch_PP-OCRv4_rec_infer')

class PrintRedirector:
    """重定向标准输出到Tkinter文本框"""
    def __init__(self, text_widget: scrolledtext.ScrolledText):
        self.text_widget = text_widget
        self.queue = queue.Queue()
        self.running = True
        
        # 在主线程中绑定事件
        self.text_widget.bind("<<UpdateText>>", self._process_queue)
        
        # 启动工作线程
        self.thread = threading.Thread(target=self._monitor_queue, daemon=True)
        self.thread.start()

    def write(self, message: str) -> None:
        """将消息放入队列"""
        self.queue.put(message)
        # 通知主线程更新
        self.text_widget.event_generate("<<UpdateText>>")

    def _monitor_queue(self) -> None:
        """监控队列并触发事件"""
        while self.running:
            try:
                # 定期检查队列
                if not self.queue.empty():
                    self.text_widget.event_generate("<<UpdateText>>")
                time.sleep(0.1)
            except:
                break

    def _process_queue(self, event=None) -> None:
        """处理队列中的所有消息(在主线程执行)"""
        while not self.queue.empty():
            try:
                message = self.queue.get_nowait()
                self.text_widget.insert(tk.END, message)
                self.text_widget.see(tk.END)
                self.text_widget.update_idletasks()
            except queue.Empty:
                break

    def flush(self) -> None:
        """实现flush方法以兼容标准输出"""
        self._process_queue()

class ModelManager:
    """模型管理器，预加载模型实例池并为连接分配模型"""
    def __init__(self):
        self.yolo_pool = Queue()
        self.ocr_pool = Queue()
        self.yolo_instances = {}  # 跟踪已分配的YOLO实例
        self.ocr_instances = {}   # 跟踪已分配的OCR实例
        self.total_yolo_instances = 0  # 跟踪总YOLO实例数
        self.total_ocr_instances = 0   # 跟踪总OCR实例数
        self.lock = threading.Lock()
        self.pre_warm_models()

    def pre_warm_models(self) -> None:
        """预加载模型实例到池中"""
        print(f"预加载 {PRE_WARM_MODEL_COUNT} 个模型实例...")
        for i in range(PRE_WARM_MODEL_COUNT):
            # 预加载YOLO模型
            yolo = YoloV8()
            yolo.loadModel()
            if MODEL_WARMUP:
                self._warmup_model(yolo)
            self.yolo_pool.put(yolo)
            
            # 预加载OCR模型
            ocr = self._create_ocr_instance()
            self.ocr_pool.put(ocr)
            
            self.total_yolo_instances += 1
            self.total_ocr_instances += 1
            
            print(f"已预加载模型实例 {i+1}/{PRE_WARM_MODEL_COUNT}")
        print("模型预加载完成")

    def _create_ocr_instance(self) -> PaddleOCR:
        """创建OCR实例的辅助方法"""
        return PaddleOCR(
            lang='ch',
            det_model_dir=DET_MODEL_DIR,
            rec_model_dir=REC_MODEL_DIR,
            use_gpu=True,
            precision='fp16',
            use_angle_cls=False,
            use_space_char=False,
            show_log=False,
            enable_mkldnn=False,  # 关闭MKLDNN加速，可能减少内存占用
        )

    def get_models(self, client_id: str) -> Tuple[YoloV8, PaddleOCR]:
        """从池中获取模型实例"""
        with self.lock:
            if self.yolo_pool.qsize() > 0 and self.ocr_pool.qsize() > 0:
                # 从池中获取模型
                yolo = self.yolo_pool.get()
                ocr = self.ocr_pool.get()
                
                # 记录分配情况
                self.yolo_instances[client_id] = yolo
                self.ocr_instances[client_id] = ocr
                
                print(f"为客户端 {client_id} 分配预加载模型")
                return yolo, ocr
            else:
                # 检查是否超过最大实例限制
                if (self.total_yolo_instances >= MAX_MODEL_INSTANCES or 
                    self.total_ocr_instances >= MAX_MODEL_INSTANCES):
                    print(f"警告: 已达到最大模型实例限制({MAX_MODEL_INSTANCES})，等待可用模型...")
                    # 等待模型返回池中
                    while self.yolo_pool.empty() or self.ocr_pool.empty():
                        time.sleep(0.1)
                    return self.get_models(client_id)
                
                # 池中没有可用模型，创建新实例
                print(f"模型池已空，为客户端 {client_id} 创建新模型实例")
                yolo = YoloV8()
                yolo.loadModel()
                if MODEL_WARMUP:
                    self._warmup_model(yolo)
                
                ocr = self._create_ocr_instance()
                
                self.yolo_instances[client_id] = yolo
                self.ocr_instances[client_id] = ocr
                self.total_yolo_instances += 1
                self.total_ocr_instances += 1
                
                return yolo, ocr

    # 在ModelManager的return_models方法中优化池管理逻辑
    def return_models(self, client_id: str) -> None:
        """将模型实例返回到池中"""
        with self.lock:
            if client_id in self.yolo_instances and client_id in self.ocr_instances:
                yolo = self.yolo_instances[client_id]
                ocr = self.ocr_instances[client_id]
                
                # 清理GPU缓存
                self._cleanup_gpu_memory()
                
                # 优化池管理：限制池大小，避免无限增长
                max_pool_size = PRE_WARM_MODEL_COUNT * 10  # 设置最大池大小为预加载数量的2倍
                
                if (self.yolo_pool.qsize() < max_pool_size and 
                    self.ocr_pool.qsize() < max_pool_size):
                    # 池未满，返回模型
                    self.yolo_pool.put(yolo)
                    self.ocr_pool.put(ocr)
                else:
                    # 池已满，销毁多余实例
                    self._destroy_model(yolo, ocr)
                    self.total_yolo_instances -= 1
                    self.total_ocr_instances -= 1
                
                # 移除记录
                del self.yolo_instances[client_id]
                del self.ocr_instances[client_id]

    def _destroy_model(self, yolo: YoloV8, ocr: PaddleOCR) -> None:
        """销毁模型实例并释放资源"""
        try:
            # 清理YOLO模型
            if hasattr(yolo, 'model'):
                if hasattr(yolo.model, 'cpu'):
                    yolo.model.cpu()
                # 清除参数引用
                if hasattr(yolo.model, 'parameters'):
                    for param in yolo.model.parameters():
                        param.data = None
                del yolo.model
                yolo.model = None

            # 优化OCR资源释放
            if hasattr(ocr, '_text_sys'):
                # 直接清理PaddleOCR的核心组件
                text_sys = ocr._text_sys
                if hasattr(text_sys, 'detector') and text_sys.detector:
                    text_sys.detector = None
                if hasattr(text_sys, 'recognizer') and text_sys.recognizer:
                    text_sys.recognizer = None
                if hasattr(text_sys, 'cls') and text_sys.cls:
                    text_sys.cls = None
                ocr._text_sys = None
            
            # 强制垃圾回收
            for _ in range(3):
                gc.collect()
                
        except Exception as e:
            print(f"销毁模型时出错: {e}")

    def _cleanup_gpu_memory(self) -> None:
        """清理GPU内存"""
        try:
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except:
            pass

    @staticmethod
    def _warmup_model(model: YoloV8) -> None:
        """模型预热"""
        dummy = np.zeros((640, 640, 3), dtype=np.uint8)
        model.detect(dummy)

class ThreadedServer:
    """多线程服务器类"""
    def __init__(self, host: str = '0.0.0.0', port: int = FIXED_PORT, instance_id: int = 1):
        self.server_address = (host, port)
        self.task_queue = Queue(maxsize=TASK_QUEUE_SIZE)
        self.workers: List[threading.Thread] = []
        self.running = False
        self.instance_id = instance_id
        self.model_manager = ModelManager()
        self.client_counter = 0
        self.client_lock = threading.Lock()
        self.server_socket = None
        self.active_connections = set()  # 跟踪活跃连接

    def start(self) -> None:
        """启动服务器"""
        self.running = True
        
        # 创建工作线程
        self._create_workers()
        
        # 启动监听线程
        listener = threading.Thread(target=self._listen, daemon=True)
        listener.start()
        
        # 启动内存监控线程
        monitor = threading.Thread(target=self._memory_monitor, daemon=True)
        monitor.start()

    def _memory_monitor(self) -> None:
        """监控内存使用情况"""
        while self.running:
            try:
                if torch.cuda.is_available():
                    allocated = torch.cuda.memory_allocated() / 1024**2
                    cached = torch.cuda.memory_reserved() / 1024**2
                    if allocated > 1024:  # 超过1GB时输出警告
                        print(f"GPU内存警告: 已分配{allocated:.2f}MB, 缓存{cached:.2f}MB")
                        # 尝试清理缓存
                        gc.collect()
                        torch.cuda.empty_cache()
            except:
                pass
            time.sleep(30)  # 每30秒检查一次

    def _create_workers(self) -> None:
        """创建工作线程"""
        for _ in range(MAX_WORKERS):
            worker = threading.Thread(target=self._worker, daemon=True)
            worker.start()
            self.workers.append(worker)

    def _listen(self) -> None:
        """监听客户端连接"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._configure_socket(self.server_socket)
        
        try:
            # 绑定到固定端口
            self.server_socket.bind(self.server_address)
            self.server_socket.listen(10)

            # 获取本机IP地址
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            
            print(f"服务器启动成功!")
            print(f"固定端口: {FIXED_PORT}")
            print(f"监听地址: 0.0.0.0:{FIXED_PORT}")
            print(f"本地连接: 127.0.0.1:{FIXED_PORT}")
            print(f"局域网连接: {local_ip}:{FIXED_PORT}")
            print(f"预加载模型数量: {PRE_WARM_MODEL_COUNT}")
            print(f"最大模型实例数: {MAX_MODEL_INSTANCES}")
            print(f"等待客户端连接...")

            while self.running:
                try:
                    conn, addr = self.server_socket.accept()
                    self._configure_client_socket(conn)
                    
                    # 为每个连接分配唯一ID
                    with self.client_lock:
                        client_id = f"{addr[0]}:{addr[1]}_{self.client_counter}"
                        self.client_counter += 1
                    
                    # 跟踪活跃连接
                    self.active_connections.add(client_id)
                    self.task_queue.put((conn, addr, client_id))
                except socket.error as e:
                    if self.running:  # 只在服务器运行时打印错误
                        print(f"接受连接时出错: {e}")
                    continue
        except Exception as e:
            print(f"服务器启动失败: {e}")
            print(f"端口 {FIXED_PORT} 可能已被占用，请检查或更换端口")
        finally:
            self.running = False
            if self.server_socket:
                self.server_socket.close()

    def _configure_socket(self, sock: socket.socket) -> None:
        """配置服务器socket"""
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 6)

    def _configure_client_socket(self, conn: socket.socket) -> None:
        """配置客户端socket"""
        conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 6)
        conn.settimeout(30)  # 设置超时时间

    def _worker(self) -> None:
        """工作线程处理函数"""
        while self.running:
            try:
                conn, addr, client_id = self.task_queue.get(timeout=1)
                # 为每个连接分配模型实例
                yolo, ocr_engine = self.model_manager.get_models(client_id)
                self._handle_client(conn, addr, client_id, yolo, ocr_engine)
                # 标记任务完成
                self.task_queue.task_done()
            except queue.Empty:
                continue

    def _handle_client(self, conn: socket.socket, addr: tuple, client_id: str,
                      yolo: YoloV8, ocr_engine: PaddleOCR) -> None:
        """处理客户端请求"""
        try:
            with conn:
                self._log_connection(addr, client_id)
                conn.settimeout(30)  # 设置连接超时
                while True:
                    # 添加心跳检测
                    try:
                        header, image = self._receive_message(conn)
                        if not header:
                            break
                    except socket.timeout:
                        print(f"客户端 {client_id} 连接超时")
                        break
                    start_time = time.time()
                    result = self._process_request(header, image, yolo, ocr_engine)
                    self._send_response(conn, result, header['type'])
                    
                    latency = (time.time() - start_time) * 1000
                    print(f"客户端 {client_id} --> {header['type']} 请求处理完成 耗时: {latency:.2f}ms")

        except Exception as e:
            traceback.print_exc()
            print(f"客户端 {client_id} 处理异常: {str(e)}")
        finally:
            # 移除活跃连接记录
            if client_id in self.active_connections:
                self.active_connections.remove(client_id)
            # 返回模型到池中
            self.model_manager.return_models(client_id)
            print(f"客户端 {client_id} 断开连接")

    def _log_connection(self, addr: tuple, client_id: str) -> None:
        """记录连接日志"""
        formatted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{formatted_time}\t新连接: {addr} (ID: {client_id})")

    def _process_request(self, header: Dict[str, Any], image: np.ndarray,
                        yolo: YoloV8, ocr_engine: PaddleOCR) -> Any:
        """处理不同类型的请求"""
        request_type = header['type']
        
        if request_type == 'game_windows':
            return yolo.detect(image)
        elif request_type == 'min_map':
            return yolo.min_map_detect(image)
        elif request_type == 'ocr':
            return self._ocr_process(image, ocr_engine)
        else:
            raise ValueError(f"无效的请求类型: {request_type}")

    def _receive_message(self, conn: socket.socket) -> Tuple[Optional[Dict], Optional[np.ndarray]]:
        """接收客户端消息"""
        try:
            # 接收消息头长度
            header_len = self._recv_all(conn, HEADER_SIZE)
            if not header_len:
                return None, None

            # 接收消息头
            header_size = struct.unpack('!I', header_len)[0]
            header_data = self._recv_all(conn, header_size)
            if not header_data:
                return None, None

            header = json.loads(header_data.decode('utf-8'))

            # 接收图像数据
            image_size = header['image_size']
            image_data = self._recv_all(conn, image_size)
            if not image_data:
                return None, None

            # 解码图像
            image = cv2.imdecode(np.frombuffer(image_data, dtype=np.uint8), cv2.IMREAD_COLOR)
            
            # 记录大图像
            # if image_size > 300000:
            #     print(f"接收图片数据长度:{image_size}字节")
                
            return header, image

        except (socket.timeout, ConnectionResetError, json.JSONDecodeError):
            return None, None

    def _recv_all(self, conn: socket.socket, size: int) -> Optional[bytes]:
        """接收指定大小的数据"""
        data = bytearray()
        while len(data) < size:
            chunk = conn.recv(min(BUFFER_SIZE, size - len(data)))
            if not chunk:
                return None
            data.extend(chunk)
        return bytes(data)

    def _send_response(self, conn: socket.socket, data: Any, msg_type: str) -> None:
        """发送响应给客户端"""
        try:
            json_data = json.dumps(data).encode('utf-8')
            header = json.dumps({
                'type': msg_type,
                'data_size': len(json_data)
            }).encode('utf-8')

            # 发送消息头长度和消息头
            conn.sendall(struct.pack('!I', len(header)))
            conn.sendall(header)
            
            # 发送数据
            conn.sendall(json_data)
        except (BrokenPipeError, ConnectionResetError):
            print("客户端连接已中断")

    # def _ocr_process(self, image: np.ndarray, ocr_engine: PaddleOCR) -> str:
    #     """处理OCR请求"""
    #     gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    #     results = ocr_engine.ocr(gray, det=False, cls=False)
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

def get_ip_address():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        _ip = s.getsockname()[0]
        s.close()
        return _ip
    except Exception as e:
        print(f"获取 IP 地址时出现错误: {e}")
        return None

def main() -> None:
    """主函数"""
    ip = get_ip_address()
    root = tk.Tk()
    root.title(f"服务器日志-<{ip}>  <--请把这个ip填到<主机IP>的输入框里")
    root.geometry("800x600")

    # 创建框架
    frame = tk.Frame(root)
    frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    # 信息显示区域
    info_frame = tk.Frame(frame)
    info_frame.pack(fill=tk.X, pady=(0, 10))
    
    tk.Label(info_frame, text="服务器状态:", font=("Arial", 12, "bold")).pack(anchor=tk.W)
    status_label = tk.Label(info_frame, text="正在启动...", fg="blue", font=("Arial", 10))
    status_label.pack(anchor=tk.W)
    
    tk.Label(info_frame, text="连接信息:", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(10, 0))
    info_text = tk.Text(info_frame, height=2, width=80)
    info_text.pack(fill=tk.X, pady=(5, 0))

    # 日志区域
    tk.Label(frame, text="运行日志:", font=("Arial", 12, "bold")).pack(anchor=tk.W)
    text_area = scrolledtext.ScrolledText(frame, width=80, height=20)
    text_area.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
    
    # 重定向标准输出
    sys.stdout = PrintRedirector(text_area)

    # 启动服务实例
    server = ThreadedServer(port=FIXED_PORT, instance_id=0)
    threading.Thread(target=server.start, daemon=True).start()

    # 更新UI信息
    def update_ui():
        info = f"预加载模型数量: {PRE_WARM_MODEL_COUNT}\n"
        info += f"模型池状态: YOLO({server.model_manager.yolo_pool.qsize()}/{PRE_WARM_MODEL_COUNT}) "
        info += f"OCR({server.model_manager.ocr_pool.qsize()}/{PRE_WARM_MODEL_COUNT})"
        
        info_text.delete(1.0, tk.END)
        info_text.insert(1.0, info)
        
        # 检查服务器是否启动成功
        if server.server_socket and server.running:
            status_label.config(text="运行中", fg="green")
        else:
            status_label.config(text="启动失败 - 端口可能被占用", fg="red")
        
        # 定期更新UI
        root.after(5000, update_ui)

    # 延迟更新UI
    root.after(1000, update_ui)

    def on_closing() -> None:
        """窗口关闭事件处理"""
        server.running = False
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == '__main__':
    main()