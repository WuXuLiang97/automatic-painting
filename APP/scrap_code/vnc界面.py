# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, messagebox
import vncdotool.api as vnc_api
import cv2
import numpy as np
from io import BytesIO
from threading import Thread
import os
import time


class VNCConnector:
    def __init__(self, root):
        self.root = root
        self.root.title("VNC连接工具")
        self.root.geometry("350x250")
        self.root.resizable(False, False)
        self.root.configure(bg="#f0f0f0")

        # 创建连接状态变量
        self.connected = False
        self.client = None

        # 创建UI
        self.create_widgets()

        # 设置默认值
        self.ip_var.set("127.0.0.1")
        self.port_var.set("5900")

    def create_widgets(self):
        # 创建样式
        style = ttk.Style()
        style.configure("TFrame", background="#f0f0f0")
        style.configure("TLabel", background="#f0f0f0", font=("Arial", 10))
        style.configure("TButton", font=("Arial", 10))
        style.configure("Connect.TButton", foreground="green", font=("Arial", 10, "bold"))
        style.configure("Disconnect.TButton", foreground="red", font=("Arial", 10, "bold"))
        style.configure("Screenshot.TButton", foreground="blue", font=("Arial", 10))

        # 创建主框架
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        title_label = ttk.Label(main_frame, text="VNC连接设置", font=("Arial", 12, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 15))

        # IP地址
        ip_label = ttk.Label(main_frame, text="服务器IP:")
        ip_label.grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)

        self.ip_var = tk.StringVar()
        ip_entry = ttk.Entry(main_frame, textvariable=self.ip_var, width=20)
        ip_entry.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)

        # 端口
        port_label = ttk.Label(main_frame, text="端口:")
        port_label.grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)

        self.port_var = tk.StringVar()
        port_entry = ttk.Entry(main_frame, textvariable=self.port_var, width=8)
        port_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)

        # 密码
        password_label = ttk.Label(main_frame, text="密码:")
        password_label.grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)

        self.password_var = tk.StringVar()
        password_entry = ttk.Entry(main_frame, textvariable=self.password_var,
                                   show="*", width=20)
        password_entry.grid(row=3, column=1, sticky=tk.EW, padx=5, pady=5)

        # 状态显示
        self.status_var = tk.StringVar()
        self.status_var.set("状态: 未连接")
        status_label = ttk.Label(main_frame, textvariable=self.status_var)
        status_label.grid(row=4, column=0, columnspan=2, pady=10)

        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10)

        # 连接/断开按钮
        self.connect_button = ttk.Button(button_frame, text="连接",
                                         command=self.toggle_connection,
                                         style="Connect.TButton")
        self.connect_button.pack(side=tk.LEFT, padx=5)

        # 截图按钮
        self.screenshot_button = ttk.Button(button_frame, text="截图",
                                            command=self.capture_screenshot,
                                            style="Screenshot.TButton",
                                            state=tk.DISABLED)
        self.screenshot_button.pack(side=tk.LEFT, padx=5)

        # 配置网格列权重
        main_frame.columnconfigure(1, weight=1)

    def toggle_connection(self):
        if self.connected:
            self.disconnect()
        else:
            self.connect()

    def connect(self):
        ip = self.ip_var.get()
        port = self.port_var.get()
        password = self.password_var.get()

        if not ip:
            messagebox.showerror("错误", "请输入服务器IP地址")
            return

        try:
            port = int(port)
        except ValueError:
            messagebox.showerror("错误", "端口号必须是数字")
            return

        # 更新UI状态
        self.status_var.set("状态: 连接中...")
        self.connect_button.config(state=tk.DISABLED)
        self.root.update()

        # 在新线程中连接
        Thread(target=self._connect_thread, args=(ip, port, password), daemon=True).start()

    def _connect_thread(self, ip, port, password):
        try:
            # 创建VNC客户端
            self.client = vnc_api.connect(f"{ip}:{port}", password=password)
            self.connected = True

            # 更新UI
            self.root.after(0, lambda: self.status_var.set(f"状态: 已连接到 {ip}:{port}"))
            self.root.after(0, lambda: self.connect_button.config(text="断开", state=tk.NORMAL))
            self.root.after(0, lambda: self.screenshot_button.config(state=tk.NORMAL))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("连接错误", f"连接失败: {str(e)}"))
            self.root.after(0, lambda: self.status_var.set("状态: 连接失败"))
            self.root.after(0, lambda: self.connect_button.config(state=tk.NORMAL))

    def disconnect(self):
        if self.client:
            try:
                self.client.disconnect()
            except:
                pass

        self.connected = False
        self.client = None

        # 更新UI
        self.status_var.set("状态: 已断开")
        self.connect_button.config(text="连接")
        self.screenshot_button.config(state=tk.DISABLED)

    def capture_screenshot(self):
        if not self.client or not self.connected:
            messagebox.showerror("错误", "未连接到VNC服务器")
            return

        # 在新线程中截图
        Thread(target=self._capture_thread, daemon=True).start()

    def _capture_thread(self):
        try:
            # 更新状态
            self.root.after(0, lambda: self.status_var.set("状态: 截取屏幕中..."))
            self.root.after(0, lambda: self.screenshot_button.config(state=tk.DISABLED))

            # 创建内存缓冲区
            buffer = BytesIO()

            # 截图
            self.client.captureScreen(buffer)

            # 获取截图数据
            buffer.seek(0)
            screenshot_bytes = buffer.getvalue()

            # 转换为OpenCV图像
            image = cv2.imdecode(np.frombuffer(screenshot_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)

            if image is None:
                self.root.after(0, lambda: messagebox.showerror("错误", "截图解码失败"))
                return

            # 保存截图
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"vnc_screenshot_{timestamp}.png"
            cv2.imwrite(filename, image)

            # 更新状态
            self.root.after(0, lambda: self.status_var.set(f"状态: 截图已保存为 {filename}"))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("截图错误", f"截图失败: {str(e)}"))

        finally:
            self.root.after(0, lambda: self.screenshot_button.config(state=tk.NORMAL))
            if self.connected:
                self.root.after(0, lambda: self.status_var.set(f"状态: 已连接到 {self.ip_var.get()}:{self.port_var.get()}"))


if __name__ == "__main__":
    root = tk.Tk()
    app = VNCConnector(root)
    root.mainloop()
