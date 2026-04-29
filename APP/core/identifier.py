# -*- coding: utf-8 -*-
import cv2
import time
from typing import Optional, Tuple, List
from core.global_variable import display_queue


class CaptureCardConnection:
    def __init__(self):
        self.cap = None
        self.device_index = None
        self.connection_status = False
        self.last_check_time = 0
        self.check_interval = 2.0  # 连接状态检查间隔（秒）

    def find_available_devices(self) -> List[int]:
        """
        查找所有可用的采集卡设备

        返回:
            List[int]: 可用设备的索引列表
        """
        available_devices = []
        for idx in range(10):  # 检查前10个可能的设备索引
            cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    available_devices.append(idx)
                    print(f"找到设备 {idx}: 分辨率 {frame.shape[1]}x{frame.shape[0]}")
                cap.release()

        return available_devices

    def connect(self, device_index: int, resolution: Optional[Tuple[int, int]] = None) -> bool:
        """
        连接到指定的采集卡设备

        参数:
            device_index (int): 设备索引
            resolution (Optional[Tuple[int, int]]): 可选的分辨率设置 (宽度, 高度)

        返回:
            bool: 连接是否成功
        """
        # 如果已经连接，先断开
        if self.cap is not None:
            self.disconnect()

        # 尝试连接设备
        self.cap = cv2.VideoCapture(device_index)
        if not self.cap.isOpened():
            print(f"无法打开设备 {device_index}")
            self.cap = None
            self.connection_status = False
            return False

        # 设置分辨率（如果指定）
        if resolution:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])

        self.device_index = device_index
        self.connection_status = True
        self.last_check_time = time.time()

        # 获取实际分辨率
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self.cap.get(cv2.CAP_PROP_FPS)

        print(f"已连接到设备 {device_index}")
        print(f"分辨率: {width}x{height}, FPS: {fps:.2f}")

        return True

    def disconnect(self):
        """断开与采集卡的连接"""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            self.device_index = None
            self.connection_status = False
            print("已断开采集卡连接")

    def is_connected(self) -> bool:
        """
        检查采集卡是否仍然连接

        返回:
            bool: 连接状态
        """
        current_time = time.time()

        # 避免过于频繁地检查连接状态
        if current_time - self.last_check_time < self.check_interval:
            return self.connection_status

        self.last_check_time = current_time

        # 如果未连接，直接返回False
        if not self.connection_status or self.cap is None:
            return False

        # 检查采集卡是否仍然可访问
        if not self.cap.isOpened():
            self.connection_status = False
            return False

        # 尝试读取一帧来验证连接
        ret, frame = self.cap.read()
        if not ret or frame is None:
            self.connection_status = False
            return False

        self.connection_status = True
        return True

    def get_connection_info(self) -> Optional[dict]:
        """
        获取连接信息

        返回:
            Optional[dict]: 连接信息字典，包含设备索引、分辨率等
        """
        if not self.is_connected() or self.cap is None:
            return None

        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self.cap.get(cv2.CAP_PROP_FPS)

        return {
            'device_index': self.device_index,
            'resolution': (width, height),
            'fps': fps,
            'backend': 'DirectShow'  # 因为我们使用了CAP_DSHOW
        }

    def capture(self) -> Optional[cv2.Mat]:
        """
        捕获单帧图像（用于测试或偶尔获取画面）

        返回:
            Optional[cv2.Mat]: 捕获的帧图像，如果失败则返回None
        """
        if not self.is_connected() or self.cap is None:
            return None

        ret, frame = self.cap.read()
        if ret and frame is not None:
            print(f"frame:{frame.shape}")
            frame1 = frame[0:600, 0:1067]
            if not display_queue.full():
                # 为展示线程缩小分辨率
                display_frame = cv2.resize(frame1, (356, 200))
                display_queue.put(display_frame)
            return frame1

        return None

    def __del__(self):
        """析构函数，确保资源被释放"""
        self.disconnect()


# 使用示例
if __name__ == "__main__":
    # 创建采集卡连接实例
    capture_card = CaptureCardConnection()

    # 查找可用设备
    devices = capture_card.find_available_devices()
    if not devices:
        print("未找到可用采集卡设备")
        exit()

    # 连接到第一个可用设备
    if capture_card.connect(devices[0]):
        print("连接成功")

        # 定期检查连接状态
        for i in range(5):
            if capture_card.is_connected():
                print(f"连接状态: 正常 ({i + 1}/5)")

                # 获取连接信息
                info = capture_card.get_connection_info()
                if info:
                    print(f"设备信息: 索引 {info['device_index']}, 分辨率 {info['resolution'][0]}x{info['resolution'][1]}")

                # 可选：捕获一帧并显示（用于测试）
                frame = capture_card.capture_single_frame()
                if frame is not None:
                    cv2.imshow("Test Frame", frame)
                    cv2.waitKey(1000)  # 显示1秒
                    cv2.destroyAllWindows()
            else:
                print("连接已断开")
                break

            time.sleep(1)  # 等待1秒

        # 断开连接
        capture_card.disconnect()
    else:
        print("连接失败")
