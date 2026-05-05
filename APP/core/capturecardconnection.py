# -*- coding: utf-8 -*-

import os
import platform
import time
from typing import Optional, Tuple, List, Dict

import cv2
import numpy as np

from core.global_variable import display_queue
from utils.logging_setup import logger

class CaptureCardConnection:
    def __init__(self):
        """
        初始化采集卡连接 - 使用OpenCV后端
        """
        self.cap = None
        self.device_name = None
        self.device_id = None
        self.connection_status = False
        self.last_check_time = 0
        self.check_interval = 2.0  # 连接状态检查间隔（秒）
        self.actual_resolution = (0, 0)  # 存储实际分辨率
        self.os_type = platform.system()  # 获取操作系统类型
        self.available_devices = []
        self.current_frame = None
        self.last_frame_time = 0
        self.frame_rate = 0
        self.preview_active = False  # 预览窗口状态标志
        self.max_device_index = 10  # 最大尝试设备索引数
        self.crop_region = None  # 裁剪区域 (x, y, width, height)
        # 交互式裁剪选择状态
        self._selecting = False
        self._sel_start = (0, 0)
        self._sel_end = (0, 0)

    def find_available_devices(self) -> List[Dict[str, str]]:
        """
        查找所有可用的视频设备

        返回:
            List[Dict]: 可用设备的信息列表，包含名称和ID
        """
        devices = []

        # 尝试不同的设备索引
        for i in range(self.max_device_index):
            try:
                # 尝试打开设备
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    # 尝试读取一帧以确认设备可用
                    ret, frame = cap.read()
                    if ret:
                        # 获取设备名称（在某些平台上可能不可用）
                        device_name = f"Device {i}"

                        # 尝试获取更详细的设备信息
                        try:
                            # 获取后端名称
                            backend_name = cap.getBackendName()
                            # 获取分辨率
                            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                            device_name = f"Device {i} ({backend_name}, {width}x{height})"
                        except:
                            pass

                        # 添加到设备列表
                        devices.append({
                            'name': device_name,
                            'id': str(i),
                            'full_name': device_name,
                            'resolution': (width, height) if 'width' in locals() else (0, 0)
                        })

                    # 释放设备
                    cap.release()
            except Exception as e:
                logger.debug(f"检查设备索引 {i} 时出错: {str(e)}")
                continue

        logger.info(f"找到 {len(devices)} 个可用设备")
        self.available_devices = devices
        return devices

    def connect(self, device_index: int, resolution: Optional[Tuple[int, int]] = None) -> bool:
        """
        连接到指定的采集卡设备

        参数:
            device_index (int): 设备索引（从0开始）
            resolution (Optional[Tuple[int, int]]): 可选的分辨率设置 (宽度, 高度)

        返回:
            bool: 连接是否成功
        """
        # 如果已经连接，先断开
        if self.cap is not None:
            self.disconnect()

        # 检查设备索引是否有效
        if device_index < 0 or device_index >= len(self.available_devices):
            logger.error(f"设备索引 {device_index} 无效，可用设备数量: {len(self.available_devices)}")
            return False

        device_info = self.available_devices[device_index]
        device_id = device_info['id']

        try:
            # 使用OpenCV打开设备
            self.cap = cv2.VideoCapture(int(device_id))

            # 检查是否成功打开
            if not self.cap.isOpened():
                logger.error(f"无法打开设备索引 {device_id}")
                return False

            # 设置分辨率（如果指定）
            if resolution:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])

            # 获取实际分辨率
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.actual_resolution = (width, height)

            # 设置自动对焦（如果可用）
            try:
                self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
            except:
                pass

            # 设置自动曝光（如果可用）
            try:
                self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
            except:
                pass

            self.device_name = device_info['name']
            self.device_id = device_id
            self.connection_status = True
            self.last_check_time = time.time()

            logger.info(f"已成功连接到设备: {self.device_name}")
            logger.info(f"实际分辨率: {self.actual_resolution[0]}x{self.actual_resolution[1]}")
            self.start_preview(duration=5)  # 0表示无限预览
            return True

        except Exception as e:
            logger.error(f"连接设备失败: {str(e)}")
            self.disconnect()
            return False

    def set_crop_region(self, x: int, y: int, width: int, height: int):
        """
        设置裁剪区域

        参数:
            x (int): 起始X坐标
            y (int): 起始Y坐标
            width (int): 裁剪宽度
            height (int): 裁剪高度
        """
        self.crop_region = (x, y, width, height)
        logger.info(f"设置裁剪区域: x={x}, y={y}, width={width}, height={height}")

    def clear_crop_region(self):
        """清除裁剪区域"""
        self.crop_region = None
        logger.info("已清除裁剪区域")

    def disconnect(self):
        """断开与采集卡的连接"""
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception as e:
                logger.error(f"关闭连接时出错: {str(e)}")
            finally:
                self.cap = None
                self.device_name = None
                self.device_id = None
                self.connection_status = False
                self.actual_resolution = (0, 0)
                self.crop_region = None
                logger.info("已断开采集卡连接")

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

        # 尝试读取一帧来验证连接
        try:
            # 使用非阻塞方式检查连接状态
            ret, frame = self.cap.read()
            if ret:
                # 将帧放回，以便下次读取
                self.current_frame = frame
                self.connection_status = True
                return True
            else:
                self.connection_status = False
                return False

        except Exception as e:
            logger.error(f"检查连接状态失败: {str(e)}")
            self.connection_status = False
            return False

    def get_connection_info(self) -> Optional[dict]:
        """
        获取连接信息

        返回:
            Optional[dict]: 连接信息字典，包含设备名称、分辨率等
        """
        if not self.is_connected() or self.cap is None:
            return None

        return {
            'device_name': self.device_name,
            'device_id': self.device_id,
            'resolution': self.actual_resolution,
            'backend': 'OpenCV',
            'os': self.os_type,
            'crop_region': self.crop_region
        }

    def capture(self, blocking: bool = True) -> Optional[np.ndarray]:
        """
        捕获单帧图像

        参数:
            blocking (bool): 是否阻塞直到获取到帧

        返回:
            Optional[np.ndarray]: 捕获的帧图像 (OpenCV 格式)，如果失败则返回None
        """
        if not self.is_connected() or self.cap is None:
            return None

        try:
            # 从视频流中读取帧
            ret, frame = self.cap.read()

            if not ret:
                return None

            # 更新帧率和时间戳
            current_time = time.time()
            if self.last_frame_time > 0:
                self.frame_rate = 0.9 * self.frame_rate + 0.1 / (current_time - self.last_frame_time)
            self.last_frame_time = current_time

            # 应用裁剪（如果设置了裁剪区域）
            if self.crop_region:
                x, y, width, height = self.crop_region
                # 确保裁剪区域在帧范围内
                h, w = frame.shape[:2]
                x = max(0, min(x, w - 1))
                y = max(0, min(y, h - 1))
                width = min(width, w - x)
                height = min(height, h - y)

                if width > 0 and height > 0:
                    frame = frame[y:y + height, x:x + width]
            self.current_frame = frame
            if not display_queue.full():
                # 为展示线程缩小分辨率
                display_frame = cv2.resize(frame, (356, 200))
                display_queue.put(display_frame)
            return frame

        except Exception as e:
            logger.error(f"捕获帧失败: {str(e)}")
            return None

    def _on_mouse(self, event, x, y, flags, param):
        """鼠标回调：拖拽选择裁剪区域"""
        if event == cv2.EVENT_LBUTTONDOWN:
            self._selecting = True
            self._sel_start = (x, y)
            self._sel_end = (x, y)
        elif event == cv2.EVENT_MOUSEMOVE and self._selecting:
            self._sel_end = (x, y)
        elif event == cv2.EVENT_LBUTTONUP:
            self._selecting = False
            self._sel_end = (x, y)
            x1, y1 = self._sel_start
            x2, y2 = self._sel_end
            if abs(x2 - x1) > 5 and abs(y2 - y1) > 5:
                rx = min(x1, x2)
                ry = min(y1, y2)
                rw = abs(x2 - x1)
                rh = abs(y2 - y1)
                self.set_crop_region(rx, ry, rw, rh)
                logger.info(f"交互式设置裁剪区域: x={rx}, y={ry}, w={rw}, h={rh}")

    def start_preview(self, window_name: str = "Capture Card Preview", duration: float = 0) -> bool:
        """启动预览窗口。

        鼠标拖拽选择裁剪区域，按键:
          c = 截图 (BMP),  r = 重置裁剪,  Esc/q = 退出
        """
        if not self.is_connected():
            logger.error("无法启动预览：未连接到设备")
            return False

        try:
            self.preview_active = True
            self._selecting = False
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(window_name, 800, 600)
            cv2.setMouseCallback(window_name, self._on_mouse)
            frame_count = 0
            start_time = time.time()

            while self.preview_active:
                if duration > 0 and time.time() - start_time > duration:
                    break

                if not self.is_connected():
                    logger.error("连接已断开")
                    break

                frame = self.capture()
                if frame is not None:
                    frame_count += 1
                    elapsed_time = time.time() - start_time
                    if elapsed_time > 0:
                        fps = frame_count / elapsed_time
                        info_lines = [f"FPS: {fps:.1f} | Res: {frame.shape[1]}x{frame.shape[0]}"]
                        if self.crop_region:
                            info_lines.append(f"Crop: {self.crop_region[2]}x{self.crop_region[3]}")
                        info_lines.append("Drag mouse to set crop | c=snap(BMP) r=reset q=quit")
                        y0 = 30
                        for line in info_lines:
                            cv2.putText(frame, line, (10, y0),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                            y0 += 24

                    # 绘制拖拽中的矩形框
                    if self._selecting:
                        cv2.rectangle(frame, self._sel_start, self._sel_end, (0, 0, 255), 1)
                    # 绘制已设置的裁剪区域
                    elif self.crop_region:
                        x, y, w, h = self.crop_region
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 0), 1)

                    cv2.imshow(window_name, frame)

                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q') or key == 27:
                        break
                    elif key == ord('c'):
                        self.capture_screenshot()
                    elif key == ord('r'):
                        self.clear_crop_region()
                        self._sel_start = (0, 0)
                        self._sel_end = (1067, 600)
                else:
                    logger.warning("未能捕获到帧")
                    time.sleep(0.1)

            cv2.destroyWindow(window_name)
            self.preview_active = False
            return True

        except Exception as e:
            logger.error(f"预览过程中发生错误: {str(e)}")
            cv2.destroyAllWindows()
            self.preview_active = False
            return False

    def stop_preview(self):
        """停止预览"""
        self.preview_active = False

    def capture_screenshot(self, save_dir: str = "screenshots") -> Optional[str]:
        """
        捕获当前帧并保存为截图

        参数:
            save_dir (str): 保存截图的目录

        返回:
            Optional[str]: 保存的文件路径，如果失败则返回None
        """
        if not self.is_connected():
            logger.error("无法截图：未连接到设备")
            return None

        # 创建保存目录
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        # 捕获当前帧
        frame = self.capture()
        if frame is None:
            logger.error("无法捕获帧")
            return None

        # 生成文件名 (BMP 格式)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(save_dir, f"screenshot_{timestamp}.bmp")

        # 保存图像
        try:
            cv2.imwrite(filename, frame)
            logger.info(f"截图已保存: {filename}")
            return filename
        except Exception as e:
            logger.error(f"保存截图失败: {str(e)}")
            return None

    def __del__(self):
        """析构函数，确保资源被释放"""
        self.disconnect()


