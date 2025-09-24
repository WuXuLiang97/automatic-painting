# -*- coding: utf-8 -*-
"""DetectionFacade

职责：与远程检测 / OCR 服务的 Socket 协议通信。
已迁移自 core.detection_facade (保持向后兼容通过旧模块的转发)。

TODO 后续：
- 指数退避重试策略
- 熔断器 + 半开状态
- 结果结构化（DetectionBox 模型）
- metrics 回调钩子
"""
from __future__ import annotations
import json
import socket
import struct
import time
from typing import List, Tuple, Optional, Any

import cv2

from front.shared.constants import DetectionMessageType, WINDOW_WIDTH, WINDOW_HEIGHT
from front.shared.exceptions import DetectionError


class DetectionFacade:
    def __init__(self, server_ip: str | None, server_port: int, logger, timeout: float = 1.0):
        self.server_ip = server_ip
        self.server_port = server_port
        self.logger = logger
        self.timeout = timeout
        self.sock: Optional[socket.socket] = None

    # ---------------- Public API ---------------- #
    def connect(self):
        if not self.server_ip:
            raise DetectionError("server_ip 未设置")
        if self.sock:
            try:
                self.sock.close()
            except Exception:  # noqa: BLE001
                pass
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.logger.info(f"连接检测服务: {(self.server_ip, self.server_port)}")
        self.sock.connect((self.server_ip, self.server_port))

    def ensure_connection(self):
        if self.sock is None:
            self.connect()

    def detect_game(self, image) -> List[Any]:
        """发送游戏窗口截图做目标检测"""
        header, data = self._send_image(image, DetectionMessageType.GAME, width=WINDOW_WIDTH, height=WINDOW_HEIGHT)
        if header.get("type") != DetectionMessageType.GAME.value:
            raise DetectionError("返回类型不匹配(game_windows)")
        return data

    def detect_minimap(self, image) -> List[Any]:
        header, data = self._send_image(image, DetectionMessageType.MINIMAP, width=1, height=1)
        if header.get("type") != DetectionMessageType.MINIMAP.value:
            raise DetectionError("返回类型不匹配(min_map)")
        return data

    def ocr(self, image) -> str:
        header, data = self._send_image(image, DetectionMessageType.OCR, width=1, height=1)
        if header.get("type") != DetectionMessageType.OCR.value:
            raise DetectionError("返回类型不匹配(ocr)")
        return data  # type: ignore[return-value]

    # ---------------- Internal ---------------- #
    def _send_image(self, image, msg_type: DetectionMessageType, width: int, height: int):
        self.ensure_connection()
        try:
            img_bytes = cv2.imencode('.jpg', image)[1].tobytes()
            header_dict = {
                "type": msg_type.value,
                "width": width,
                "height": height,
                "image_size": len(img_bytes),
            }
            header_json = json.dumps(header_dict).encode('utf-8')
            header_len = struct.pack('!I', len(header_json))
            self._send_with_retry(header_len, "header_len")
            self._send_with_retry(header_json, "header")
            self._send_with_retry(img_bytes, f"image({len(img_bytes)})")
            header, payload = self._receive_message_from_server()
            return header, payload
        except (OSError, TimeoutError) as e:  # noqa: PERF203
            self.logger.warning(f"发送失败，重连中: {e}")
            self._reconnect()
            raise

    def _send_with_retry(self, data: bytes, tag: str, retries: int = 3):
        for attempt in range(1, retries + 1):
            try:
                assert self.sock is not None, "socket 未初始化"
                self.sock.sendall(data)
                return
            except OSError as e:
                self.logger.warning(f"发送 {tag} 失败 第{attempt}次: {e}")
                self._reconnect()
        raise DetectionError(f"发送 {tag} 失败 (重试用尽)")

    def _recv_exact(self, n: int) -> bytes:
        assert self.sock is not None, "socket 未初始化"
        buf = bytearray(n)
        view = memoryview(buf)
        received = 0
        while received < n:
            chunk = self.sock.recv(n - received)
            if not chunk:
                raise DetectionError("连接断开")
            view[received:received+len(chunk)] = chunk
            received += len(chunk)
        return bytes(buf)

    def _receive_message_from_server(self):
        header_len_buf = self._recv_exact(4)
        header_len = struct.unpack('!I', header_len_buf)[0]
        header_raw = self._recv_exact(header_len)
        header = json.loads(header_raw.decode('utf-8'))
        if 'type' not in header or 'data_size' not in header:
            raise DetectionError('协议缺少必要字段')
        data_buf = self._recv_exact(header['data_size'])
        try:
            payload = json.loads(data_buf.decode('utf-8'))
        except json.JSONDecodeError:
            payload = data_buf.decode('utf-8', errors='ignore')
        return header, payload

    def _reconnect(self):
        self.logger.info("尝试重连检测服务 ...")
        try:
            if self.sock:
                self.sock.close()
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.2)
        self.connect()

__all__ = ["DetectionFacade"]
