# -*- coding: utf-8 -*-
import os
import time

import cv2
from PyQt5.QtCore import pyqtSignal, QThread
from utils.screen.screenshot_util import screenshot_util
from utils.common.auto_key import pyauto
from utils.common.image import FindPic, template_match
from utils.common.load_image import read_from_path
from global_fields import fields
from root_dir import root_path
from utils.log.logging_setup import logger

# from utils.yjs import yjs

current_path = os.path.dirname(os.path.abspath(__file__))


# root_path = os.path.abspath(os.path.join(current_path, '../'))


class CheckProcess(QThread):
    ghost_state_message = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.template = read_from_path(root_path + "/res/GhostState.png")
        self.template = cv2.cvtColor(self.template, cv2.COLOR_BGR2GRAY)
        self.su = screenshot_util
        self.running = True
        self.vnc_connection = None

    def run(self):
        logger.info(f"check_d.py 启动")
        self.running = True
        is_send_false = False
        while self.running:
            if fields["banzhuan"] != 0:
                ret = FindPic(
                    self.vnc_connection.capture(x1=0, y1=0, x2=1067, y2=600),
                    824,
                    446,
                    937,
                    500,
                    "huiguduihua.bmp",
                    0.9,
                )
                if ret:
                    logger.info(f"check_d.py：{ret}")
                    pyauto.KeyPressChar("esc")
                    time.sleep(0.2)
                    pyauto.KeyPressChar("space")
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
            if fields["sy"]:
                logger.info(f"check_d.py:深渊人物挂掉了用复活币")
                pyauto.KeyPressChar("x")
                time.sleep(0.2)
                pyauto.KeyPressChar("space")
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
