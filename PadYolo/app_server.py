import sys
import threading
import tkinter as tk
from tkinter import scrolledtext
from image_recognition_server.cv_inference_server_2 import ThreadedServer, PrintRedirector
import socket


def get_ip_address():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        _ip = s.getsockname()[0]
        s.close()
        return _ip
    except Exception as e:
        print(f"获取 IP 地址时出现错误测试: {e}")
        return None


if __name__ == '__main__':
    ip = get_ip_address()
    root = tk.Tk()
    root.title(f"服务器日志-<{ip}>  <--请把这个ip填到<主机IP>的输入框里")
    root.geometry("800x600")

    text_area = scrolledtext.ScrolledText(root, width=80, height=30)
    # text_area.pack(padx=10, pady=10)
    text_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)  # 文本框会填充整个窗口剩余空间
    sys.stdout = PrintRedirector(text_area)

    server = ThreadedServer()
    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True
    server_thread.start()


    def on_closing():
        server.running = False
        root.destroy()


    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
