# -*- coding: utf-8 -*-
import json
import os
import random
import pydirectinput
import time
from utils.yjs import YJS
from utils.logging_setup import logger

# from utils.config_util import ini_file_path
# 拼接文件路径
ini_file_path = os.path.join('C:\\', "config.json")
pydirectinput.PAUSE = 0


class PYAUTO(YJS):
    left = 'left'
    right = 'right'
    up = 'up'
    down = 'down'

    def __init__(self):
        super().__init__()
        self.sign = None
        self.VNC = None
        self.PAUSE = 0.05
        pass

    def pyauto_init(self, sign, pause):
        self.sign = sign
        self.PAUSE = pause

    def releaseallkey(self):
        if self.sign == 0:
            pydirectinput.keyUp('left')
            pydirectinput.keyUp('right')
            pydirectinput.keyUp('up')
            pydirectinput.keyUp('down')
        elif self.sign == 1:
            logger.info(f"VNC键盘弹起所有键")
            self.VNC.key_up('left')
            self.VNC.key_up('right')
            self.VNC.key_up('up')
            self.VNC.key_up('down')
        else:
            self.ReleaseAllKey()

    def click(self, input_char='left'):
        """鼠标点击"""
        if self.sign == 0:
            pydirectinput.mouseDown(button=input_char)
            time.sleep(random.randint(50, 100) * 0.001)
            pydirectinput.mouseUp(button=input_char)
        elif self.sign == 1:
            if input_char == 'left':
                logger.info(f"VNC鼠标左点击：{input_char}")
                self.VNC.click(1)
            if input_char == 'right':
                logger.info(f"VNC鼠标右点击：{input_char}")
                self.VNC.click(3)
        else:
            if input_char == 'left':
                self.LeftClick()
            elif input_char == 'right':
                self.RightClick()

    def keyPressChar(self, input_char):
        """键盘点击"""
        if self.sign == 0:
            pydirectinput.keyDown(input_char)
            time.sleep(random.randint(30, 50) * 0.001)
            pydirectinput.keyUp(input_char)
        elif self.sign == 1:
            logger.info(f"VNC键盘点击：{input_char}")
            self.VNC.key_down(input_char)
            time.sleep(random.randint(50, 80) * 0.001)
            self.VNC.key_up(input_char)
            time.sleep(random.randint(50, 80) * 0.001)
        else:
            self.KeyPressChar(input_char)

    def moveTo(self, x, y):
        if self.sign == 0:
            pydirectinput.moveTo(x=x, y=y)
        elif self.sign == 1:
            logger.info(f"VNC鼠标移动：{(x, y)}")
            self.VNC.move(x + random.randint(-5, 5), y + random.randint(-5, 5))
        else:
            self.MoveTo(x, y)

    def keyDownChar(self, input_char):
        if self.sign == 0:
            pydirectinput.keyDown(input_char)
        elif self.sign == 1:
            logger.info(f"VNC键盘按下：{input_char}")
            self.VNC.key_down(input_char)
        else:
            self.KeyDownChar(input_char)

    def keyUpChar(self, input_char):
        if self.sign == 0:
            pydirectinput.keyUp(input_char)
        elif self.sign == 1:
            logger.info(f"VNC键盘弹起：{input_char}")
            self.VNC.key_up(input_char)
        else:
            self.KeyUpChar(input_char)


try:
    # with open(ini_file_path, 'r') as file:
    #     settings = json.load(file)
    # # 使用 get 方法安全地访问 'yjs' 键，如果不存在则默认为 0
    # sign = settings.get("yjs", 0)
    pyauto = PYAUTO()
except Exception as e:
    print(f"pyauto模块:{e}")
if __name__ == '__main__':
    # cunt = int(input("请输入需要消耗的点券：")) // 200

    from root_dir import root_path

    with open(os.path.join(root_path, "count.json"), 'r') as file:
        settings = json.load(file)
        cunt = settings.get("dianjuan", 0) // 200
        print(cunt)

    time.sleep(3)
    for i in range(cunt):
        pyauto.moveTo(random.randint(105, 120), random.randint(235, 250))
        time.sleep(random.uniform(0.1, 0.2))
        pyauto.click()
        time.sleep(random.uniform(0.1, 0.2))
        pyauto.moveTo(random.randint(724, 730), random.randint(100, 108))
        time.sleep(0.1)
        pyauto.click()
        time.sleep(random.uniform(0.1, 0.2))
        pyauto.moveTo(random.randint(470, 490), random.randint(550, 560))
        time.sleep(0.1)
        pyauto.click()
        time.sleep(1)
        pyauto.keyPressChar('space')
        time.sleep(random.uniform(1.5, 3.0))
        pyauto.keyPressChar('space')
        time.sleep(random.uniform(1.5, 3.0))
