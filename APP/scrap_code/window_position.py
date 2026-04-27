import time
import traceback

import win32api
import win32con
import win32gui
from PyQt5.QtCore import QThread

from core.get_hwnd import hwnd
from utils.screenshot_util import screenshot_util
from core import global_variable as gv
from utils.cross_control import pyauto

# 获取当前显示器的宽度和高度
width = win32api.GetSystemMetrics(0)
height = win32api.GetSystemMetrics(1)


def get_window_rect():
    try:
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        return left, top
    except Exception as e:
        print("update_settings_group_data:", e)
        print("完整堆栈：")
        traceback.print_exc()


class WindowPositionUpdater(QThread):
    def __init__(self):
        super().__init__()
        self.last_position = get_window_rect()
        gv.last_position = self.last_position
        self.running = True
        self.count = 0

    def run(self):
        while self.running:
            self.update_position_if_changed()
            time.sleep(1)  # 延时1秒

    def update_position_if_changed(self):
        global width, height
        current_pos = get_window_rect()
        # 获取当前显示器的宽度和高度
        width_1 = win32api.GetSystemMetrics(0)
        height_1 = win32api.GetSystemMetrics(1)
        if current_pos != self.last_position:
            self.last_position = current_pos
            gv.last_position = self.last_position
            screenshot_util.activate_window_by_handle()  # 激活窗口
            print(f"游戏窗口被移动！新坐标{self.last_position}，原坐标：{self.last_position}")
        if width_1 != width or height != height_1:
            # 获取当前显示设置
            dm = win32api.EnumDisplaySettings(None, 0)

            # 修改显示设置
            dm.PelsWidth = width
            dm.PelsHeight = height
            dm.DisplayFixedOutput = win32con.DMDFO_DEFAULT

            # 应用新的显示设置
            win32api.ChangeDisplaySettings(dm, 0)
            # 检查当前活动窗口是否是我们想要保持活动的窗口
        if hwnd != win32gui.GetForegroundWindow():
            self.count += 1
            print(f"不是活动窗口{self.count}，20秒后重新激活窗口")
            time.sleep(20)
            pyauto.moveTo(self.last_position[0] + 640, self.last_position[1] + 40)
            time.sleep(0.1)
            pyauto.click()
            time.sleep(0.1)
            print(f"尝试鼠标点击窗口激活")

    def stop(self):
        self.running = False
