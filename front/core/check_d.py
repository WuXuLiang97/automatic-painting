# -*- coding: utf-8 -*-
import os
import time

import cv2
from PyQt5.QtCore import pyqtSignal, QThread
from utils.cv_recognizer import my_imread, vnc_mm
from utils.cv_util import template_match
from utils.cross_control import pyauto
from utils.screenshot_util import screenshot_util
from root_dir import root_path
from core import global_variable as gv
from utils.logging_setup import logger

# from utils.yjs import yjs

current_path = os.path.dirname(os.path.abspath(__file__))


# root_path = os.path.abspath(os.path.join(current_path, '../'))

class CheckProcess(QThread):
    ghost_state_message = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.template = my_imread(root_path + "/res/GhostState.png")
        self.template = cv2.cvtColor(self.template, cv2.COLOR_BGR2GRAY)
        # self.template1 = cv2.imread(root_path + "/res/guanbi.png")
        self.su = screenshot_util
        self.mm = vnc_mm
        self.running = True

    def run(self):
        logger.info(f"check_d.py 启动")
        self.running = True
        is_send_false = False
        # self.su.init_game_hwnd(mode=1)
        while self.running:
            if gv.banzhuan != 0:
                ret = self.mm.FindPic(824, 446, 937, 500, "huiguduihua.bmp", 0.9)
                if ret:
                    logger.info(f"check_d.py：{ret}")
                    pyauto.KeyPressChar('esc')
                    time.sleep(0.2)
                    pyauto.KeyPressChar('space')
                    time.sleep(0.2)
            game_image = self.su.get_game_screenshot()
            ghost_trait_img = game_image[404:464, 474:593]
            GRAY_img = cv2.cvtColor(ghost_trait_img, cv2.COLOR_BGR2GRAY)
            x, y = template_match(GRAY_img, self.template)
            if x is None or y is None:
                if not is_send_false:
                    self.ghost_state_message.emit("false")
                    is_send_false = True
                time.sleep(1)
                continue
            if gv.sy:
                logger.info(f"check_d.py:深渊人物挂掉了用复活币")
                pyauto.KeyPressChar('x')
                time.sleep(0.2)
                pyauto.KeyPressChar('space')
                time.sleep(0.2)
            else:
                logger.info(f"check_d.py:人物挂掉了")
                self.ghost_state_message.emit("true")
            is_send_false = False

            time.sleep(1)

        logger.info(f"check_d.py 终止")

    def stop(self):
        self.running = False
        self.wait(1000)
