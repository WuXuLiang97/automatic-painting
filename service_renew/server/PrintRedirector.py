import tkinter as tk
import re


class PrintRedirector:
    """
    日志重定向类：
    将 print() 和 logging 输出内容重定向到 Tkinter 文本框，
    关闭窗口后自动失效，避免 TclError。
    支持识别日志级别并显示颜色。
    """
    COLORS = {
        'DEBUG': 'blue',
        'INFO': 'green',
        'WARNING': 'orange',
        'ERROR': 'red',
        'CRITICAL': 'purple',
        'RESET': 'black'
    }
    # 正则表达式匹配日志级别
    LOG_LEVEL_PATTERN = re.compile(r'^(?:\033\[\d+m)?\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} - (DEBUG|INFO|WARNING|ERROR|CRITICAL) -')

    def __init__(self, text_widget):
        """
        初始化方法
        :param text_widget: Tkinter 的文本框组件（如 ScrolledText）
        """
        self.text_widget = text_widget
        self._active = True
        # 配置标签颜色
        for level, color in self.COLORS.items():
            self.text_widget.tag_config(level, foreground=color)
        self.text_widget.tag_config('RESET', foreground=self.COLORS['RESET'])

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
            # 尝试匹配日志级别
            match = self.LOG_LEVEL_PATTERN.match(message)
            if match:
                level = match.group(1)
                self.text_widget.insert(tk.END, message, level)
            else:
                self.text_widget.insert(tk.END, message, 'RESET')
            self.text_widget.see(tk.END)
        except tk.TclError:
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
