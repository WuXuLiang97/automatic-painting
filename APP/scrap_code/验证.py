import ctypes
import time
from io import BytesIO

import cv2
import numpy as np
from vncdotool import api
from vncdotool import KEYMAP

# 连接VNC服务器（虚拟机IP:端口）
client = api.connect('192.168.1.125::5900', password='')

# 模拟鼠标点击（坐标x=100, y=200，左键）
client.mouseMove(864, 594)
# client.mousePress(1)  # 1=左键, 2=中键, 3=右键
# client.mousePress(1)  # 1=左键, 2=中键, 3=右键

# 模拟键盘输入
# client.keyPress('a')  # 输入字符 'a'
# client.keyDown('right')  # 开始按下向下箭头
# time.sleep(2.5)  # 保持按下2.5秒
# client.keyUp('right')  # 释放
# client.keyPress('shift-h')  # 输入大写 'H'
# client.keyPress('ctrl-c')  # 组合键 Ctrl+C
image_size = 1440017
image_buffer = (ctypes.c_ubyte * image_size)
image = client.rcapture("rcapture.png", 0, 0, 1067, 600)

# 使用图像
cv2.imshow('VNC Screenshot', image)
cv2.waitKey(0)
client.disconnect()
# from core import capture

# import cv2
#
# image_bgr = capture.Capture(853962, 0, 0, 1067, 600)
# cv2.imshow('name', image_bgr)
# cv2.waitKey(0)
# cv2.destroyAllWindows()
