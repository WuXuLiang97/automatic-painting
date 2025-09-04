import threading
from PyQt5.QtCore import pyqtSignal, QThread
from global_fields import display_queue
import time
import numpy as np


class DisplayThread(QThread):
    """专用展示线程"""

    update_signal = pyqtSignal(np.ndarray)  # 图像更新信号

    def __init__(self):
        super().__init__()
        self.running = True
        self.lock = threading.Lock()  # 添加线程锁

    def run(self):
        while self.running:
            with self.lock:  # 使用锁保护共享资源
                if not display_queue.empty():
                    frame = display_queue.get()
                    self.update_signal.emit(frame)
            time.sleep(0.033)

    def stop(self):
        with self.lock:
            self.running = False
