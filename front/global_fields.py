# -*- coding: utf-8 -*-
# 初始化全局变量来存储上一次的位置
import queue
import threading
import win32api


# 创建一个队列用于存储图片数据
image_queue = queue.Queue()

# 创建一个全局变量用来判断启动线程没有
fields = {"called": False}

STOP_EVENT = threading.Event()
last_position = (0, 0)
# 创建一个锁对象
Capture_lock = threading.Lock()
server_ip = None
server_port = 12345
banzhuan = None
sy = False
vmware_ip = None
vmware_prot = None
vmware_password = None
display_queue = queue.Queue(maxsize=2)  # 展示专用队列

import utils.mockdevice.vnc as VNC

# 创建一个全局的VNC连接对象
VNC_Connection = None

from utils.screen.screenshot_util import ScreenshotUtil

screenshot_util = ScreenshotUtil()

from utils.mockdevice.DeviceMouseKeyboard import DeviceMouseKeyboard

# 获取屏幕的宽度和高度
screen_width = win32api.GetSystemMetrics(0)
screen_height = win32api.GetSystemMetrics(1)
device_mouse_keyboard = DeviceMouseKeyboard(screen_width, screen_height, 1)
