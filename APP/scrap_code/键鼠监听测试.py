# -*- coding: utf-8 -*-
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTextEdit, QVBoxLayout, QWidget, QPushButton
from PyQt5.QtCore import Qt

import threading
import time

from PyQt5.QtCore import pyqtSignal, QObject
from pynput import keyboard, mouse
import logging


# 自定义信号，用于从线程发送按键信息到主GUI
class KeyPressSignal(QObject):
    key_pressed = pyqtSignal(str)
    mouse_pressed = pyqtSignal(str, int, int)  # 新增鼠标信号：按钮名称, x坐标, y坐标


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
        def on_mouse_click(x, y, button, pressed):
            if pressed:  # 只处理按下事件
                # 发送按钮名称和坐标
                button_name = str(button).split('.')[-1]  # 提取按钮名称（如 'left', 'right'）
                self.signal.mouse_pressed.emit(button_name, x, y)

        # 创建键盘监听器
        self.keyboard_listener = keyboard.Listener(on_press=on_press)
        self.keyboard_listener.start()

        # 创建鼠标监听器
        self.mouse_listener = mouse.Listener(on_click=on_mouse_click)
        self.mouse_listener.start()

        print("输入监听器已启动")
        logging.info("输入监听器已启动")
        # 保持线程运行
        while self.running:
            time.sleep(0.1)  # 降低CPU使用率
        print("输入监听器已停止")
        logging.info("输入监听器已停止")
        # # 创建键盘监听器，并设置停止条件
        # with keyboard.Listener(on_press=on_press) as listener:
        #     while self.running:
        #         time.sleep(1)
        # print("KeyboardListenerThread 已停止")

    def stop(self):
        self.running = False
        # 停止监听器
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        if self.mouse_listener:
            self.mouse_listener.stop()


# 测试方法
def test_keyboard_listener():
    # 创建应用和主窗口
    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("输入监听测试")
    window.resize(600, 400)

    # 创建中央部件和布局
    central_widget = QWidget()
    layout = QVBoxLayout(central_widget)

    # 创建文本显示区域
    text_edit = QTextEdit()
    text_edit.setReadOnly(True)
    layout.addWidget(text_edit)

    # 创建停止按钮
    stop_button = QPushButton("停止监听")
    layout.addWidget(stop_button)

    # 设置中央部件
    window.setCentralWidget(central_widget)

    # 创建信号对象
    signal = KeyPressSignal()

    # 创建并启动监听线程
    listener_thread = KeyboardListenerThread(signal)
    listener_thread.start()

    # 定义信号处理函数
    def handle_key_press(key):
        text_edit.append(f"键盘事件: {key}")
        text_edit.append("")
        text_edit.verticalScrollBar().setValue(text_edit.verticalScrollBar().maximum())

    def handle_mouse_press(button, x, y):
        text_edit.append(f"鼠标事件: {button}键按下 - 位置({x}, {y})")
        text_edit.append("")
        text_edit.verticalScrollBar().setValue(text_edit.verticalScrollBar().maximum())

    # 连接信号
    signal.key_pressed.connect(handle_key_press)
    signal.mouse_pressed.connect(handle_mouse_press)

    # 停止按钮处理函数
    def stop_listener():
        listener_thread.stop()
        text_edit.append("监听器已停止")
        stop_button.setEnabled(False)

    stop_button.clicked.connect(stop_listener)

    # 窗口关闭事件处理
    def close_event(event):
        listener_thread.stop()
        event.accept()

    window.closeEvent = close_event

    # 显示窗口并运行应用
    window.show()
    sys.exit(app.exec_())


# 运行测试
if __name__ == "__main__":
    # 设置日志记录
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("input_listener.log"),
            logging.StreamHandler()
        ]
    )

    test_keyboard_listener()
