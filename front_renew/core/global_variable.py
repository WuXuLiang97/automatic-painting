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

# 服务器配置（由主窗口初始化/更新，其它模块应只读使用）
global_server_ip = None  # 服务器IP地址，由 callMain.on_text_changed 写入
server_ip = global_server_ip  # 向后兼容的别名（推荐直接使用 global_server_ip）
global_server_port = 12345  # 服务器端口号（当前由配置文件控制）
server_port = global_server_port  # 向后兼容的别名

# 游戏相关配置（运行模式，由主窗口或配置决定）
global_banzhuan = None  # 游戏模式：0=搬砖，1/2为剧情等，由 callMain.on_combobox_changed 写入
banzhuan = global_banzhuan  # 向后兼容的别名
global_sy = False  # 深渊模式标志，由刷图逻辑在运行时切换
sy = global_sy  # 向后兼容的别名

# VMware虚拟机配置（由配置界面写入，其它模块只读）
vmware_ip = None  # 虚拟机IP
vmware_prot = None  # 虚拟机端口
vmware_password = None  # 虚拟机密码

# UI相关配置（当前选中的标签页索引等）
global_tab_index = 0  # 当前选中的标签页索引，由 callMain.on_tab_changed 写入
tab_index = global_tab_index  # 向后兼容的别名

# 设备标识符（由采集卡配置界面写入）
vid = ''  # 设备VID
pid = ''  # 设备PID
identifier = 0  # 设备标识符

# 线程通信队列
display_queue = queue.Queue(maxsize=2)  # 用于图像显示的队列
