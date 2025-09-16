# -*- coding: utf-8 -*-
# 初始化全局变量来存储上一次的位置
import queue
import threading

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
tab_index = 0
vid = ''
pid = ''
identifier = 0
display_queue = queue.Queue(maxsize=2)  # 展示专用队列
