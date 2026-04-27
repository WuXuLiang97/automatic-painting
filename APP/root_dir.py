import os
import sys

try:
    # 检查是否运行在打包后的可执行文件中
    if getattr(sys, 'frozen', False):
        # 如果运行在打包后的可执行文件中，使用 sys._MEIPASS
        root_path = sys._MEIPASS
    else:
        # 如果直接运行脚本，使用脚本的当前目录
        root_path = os.path.dirname(__file__)
except Exception as e:
    # 捕捉其他所有类型的异常
    print(f"发生了一个错误: {e}")
