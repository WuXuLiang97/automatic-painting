import tkinter as tk  # 用于GUI界面（显示服务器日志）


class PrintRedirector:
    """
    日志重定向类：
    将 print() 和 logging 输出内容重定向到 Tkinter 文本框，
    关闭窗口后自动失效，避免 TclError。
    支持日志级别显示（通过颜色或前缀标识）。
    """

    def __init__(self, text_widget):
        """
        初始化方法
        :param text_widget: Tkinter 的文本框组件（如 ScrolledText）
        """
        self.text_widget = text_widget  # 保存文本框组件引用
        self._active = True
        # 配置标签样式（用于不同日志级别）
        self._setup_tags()

    def _setup_tags(self):
        """设置文本标签样式，用于不同日志级别"""
        try:
            # DEBUG - 灰色
            self.text_widget.tag_config("DEBUG", foreground="gray")
            # INFO - 黑色（默认）
            self.text_widget.tag_config("INFO", foreground="black")
            # WARNING - 橙色
            self.text_widget.tag_config("WARNING", foreground="orange")
            # ERROR - 红色
            self.text_widget.tag_config("ERROR", foreground="red")
            # CRITICAL - 深红色
            self.text_widget.tag_config("CRITICAL", foreground="darkred")
        except tk.TclError:
            # 如果标签配置失败，忽略（可能窗口已关闭）
            pass

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
            # 检测日志级别（logging 格式: "2025-01-XX XX:XX:XX - LEVEL - message"）
            tag = "INFO"  # 默认标签
            if " - DEBUG - " in message:
                tag = "DEBUG"
            elif " - INFO - " in message:
                tag = "INFO"
            elif " - WARNING - " in message:
                tag = "WARNING"
            elif " - ERROR - " in message:
                tag = "ERROR"
            elif " - CRITICAL - " in message:
                tag = "CRITICAL"
            
            # 控件可能已经被销毁，销毁后访问会抛出 TclError
            self.text_widget.insert(tk.END, message, tag)  # 插入到文本框末尾，应用标签
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
