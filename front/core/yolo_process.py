import time

from PyQt5.QtCore import pyqtSignal, QObject

from utils.screenshot_util import screenshot_util
from yolo.yolo_main import YoloV8


class YoloProcess(QObject):
    message = pyqtSignal(str)
    model_load_message = pyqtSignal(str)
    detect_message = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.yolo = None
        self.running = True

    def send_log(self, log):
        self.message.emit(log)

    def get_load_model_status(self):
        if self.yolo is None:
            return False
        return self.yolo.get_load_model_status()

    def load_model(self):
        self.yolo = YoloV8()
        self.send_log("模型加载中...")
        self.yolo.loadModel()
        self.send_log("模型加载完成")

    def process(self):
        while self.running:
            game_image = screenshot_util.get_game_screenshot()
            res = self.yolo.detect(game_image)
            self.detect_message.emit(res)
            time.sleep(0.001)

    def detect(self):
        game_image = screenshot_util.get_game_screenshot()
        res = self.yolo.detect(game_image)
        return res

    def detect_by_img(self, game_image):
        res = self.yolo.detect(game_image)
        return res

    def min_map_detect_by_img(self, game_image):
        res = self.yolo.min_map_detect(game_image)
        return res

    def stop(self):
        self.running = False