# 使用示例
if __name__ == "__main__":
    # 创建采集卡连接实例
    capture_card = CaptureCardConnection()

    # 查找可用设备
    print("正在查找可用视频设备...")
    devices = capture_card.find_available_devices()

    if devices:
        print(f"找到 {len(devices)} 个可用设备:")
        for i, device in enumerate(devices):
            print(f"  {i}. {device['full_name']}")

        # 尝试连接第一个设备
        device_index = 0
        if capture_card.connect(device_index, (1920, 1080)):
            print(f"成功连接到设备: {devices[device_index]['name']}")

            # 获取连接信息
            info = capture_card.get_connection_info()
            if info:
                print(f"设备信息:")
                print(f"  名称: {info['device_name']}")
                print(f"  ID: {info['device_id']}")
                print(f"  分辨率: {info['resolution'][0]}x{info['resolution'][1]}")
                print(f"  后端: {info['backend']}")

            # 创建保存截图的目录
            if not os.path.exists('screenshots'):
                os.makedirs('screenshots')

            print("摄像头已打开")
            print("按键说明:")
            print("  空格键 - 截图")
            print("  c 键 - 在预览模式下截图")
            print("  r 键 - 重置裁剪区域")
            print("  ESC 或 q 键 - 退出")
            capture_card.set_crop_region(0,0,1067,600)
            # 启动预览
            capture_card.start_preview(duration=0)  # 0表示无限预览

            # 断开连接
            capture_card.disconnect()
        else:
            print(f"无法连接到设备: {devices[device_index]['name']}")
    else:
        print("未找到可用视频设备")
        print("请检查:")
        print("1. 采集卡是否已正确连接")
        print("2. 设备驱动程序是否已安装")
        print("3. 是否有足够的权限访问设备（尝试以管理员身份运行）")
