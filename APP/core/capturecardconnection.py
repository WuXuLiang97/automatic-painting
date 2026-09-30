# -*- coding: utf-8 -*-

import os
import platform
import time
from typing import Optional, Tuple, List, Dict

import cv2
import numpy as np

from core.global_variable import display_queue
from utils.logging_setup import logger

# 视频后端优先级。
# 探测与连接必须使用同一个后端：同一台采集卡在不同后端下的索引可能不同
# （本机实测 MSMF 下采集卡在 1 号、DSHOW 下同索引打不开），老代码探测时
# MSMF/DSHOW 混着试、真正连接时又用 CAP_ANY，索引含义会漂移，
# 于是出现"采集卡有时在设备 0、有时在设备 1"。
DEVICE_BACKENDS = (('MSMF', cv2.CAP_MSMF), ('DSHOW', cv2.CAP_DSHOW))

# 依次探测的分辨率（从大到小）。这是设备的 UVC 输出能力，与"当下有没有接 HDMI
# 信号"无关，因此可以稳定地用来区分设备：采集卡能到 1920x1080，普通摄像头到不了。
DEVICE_TEST_RESOLUTIONS = ((1920, 1080), (1280, 720), (640, 480))

# 能达到该宽度的设备判为采集卡
CAPTURE_CARD_MIN_WIDTH = 1920

# 探测的最大原始索引（含）。索引保持原样、不做压缩，避免"跳过打不开的设备后位置整体前移"
MAX_DEVICE_INDEX = 5

