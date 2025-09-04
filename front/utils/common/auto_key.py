# -*- coding: utf-8 -*-
import json
import os
import random
import pydirectinput
import time
from utils.log.logging_setup import logger
from global_fields import VNC_Connection, device_mouse_keyboard

# 禁用pydirectinput的默认延迟，加快自动化速度
pydirectinput.PAUSE = 0


class PYAUTO:
    """
    自动化输入控制类，支持三种模式：
    0 - 本地pydirectinput
    1 - VNC远程控制
    2 - yjs自定义接口
    """

    left = "left"
    right = "right"
    up = "up"
    down = "down"

    def __init__(self, sign):
        self.sign = sign  # 控制模式标志

    def releaseallkey(self):
        """释放所有方向键"""
        if self.sign == 0:
            pydirectinput.keyUp("left")
            pydirectinput.keyUp("right")
            pydirectinput.keyUp("up")
            pydirectinput.keyUp("down")
        elif self.sign == 1:
            logger.info(f"VNC键盘弹起所有键")
            VNC_Connection.key_up("left")
            VNC_Connection.key_up("right")
            VNC_Connection.key_up("up")
            VNC_Connection.key_up("down")
        else:
            device_mouse_keyboard.ReleaseAllKey()

    def click(self, input_char="left"):
        """鼠标点击，支持左/右键"""
        if self.sign == 0:
            pydirectinput.mouseDown(button=input_char)
            time.sleep(random.randint(50, 100) * 0.001)
            pydirectinput.mouseUp(button=input_char)
        elif self.sign == 1:
            if input_char == "left":
                logger.info(f"VNC鼠标左点击：{input_char}")
                VNC_Connection.click(1)
            if input_char == "right":
                logger.info(f"VNC鼠标右点击：{input_char}")
                VNC_Connection.click(3)
        else:
            if input_char == "left":
                device_mouse_keyboard.LeftClick()
            elif input_char == "right":
                device_mouse_keyboard.RightClick()

    def KeyPressChar(self, input_char):
        """键盘点击（按下并弹起）"""
        if self.sign == 0:
            pydirectinput.keyDown(input_char)
            time.sleep(random.randint(30, 50) * 0.001)
            pydirectinput.keyUp(input_char)
        elif self.sign == 1:
            logger.info(f"VNC键盘点击：{input_char}")
            VNC_Connection.key_down(input_char)
            time.sleep(random.randint(50, 80) * 0.001)
            VNC_Connection.key_up(input_char)
        else:
            device_mouse_keyboard.KeyPressChar(input_char)

    def moveTo(self, x, y):
        """鼠标移动到指定坐标"""
        if self.sign == 0:
            pydirectinput.moveTo(x=x, y=y)
        elif self.sign == 1:
            logger.info(f"VNC鼠标移动：{(x, y)}")
            VNC_Connection.move(x + random.randint(-5, 5), y + random.randint(-5, 5))
        else:
            device_mouse_keyboard.MoveTo(x, y)

    def KeyDownChar(self, input_char):
        """按下某个键（不弹起）"""
        if self.sign == 0:
            pydirectinput.keyDown(input_char)
        elif self.sign == 1:
            logger.info(f"VNC键盘按下：{input_char}")
            VNC_Connection.key_down(input_char)
        else:
            device_mouse_keyboard.KeyDownChar(input_char)

    def KeyUpChar(self, input_char):
        """弹起某个键"""
        if self.sign == 0:
            pydirectinput.keyUp(input_char)
        elif self.sign == 1:
            logger.info(f"VNC键盘弹起：{input_char}")
            VNC_Connection.key_up(input_char)
        else:
            device_mouse_keyboard.KeyUpChar(input_char)


# 初始化pyauto对象，默认VNC模式（sign=1）
try:
    pyauto = PYAUTO(1)
except Exception as e:
    print(f"pyauto模块:{e}")


if __name__ == "__main__":
    # 示例：批量点击和按键操作
    from root_dir import root_path

    with open(os.path.join(root_path, "count.json"), "r") as file:
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
        pyauto.KeyPressChar("space")
        time.sleep(random.uniform(1.5, 3.0))
        pyauto.KeyPressChar("space")
        time.sleep(random.uniform(1.5, 3.0))
