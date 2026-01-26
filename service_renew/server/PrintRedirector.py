import tkinter as tk  # 用于GUI界面（显示服务器日志）


class PrintRedirector:
    """
    日志重定向类：
    将 print() 输出内容重定向到 Tkinter 文本框，
    关闭窗口后自动失效，避免 TclError。
    """

    def __init__(self, text_widget):
        """
        初始化方法
        :param text_widget: Tkinter 的文本框组件（如 ScrolledText）
        """
        self.text_widget = text_widget  # 保存文本框组件引用
        self._active = True

    def write(self, message):
        """
        写入日志到文本框
        :param message: 要写入的字符串
        """
        if not self._active:
            return
        if not message:
            return
        try:
            # 控件可能已经被销毁，销毁后访问会抛出 TclError
            self.text_widget.insert(tk.END, message)  # 插入到文本框末尾
            self.text_widget.see(tk.END)  # 自动滚动到最新内容
        except tk.TclError:
            # 标记失效，后续不再写入
            self._active = False

    def flush(self):
        """
        刷新方法（兼容 print 的 flush 参数，实际无需操作）
        """
        pass

    def close(self):
        """
        关闭方法：标记失效，避免 TclError
        """
        self._active = False
        self.text_widget = None