# 设备探测结果的缓存时长（秒）。探测要逐个打开设备并切分辨率，部分机器上要几十秒，
# 所以缓存时间放宽一点：进标签页探测一次，随后点连接直接复用
DEVICES_CACHE_SECONDS = 120

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
        self.max_device_index = MAX_DEVICE_INDEX  # 最大尝试设备索引数
        self.crop_region = None  # 裁剪区域 (x, y, width, height)
        self.device_identity = None  # 最近一次成功连接的设备身份（索引+后端+分辨率），供写回配置文件
        # 交互式裁剪选择状态
        self._selecting = False
        self._sel_start = (0, 0)
        self._sel_end = (0, 0)
        # 限速节流
        self._target_fps = 30.0  # 目标帧率
        self._min_frame_interval = 1.0 / self._target_fps
        self._last_capture_time = 0.0
        # 设备缓存
        self._devices_cache = None
        self._devices_cache_time = 0.0

    def _open_device(self, index, api):
        """按指定后端打开设备（不读帧）；打不开返回 None"""
        try:
            cap = cv2.VideoCapture(index, api)
            if cap.isOpened():
                return cap
            cap.release()
        except Exception as e:
            logger.warning(f"打开设备 index={index} api={api} 失败: {e}")
        return None

    def _probe_max_resolution(self, cap):
        """探测设备能输出的最大分辨率（从大到小逐个请求后回读）

        采集卡是 UVC 设备，输出能力是固定的（1920x1080），即使当前没有 HDMI 信号
        也能问出来，所以拿它当设备身份比索引可靠。
        """
        fallback = (0, 0)
        for width, height in DEVICE_TEST_RESOLUTIONS:
            try:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                time.sleep(0.05)
                real_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                real_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            except Exception:
                continue
            if real_width <= 0 or real_height <= 0:
                continue
            if real_width >= width and real_height >= height:
                # 驱动接受并回读了请求的分辨率
                return real_width, real_height
            if real_width * real_height > fallback[0] * fallback[1]:
                fallback = (real_width, real_height)
        return fallback

    def _probe_device(self, index):
        """探测原始索引 index：按后端优先级找一个能打开的后端，记录其最大输出分辨率

        每个索引只产出一个候选（第一个能打开的后端），避免同一台设备在
        MSMF / DSHOW 下各占一项、把下拉框搅乱。
        """
        for backend_name, api in DEVICE_BACKENDS:
            cap = self._open_device(index, api)
            if cap is None:
                continue
            try:
                max_resolution = self._probe_max_resolution(cap)
            finally:
                cap.release()
            supports_hd = max_resolution[0] >= CAPTURE_CARD_MIN_WIDTH
            return {
                'index': index,
                'backend': backend_name,
                'max_resolution': [max_resolution[0], max_resolution[1]],
                'supports_hd': supports_hd,
                'label': "{index} · {kind} · {w}x{h} · {backend}".format(
                    index=index,
                    kind='采集卡' if supports_hd else '其他设备',
                    w=max_resolution[0],
                    h=max_resolution[1],
                    backend=backend_name),
            }
        return None

    def find_available_devices(self, force_refresh=False) -> List[Dict]:
        """查找所有可用的视频设备（缓存 30 秒）

        注意：索引保持设备原本的原始索引，不做压缩。老代码按"能打开"过滤后
        重新编号，一旦某个设备被占用打不开，后面所有设备的下拉框取值都会前移，
        这就是"要猜着切换"的另一半原因。
        """
        if not force_refresh and self._devices_cache is not None:
            if time.time() - self._devices_cache_time < DEVICES_CACHE_SECONDS:
                return self._devices_cache

        devices = []
        # 并行探测，缩短等待（单个 MSMF 打开可能耗时数秒）
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=MAX_DEVICE_INDEX + 1) as pool:
            futures = {pool.submit(self._probe_device, i): i for i in range(MAX_DEVICE_INDEX + 1)}
            for f in as_completed(futures):
                try:
                    result = f.result()
                except Exception as e:
                    logger.warning(f"探测设备 {futures[f]} 异常: {e}")
                    continue
                if result:
                    devices.append(result)

        # 采集卡排在最前面（下拉框默认选中它），其余按原始索引
        devices.sort(key=lambda d: (not d['supports_hd'], d['index']))

        self._devices_cache = devices
        self._devices_cache_time = time.time()
        self.available_devices = devices
        logger.info(f"找到 {len(devices)} 个可用设备: {[d['label'] for d in devices]}")
        return devices

    def resolve_device(self, identity=None):
        """挑选本次应该连接的采集设备，返回 (候选设备, 选择原因)

        优先用已有的探测结果（缓存），只有缓存为空时才重新探测——MSMF 打开
        采集卡并切到 1080p 在部分机器上要几十秒，点"连接"时不该再等一遍。

        优先级：上次成功连接的同一设备（同索引同后端）→ 同索引（后端变了）
               → 按输出分辨率找回（索引漂移时）→ 能达到 1080p 的设备 → 第一个可用设备
        """
        devices = self.find_available_devices()
        if not devices:
            devices = self.find_available_devices(force_refresh=True)
        if not devices:
            return None, "没有找到任何可用视频设备"

        identity = identity or {}
        want_index = identity.get('index')
        want_backend = identity.get('backend')
        want_resolution = identity.get('max_resolution')

        if want_index is not None:
            for device in devices:
                if device['index'] == want_index and (not want_backend or device['backend'] == want_backend):
                    return device, f"沿用上次的设备：{device['label']}"
            for device in devices:
                if device['index'] == want_index:
                    return device, (f"索引 {want_index} 仍可用，后端 {want_backend} → "
                                    f"{device['backend']}：{device['label']}")
            if want_resolution:
                for device in devices:
                    if device['max_resolution'] == list(want_resolution):
                        return device, (f"上次设备的索引已漂移，按输出分辨率 "
                                        f"{want_resolution[0]}x{want_resolution[1]} 找回：{device['label']}")

        hd_devices = [d for d in devices if d['supports_hd']]
        if hd_devices:
            return hd_devices[0], f"按输出能力自动挑选（能出 1080p 即采集卡）：{hd_devices[0]['label']}"
        return devices[0], f"未发现 1080p 输出设备，退回第一个可用设备：{devices[0]['label']}"

    def connect_auto(self, identity=None, resolution: Optional[Tuple[int, int]] = (1920, 1080)) -> bool:
        """自动挑选并连接采集卡：优先上次的设备，连不上就按顺序回退

        :param identity: 上次成功连接的设备身份（配置里的 capture_device）
        :param resolution: 期望分辨率
        :return: 是否连接成功
        """
        identity = identity or {}
        current_identity = self.device_identity or {}
        # 已经连在这台设备上：直接返回，不必重新探测 + 重连（MSMF 重连要等几十秒）
        if (self.connection_status and self.cap is not None
                and current_identity.get('index') == identity.get('index')
                and current_identity.get('backend') == identity.get('backend')):
            logger.info(f"已经是目标设备 {current_identity.get('label')}，无需重连")
            return True

        candidate, reason = self.resolve_device(identity)
        if candidate is None:
            logger.error(reason)
            return False

        devices = list(self.available_devices)  # 复用 resolve 拿到的结果，避免重复探测
        logger.info(f"采集卡自动选择：{reason}")
        # 首选设备优先，其余按找出来的顺序兜底
        ordered = [candidate] + [d for d in devices if d is not candidate]
        for index, device in enumerate(ordered):
            if self._connect_candidate(device, resolution):
                if device is not candidate:
                    logger.warning(f"首选设备 {candidate['label']} 连接失败，已自动回退到 {device['label']}")
                return True
            logger.warning(f"连接 {device['label']} 失败，尝试下一个设备")
            if index == 0:
                # 首选就打不开，说明缓存结果过时了（设备被拔掉/占用），重新探测一轮再继续
                ordered = [candidate] + [d for d in self.find_available_devices(force_refresh=True)
                                         if d is not candidate]
                for device in ordered:
                    if self._connect_candidate(device, resolution):
                        logger.warning(f"重新探测后连上了 {device['label']}")
                        return True
                break
        logger.error("所有采集设备都连接失败")
        return False

    @staticmethod
    def frame_looks_blank(frame, threshold: float = 3.0) -> bool:
        """判断帧是否接近纯色画面

        采集卡开着但 HDMI 没信号时，通常输出纯黑/纯蓝的静帧，
        read() 会成功返回，所以光靠"能不能读到帧"判断不出没信号。
        """
        if frame is None:
            return True
        try:
            return float(frame.std()) < threshold
        except Exception:
            return False

    def check_signal(self, attempts: int = 10, interval: float = 0.05) -> bool:
        """连上后试探能否真的读到帧

        采集卡开着但没接 HDMI 信号时，cap 是打开的、却读不到帧，
        这种情况要单独提示，而不是笼统报"连接失败"。
        """
        if self.cap is None:
            return False
        for _ in range(attempts):
            try:
                ret, frame = self.cap.read()
            except Exception:
                ret, frame = False, None
            if ret and frame is not None:
                self.current_frame = frame
                return True
            time.sleep(interval)
        return False

    def connect(self, device_index: int, resolution: Optional[Tuple[int, int]] = None,
                backend: Optional[str] = None) -> bool:
        """
        连接到指定的采集卡设备（保留原签名，内部按候选设备处理）

        参数:
            device_index (int): 设备原始索引
            resolution (Optional[Tuple[int, int]]): 可选的分辨率设置 (宽度, 高度)
            backend (Optional[str]): 指定后端（MSMF / DSHOW），默认用探测到的那个

        返回:
            bool: 连接是否成功
        """
        candidate = None
        for device in self.find_available_devices():
            if device['index'] == device_index and (backend is None or device['backend'] == backend):
                candidate = device
                break
        if candidate is None:
            # 不在缓存列表里也照样试一次，避免探测失败导致完全无法连接
            candidate = {
                'index': int(device_index),
                'backend': backend or DEVICE_BACKENDS[0][0],
                'max_resolution': [0, 0],
                'supports_hd': False,
                'label': f"{device_index} · 未探测到 · {backend or DEVICE_BACKENDS[0][0]}",
            }
        return self._connect_candidate(candidate, resolution)

    def _connect_candidate(self, candidate, resolution: Optional[Tuple[int, int]] = None) -> bool:
        """按候选设备记录的"索引 + 后端"打开设备

        索引和后端必须一起用：只用索引会连到别的后端上、连到另一台设备。
        """
        # 已经连在同一台设备上就别再连一次：MSMF 重新打开 + 切分辨率要等几十秒
        current_identity = self.device_identity or {}
        if (self.connection_status and self.cap is not None
                and current_identity.get('index') == candidate.get('index')
                and current_identity.get('backend') == candidate.get('backend')):
            if not resolution or tuple(self.actual_resolution) == tuple(resolution):
                logger.info(f"已经连在 {candidate.get('label')} 上，跳过重复连接")
                return True

        # 保留裁剪区域：断开连接不应把 1067x600 的裁剪设置丢掉
        saved_crop_region = self.crop_region
        if self.cap is not None:
            self.disconnect()
        self.crop_region = saved_crop_region

        api = dict(DEVICE_BACKENDS).get(candidate.get('backend'))
        device_id = int(candidate['index'])

        try:
            if api is None:
                self.cap = cv2.VideoCapture(device_id)
            else:
                self.cap = cv2.VideoCapture(device_id, api)

            if not self.cap.isOpened():
                logger.error(f"无法打开设备 index={device_id} backend={candidate.get('backend')}")
                self.disconnect()
                return False

            # 设置分辨率（优先用调用方指定值，否则用探测到的最大分辨率）
            target = resolution or candidate.get('max_resolution') or (1920, 1080)
            try:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, target[0])
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, target[1])
            except Exception:
                pass

            # 限制采集卡输出帧率（从源头减少数据量）
            try:
                self.cap.set(cv2.CAP_PROP_FPS, 30)
            except Exception:
                pass
            # 自动对焦 / 自动曝光（对采集卡无效，摄像头才有意义）
            for prop in (cv2.CAP_PROP_AUTOFOCUS, cv2.CAP_PROP_AUTO_EXPOSURE):
                try:
                    self.cap.set(prop, 1)
                except Exception:
                    pass

            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.actual_resolution = (width, height)

            identity = dict(candidate)
            identity['index'] = device_id
            self.device_identity = identity
            self.device_name = candidate.get('label')
            self.device_id = str(device_id)
            self.connection_status = True
            self.last_check_time = time.time()

            logger.info(f"已成功连接到设备: {self.device_name}，实际分辨率: {width}x{height}")
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
                # 注意：不清除 crop_region。它是用户设的 1067x600 裁剪，
                # 老代码在这里清掉，导致"第二次连接（换设备）后画面变成 1920x1080、
                # 所有按 1067x600 写的坐标全部错位"。
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

    def set_target_fps(self, fps: float):
        """设置目标帧率（降低可减少网络带宽）"""
        self._target_fps = max(1.0, min(fps, 120.0))
        self._min_frame_interval = 1.0 / self._target_fps
        logger.info(f"目标帧率设置为: {self._target_fps:.0f} FPS")

    def _throttle(self):
        """节流：控制帧率上限"""
        now = time.time()
        elapsed = now - self._last_capture_time
        if elapsed < self._min_frame_interval:
            return False  # 帧太快，跳过
        self._last_capture_time = now
        return True

    def capture(self, blocking: bool = True) -> Optional[np.ndarray]:
        """
        捕获单帧图像（带 FPS 节流）

        参数:
            blocking (bool): 是否阻塞直到获取到帧

        返回:
            Optional[np.ndarray]: 捕获的帧图像 (OpenCV 格式)，如果失败则返回None
        """
        if not self.is_connected() or self.cap is None:
            return None

        # FPS 节流
        if not self._throttle():
            return self.current_frame  # 返回上一帧，避免重复读流

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
            print(f"  {device['label']}")

        # 自动挑选采集卡（优先能出 1080p 的设备）
        if capture_card.connect_auto(None, (1920, 1080)):
            print(f"成功连接到设备: {capture_card.device_identity}")
            print(f"是否有画面: {capture_card.check_signal()}")

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
            print("无法连接到任何采集设备，请检查占用情况（其他软件是否正在使用采集卡）")
    else:
        print("未找到可用视频设备")
        print("请检查:")
        print("1. 采集卡是否已正确连接")
        print("2. 设备驱动程序是否已安装")
        print("3. 是否有足够的权限访问设备（尝试以管理员身份运行）")
