import os

import torch

from root_dir import root_path

LOCAL_RANK = int(os.getenv('LOCAL_RANK', -1))


class YoloV8:
    def __init__(self):
        # 读取模型，这里传入训练好的模型
        self.min_map_model = None
        self.model = None
        self.x, self.y = (1280, 720)
        self.re_x, self.re_y = (1280, 720)
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.min_map_conf_thres = 0.5
        self.conf_thres = 0.3
        self.iou_thres = 0.5

    def loadModel(self):
        from ultralytics import YOLO
        self.model = YOLO(os.path.join(root_path, "yolo", "model_data", "best.engine"))
        # path_model = r"D:\server_env\app\yolo\model_data\best.pt"
        # self.model = YOLO(path_model)
        self.min_map_model = YOLO(os.path.join(root_path, "yolo", "model_data", "min_map_best.engine"))

    def detect(self, game_image):
        """
        # 返回数据类型：列表（list），其中每个元素是一个包含六个元素的元组（tuple）
        # 例子：
        [
        ('dog', 50, 100, 200, 250, 0.95),  # ('类别名', x1, y1, x2, y2, 置信度)
        ('cat', 30, 80, 150, 180, 0.80),
        # 更多检测到的目标...
        ]
        :param game_image:
        :return:
        """
        # 模型预测，save=True 的时候表示直接保存yolov8的预测结果
        metrics = self.model.predict(game_image, show=False, save=False, device=self.device, iou=self.iou_thres, conf=self.conf_thres, verbose=False)
        # 如果想自定义的处理预测结果可以这么操作，遍历每个预测结果分别的去处理
        res = []
        for m in metrics:
            names = m.names
            # 获取每个boxes的结果
            box = m.boxes
            if len(box):
                for i, det in enumerate(box):
                    label = names[int(det.cls)]
                    confidence = det.conf.item()
                    # print(f"label:{label}\tdet.cls:{det.cls}")
                    x1, y1, x2, y2 = det.xyxy[0].tolist()
                    res.append((label, x1, y1, x2, y2, confidence))
        return res

    def min_map_detect(self, game_image):
        """
        # 返回数据类型：列表（list），其中每个元素是一个包含六个元素的元组（tuple）
        # 例子：
        [
        ('dog', 50, 100, 200, 250, 0.95),  # ('类别名', x1, y1, x2, y2, 置信度)
        ('cat', 30, 80, 150, 180, 0.80),
        # 更多检测到的目标...
        ]
        :param game_image:
        :return:
        """
        # 模型预测，save=True 的时候表示直接保存yolov8的预测结果
        metrics = self.min_map_model.predict(game_image, show=False, save=False, device=self.device, iou=self.iou_thres, conf=self.min_map_conf_thres, verbose=False)
        # 如果想自定义的处理预测结果可以这么操作，遍历每个预测结果分别的去处理
        res = []
        for m in metrics:
            names = m.names
            # 获取每个boxes的结果
            box = m.boxes
            if len(box):
                for i, det in enumerate(box):
                    label = names[int(det.cls)]
                    confidence = det.conf.item()
                    # print(f"label:{label}\tdet.cls:{det.cls}")
                    x1, y1, x2, y2 = det.xyxy[0].tolist()
                    res.append((label, x1, y1, x2, y2, confidence))
        return res
