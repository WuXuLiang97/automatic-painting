# -*- coding: utf-8 -*-
"""
全局变量模块，定义应用程序中需要跨模块共享的全局变量和资源。

包含：
- 共享状态变量
- 配置信息
- 同步锁和队列等线程通信资源
"""
import queue
import threading

# 上次记录的位置坐标
default_position = (0, 0)
last_position = default_position  # 向后兼容的别名

# 线程同步锁资源
capture_lock = threading.Lock()  # 捕获操作的同步锁
Capture_lock = capture_lock  # 向后兼容的别名

# 服务器配置
global_server_ip = None  # 服务器IP地址
server_ip = global_server_ip  # 向后兼容的别名
global_server_port = 12345  # 服务器端口号
server_port = global_server_port  # 向后兼容的别名

# 游戏相关配置
global_banzhuan = None  # 游戏转职状态
banzhuan = global_banzhuan  # 向后兼容的别名
global_sy = False  # 深渊模式标志
sy = global_sy  # 向后兼容的别名

# VMware虚拟机配置
vmware_ip = None  # 虚拟机IP
vmware_prot = None  # 虚拟机端口
vmware_password = None  # 虚拟机密码

# UI相关配置
global_tab_index = 0  # 当前选中的标签页索引
tab_index = global_tab_index  # 向后兼容的别名

# 设备标识符
vid = ''  # 设备VID
pid = ''  # 设备PID
identifier = 0  # 设备标识符

# 线程通信队列
display_queue = queue.Queue(maxsize=2)  # 用于图像显示的队列
