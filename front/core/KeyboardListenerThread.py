# -*- coding: utf-8 -*-
import threading
import time

from PyQt5.QtCore import pyqtSignal, QObject
from pynput import keyboard, mouse
import logging


# 自定义信号，用于从线程发送按键信息到主GUI
class KeyPressSignal(QObject):
    key_pressed = pyqtSignal(str)
    mouse_pressed = pyqtSignal(str, int, int)  # 新增鼠标信号：按钮名称, x坐标, y坐标
    mouse_moved = pyqtSignal(int, int)  # 新增鼠标移动信号：x坐标, y坐标


# 线程类，用于运行pynput键盘监听器
class KeyboardListenerThread(threading.Thread):
    def __init__(self, signal):
        self.running = True
        threading.Thread.__init__(self)
        self.keyboard_listener = None
        self.mouse_listener = None
        self.signal = signal

    def run(self):
        def on_press(key):
            try:
                if key == keyboard.Key.home:
                    self.signal.key_pressed.emit("start")
                elif key == keyboard.Key.end:
                    self.signal.key_pressed.emit("stop")
            except AttributeError:
                # 处理特殊键的情况（这里可以忽略）
                pass

        # 鼠标监听回调
        # 鼠标移动回调
        def on_mouse_move(x, y):
            self.signal.mouse_moved.emit(x, y)

        def on_mouse_click(x, y, button, pressed):
            button_name = str(button).split('.')[-1]  # 提取按钮名称（如 'left', 'right'）
            self.signal.mouse_pressed.emit(button_name, x, y)

        # 创建键盘监听器
        self.keyboard_listener = keyboard.Listener(on_press=on_press)
        self.keyboard_listener.start()

        # 创建鼠标监听器（同时监听移动和点击）
        self.mouse_listener = mouse.Listener(
            on_move=on_mouse_move,
            on_click=on_mouse_click
        )
        self.mouse_listener.start()

        print("输入监听器已启动")
        logging.info("输入监听器已启动")
        # 保持线程运行
        while self.running:
            time.sleep(0.1)  # 降低CPU使用率
        print("输入监听器已停止")
        logging.info("输入监听器已停止")

    def stop(self):
        self.running = False
        # 停止监听器
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        if self.mouse_listener:
            self.mouse_listener.stop()
