import sys
import threading
import tkinter as tk
from tkinter import scrolledtext
from config import SERVER_HOST, SERVER_PORT
from server.ThreadedServer import ThreadedServer
from server.PrintRedirector import PrintRedirector
import socket


def get_ip_address():
    """
    获取本机局域网IP地址。
    通过连接外部地址（如8.8.8.8）获取本地IP。
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        _ip = s.getsockname()[0]
        s.close()
        return _ip
    except Exception as e:
        print(f"获取 IP 地址时出现错误: {e}")
        return None


if __name__ == '__main__':
    # 获取本机IP，用于客户端连接提示
    ip = get_ip_address()
    # 创建Tkinter主窗口
    root = tk.Tk()
    root.title(f"服务器日志-<{ip}>  <--请把这个ip填到<主机IP>的输入框里")
    root.geometry("800x600")

    # 创建带滚动条的文本框用于显示服务器日志
    text_area = scrolledtext.ScrolledText(root, width=80, height=30)
    text_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)  # 文本框会填充整个窗口剩余空间
    # 重定向标准输出到文本框，方便查看日志
    sys.stdout = PrintRedirector(text_area)

    # 启动多线程服务器（后台线程）
    server = ThreadedServer(host=SERVER_HOST, port=SERVER_PORT)
    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True  # 主程序退出时自动关闭
    server_thread.start()

    def on_closing():
        """窗口关闭事件，安全关闭服务器和GUI"""
        server.running = False
        root.destroy()

    # 绑定窗口关闭事件
    root.protocol("WM_DELETE_WINDOW", on_closing)
    # 启动GUI主循环
    root.mainloop()
