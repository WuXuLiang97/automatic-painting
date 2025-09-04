# -*- coding: utf-8 -*-
"""
@Time ： 2023/1/21 0:50
@Auth ： 大雄
@File ：main.py
@IDE ：PyCharm
@Email:3475228828@qq.com
安装命令:pip install opencv-python vncdotool -i https://mirrors.aliyun.com/pypi/simple

"""
import ctypes
import time

import cv2, numpy as np

from vncdotool import api
from vncdotool.client import KEYMAP

from global_fields import Capture_lock, display_queue


class KEY:
    left = "left"
    right = "right"
    up = "up"
    down = "down"


k = KEY()


class VNC:
    button_left = 1
    button_mid = 2
    button_right = 3

    def __init__(self, ip, prot, password=None):
        self.ip = ip + "::" + prot
        self.cmd = f"vncdo -s {self.ip} "
        self.client = api.connect(self.ip, password)
        self.key_map = KEYMAP
        self.image_size = 1440017  # 1024*768分辨率大小的
        self.image_buffer = (ctypes.c_ubyte * self.image_size)()

    def __del__(self):
        self.stop()

    def stop(self):
        self.client.disconnect()

    # 截图,可以保存到本地，也可以直接获取cv图像对象
    def capture(self, path=None):
        with Capture_lock:
            if path:
                self.client.captureScreen(path)
            else:  # 不写入图像,直接转cv图像bgr格式
                self.flush_screen(1)
                imgae = cv2.cvtColor(np.asarray(self.client.screen), cv2.COLOR_RGB2BGR)
                if not display_queue.full():
                    # 为展示线程缩小分辨率
                    display_frame = cv2.resize(imgae[0:600, 0:1067], (356, 200))
                    display_queue.put(display_frame)
                return imgae

    # 截图,可以保存到本地，也可以直接获取cv图像对象
    def capture(self, path=None, x1=0, y1=0, x2=1067, y2=600):
        with Capture_lock:
            if path:
                self.client.captureScreen(path)
            else:  # 不写入图像,直接转cv图像bgr格式
                self.flush_screen(1)
                imgae = cv2.cvtColor(np.asarray(self.client.screen), cv2.COLOR_RGB2BGR)
                if not display_queue.full():
                    # 为展示线程缩小分辨率
                    display_frame = cv2.resize(imgae[0:600, 0:1067], (356, 200))
                    display_queue.put(display_frame)
                return imgae[y1:y2, x1:x2]

    def capture_to_addr(self):
        self.flush_screen(1)
        image_bytes = np.asarray(self.client.screen).tobytes()
        ctypes.memmove(self.image_buffer, image_bytes, self.image_size)
        return ctypes.addressof(self.image_buffer), self.image_size

    # 移动鼠标
    def move(self, x, y):
        self.client.mouseMove(x, y)

    # 点击鼠标按钮,123分别对应左中右键
    def click(self, button=1, delay=0.05):
        self.client.mouseDown(button)
        time.sleep(delay)
        self.client.mouseUp(button)
        # self.flush_screen()

    # 移动并点击鼠标左键
    def left_click(self, x, y):
        self.move(x, y)
        self.click()
        self.flush_screen()

    # 双击鼠标左键
    def double_left_click(self, x, y):
        self.move(x, y)
        self.click()
        time.sleep(0.1)
        self.click()

    # 点击鼠标右键
    def right_click(self, x, y):
        self.move(x, y)
        self.click(3)

    # 拖动
    def drag(self, x, y, step=1):
        return self.client.mouseDrag(x, y, step)

    # 按键一次
    def key_press(self, key_str):
        # key_str可以参考 KEYMAP
        self.client.keyPress(key_str)
        self.flush_screen()

    # 刷新屏幕
    def flush_screen(self, incremental=1):
        return self.client.refreshScreen(incremental)  # 屏幕更改时才刷新,节省宽带

    def key_down(self, key_str):
        return self.client.keyDown(key_str)

    def key_up(self, key_str):
        return self.client.keyUp(key_str)

    # 组合键
    def hot_key(self, key_list):
        for key_str in key_list:
            self.key_down(key_str)
            time.sleep(0.05)
        for key_str in key_list[::-1]:
            self.key_down(key_str)
            time.sleep(0.05)


if __name__ == "__main__":
    try:
        v = VNC("192.168.1.125", "5900", "")
        print(v.client)
        time.sleep(2)
    except:
        print(v)

    api.shutdown()  # 关闭事件循环
