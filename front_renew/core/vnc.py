# -*- coding: utf-8 -*-
"""
@Time ： 2023/1/21 0:50
@Auth ： 大雄
@File ：main.py
@IDE ：PyCharm
@Email:3475228828@qq.com
安装命令:pip install opencv-python vncdotool -i https://mirrors.aliyun.com/pypi/simple

"""
import ctypes
import time

import cv2, numpy as np

from vncdotool import api
from vncdotool.client import KEYMAP

from core.global_variable import Capture_lock, display_queue


class KEY:
    left = 'left'
    right = 'right'
    up = 'up'
    down = 'down'


k = KEY()


class VNC:
    button_left = 1
    button_mid = 2
    button_right = 3

    def __init__(self, ip, prot, password=None):
        self.ip = ip + "::" + prot
        self.cmd = f"vncdo -s {self.ip} "
        self.client = api.connect(self.ip, password)
        self.key_map = KEYMAP
        self.image_size = 1440017  # 1024*768分辨率大小的
        self.image_buffer = (ctypes.c_ubyte * self.image_size)()

    def __del__(self):
        self.stop()

    def stop(self):
        self.client.disconnect()

    # 截图,可以保存到本地，也可以直接获取cv图像对象
    def capture(self, path=None):
        with Capture_lock:
            if path:
                self.client.captureScreen(path)
            else:  # 不写入图像,直接转cv图像bgr格式
                self.flush_screen(1)
                imgae = cv2.cvtColor(np.asarray(self.client.screen), cv2.COLOR_RGB2BGR)[0:600, 0:1067]
                if not display_queue.full():
                    # 为展示线程缩小分辨率
                    display_frame = cv2.resize(imgae, (356, 200))
                    display_queue.put(display_frame)
                return imgae

    def capture_to_addr(self):
        self.flush_screen(1)
        image_bytes = np.asarray(self.client.screen).tobytes()
        ctypes.memmove(self.image_buffer, image_bytes, self.image_size)
        return ctypes.addressof(self.image_buffer), self.image_size

    # 移动鼠标
    def move(self, x, y):
        self.client.mouseMove(x, y)

    # 点击鼠标按钮,123分别对应左中右键
    def click(self, button=1, delay=0.1):
        self.client.mouseDown(button)
        time.sleep(delay)
        self.client.mouseUp(button)
        # self.flush_screen()

    # 移动并点击鼠标左键
    def left_click(self, x, y):
        self.move(x, y)
        self.click()
        self.flush_screen()

    # 双击鼠标左键
    def double_left_click(self, x, y):
        self.move(x, y)
        self.click()
        time.sleep(0.1)
        self.click()

    # 点击鼠标右键
    def right_click(self, x, y):
        self.move(x, y)
        self.click(3)

    # 拖动
    def drag(self, x, y, step=1):
        return self.client.mouseDrag(x, y, step)

    # 按键一次
    def key_press(self, key_str):
        # key_str可以参考 KEYMAP
        self.client.keyPress(key_str)
        self.flush_screen()

    # 刷新屏幕
    def flush_screen(self, incremental=1):
        return self.client.refreshScreen(incremental)  # 屏幕更改时才刷新,节省宽带

    def key_down(self, key_str):
        return self.client.keyDown(key_str)

    def key_up(self, key_str):
        return self.client.keyUp(key_str)

    # 组合键
    def hot_key(self, key_list):
        for key_str in key_list:
            self.key_down(key_str)
            time.sleep(0.05)
        for key_str in key_list[::-1]:
            self.key_down(key_str)
            time.sleep(0.05)


if __name__ == '__main__':
    try:
        v = VNC("192.168.1.125", "5901", "")
        print(v.client)
        time.sleep(2)
        # new_image = v.capture(path=None)  # 获取新图像
        # print(type(new_image))
        # cv2.imshow("img", new_image)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()
        # api.shutdown()  # 关闭事件循环
    except:
        print(v)
    def is_colored(skill_img: np.ndarray, threshold=30):
        """
        判断图像是否为彩色的。阈值用于确定彩色和灰色的界限。
        """
        # 转换为灰度图像
        gray = cv2.cvtColor(skill_img, cv2.COLOR_BGR2GRAY)

        # 计算每个像素的绝对差值
        diff = cv2.absdiff(skill_img, cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR))
        diff_sum = np.sum(diff, axis=2)  # 求和RGB通道的差值
        print(f"is_colored:{np.mean(diff_sum)}")

        # 判断差值是否大于阈值
        return np.mean(diff_sum) > threshold
    x1, y1, x2, y2 = (162, 383, 256, 401)
    min_img = v.capture()[y1:y2, x1:x2]
    ret = is_colored(min_img, 50)


    # img_dict = {
    #     '0': ['0.bmp'], '1': ['1.bmp', '1-1.bmp'], '2': ['2.bmp', '2-1.bmp'],
    #     '3': ['3.bmp', '3-1.bmp'], '4': ['4.bmp', '4_1.bmp'],
    #     '5': ['5.bmp', '5-1.bmp'], '6': ['6.bmp', '6-1.bmp'], '7': ['7.bmp', '7-1.bmp'],
    #     '8': ['8.bmp', '8-1.bmp'], '9': ['9.bmp', '9-1.bmp']
    #
    # }
    # results = vnc_mm.screenshot_OCR_str(x1, y1, x2, y2, img_dict, 0.8, get_colour=([62, 130, 159], [65, 141, 163]), drag=None)
    # print(f"移速识别结果：{results}")
    # v.key_down(k.right)qqqqqqqqqqqq
    # time.sleep(0.05)
    # v.key_up(k.right)
    # time.sleep(0.05)
    # v.key_down(k.right)qqqqqqqqqqqqqqqq
    # time.sleep(1)
    # v.key_up(k.right)
    # time.sleep(0.05)
    # v.key_down("space")
    # time.sleep(0.1)
    # v.key_up("space")
    # # 键盘测试
    # v.key_press("a")
    # # 鼠标测试
    # v.move(200, 500)
    # v.click(1)
    # 截图测试
    # FPS = 0
    while True:
        s = time.time()
        new_image = v.capture(path=None)[0:600, 0:1067]  # 获取新图像

        FPS = 1 / (time.time() - s)
        # 绘制帧率
        cv2.putText(new_image, str(int(FPS)), (0, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        cv2.imshow("img", new_image)
        cv2.waitKey(1)
    api.shutdown()  # 关闭事件循环
