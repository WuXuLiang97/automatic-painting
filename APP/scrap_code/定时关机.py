import tkinter as tk
from tkinter import messagebox
import subprocess
import threading
import time


class ShutdownTimer:
    def __init__(self, root):
        self.root = root
        self.root.title("定时关机")

        # 关机时间输入
        tk.Label(root, text="设置关机时间（秒）").pack()
        self.time_entry = tk.Entry(root)
        self.time_entry.pack()

        # 关机和取消按钮
        tk.Button(root, text="开始关机", command=self.start_shutdown).pack()
        tk.Button(root, text="取消关机", command=self.cancel_shutdown).pack()

        # 关机线程和标志
        self.shutdown_thread = None
        self.shutdown_flag = False

    def start_shutdown(self):
        try:
            shutdown_time = int(self.time_entry.get())
            if shutdown_time <= 0:
                messagebox.showerror("错误", "时间必须大于0")
                return

            self.shutdown_flag = True
            self.shutdown_thread = threading.Thread(target=self.shutdown_after_time, args=(shutdown_time,))
            self.shutdown_thread.start()
            messagebox.showinfo("提示", f"将在{shutdown_time}秒后关机")

        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")

    def shutdown_after_time(self, time_in_seconds):
        while time_in_seconds > 0 and self.shutdown_flag:
            time.sleep(1)
            time_in_seconds -= 1

        if self.shutdown_flag:
            # 这里使用Windows的shutdown命令，Linux/Mac请替换为相应的命令
            subprocess.run(['shutdown', '/s', '/t', '1'], check=True)

    def cancel_shutdown(self):
        self.shutdown_flag = False
        if self.shutdown_thread and self.shutdown_thread.is_alive():
            self.shutdown_thread.join()
        messagebox.showinfo("提示", "关机已取消")


if __name__ == "__main__":
    root = tk.Tk()
    app = ShutdownTimer(root)
    root.mainloop()