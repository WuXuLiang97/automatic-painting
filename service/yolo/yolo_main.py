import os
import torch
from root_dir import root_path
import onnxruntime as ort
import platform

LOCAL_RANK = int(os.getenv("LOCAL_RANK", -1))  # 分布式训练相关，默认-1
MODEL_PATH = os.path.join(root_path, "yolo", "model_data", "best.onnx")
MIN_MAP_MODEL_PATH = os.path.join(
    root_path, "yolo", "model_data", "min_map_best.onnx"
)


class YoloV8:
    """
    YOLOv8推理封装类
    支持常规目标检测和小地图目标检测，自动选择GPU/CPU。
    """

    def __init__(self):
        # 初始化模型和参数
        self.min_map_model = None  # 小地图检测模型
        self.model = None  # 常规检测模型
        self.min_map_conf_thres = 0.5  # 小地图检测置信度阈值
        self.conf_thres = 0.3  # 常规检测置信度阈值
        self.iou_thres = 0.5  # IOU阈值

    def _detect_hardware(self):
        """检测硬件环境，返回最优推理引擎"""
        # 检查是否有GPU
        if torch.cuda.is_available():
            return "onnx", ["CUDAExecutionProvider", "CPUExecutionProvider"]

        # 检查是否为Intel CPU
        cpu_info = platform.processor().lower()
        if "intel" in cpu_info:
            # 检查OpenVINO模型是否存在
            if os.path.exists(OPENVINO_MODEL_PATH) and os.path.exists(
                OPENVINO_MIN_MAP_MODEL_PATH
            ):
                return "openvino", None
            else:
                print(
                    f"⚠️ OpenVINO模型文件不存在，将使用ONNX Runtime。请先转换模型: {OPENVINO_MODEL_PATH}"
                )

        # 其他CPU情况
        return "onnx", ["CPUExecutionProvider"]

    def loadModel(self):
        """
        加载YOLOv8模型权重
        """
        from ultralytics import YOLO

        providers = [
            "CUDAExecutionProvider",  # 优先 GPU
            "CPUExecutionProvider",  #  fallback 到 CPU
        ]

        self.model = ort.InferenceSession(MODEL_PATH, providers=providers)
        self.min_map_model = ort.InferenceSession(
            MIN_MAP_MODEL_PATH, providers=providers
        )

    def detect(self, game_image):
        """
        常规目标检测
        :param game_image: 输入图像（numpy数组）
        :return: 检测结果list，每项为(类别名, x1, y1, x2, y2, 置信度)
        """
        metrics = self.model.predict(
            game_image, iou_thres=self.iou_thres, conf_thres=self.conf_thres
        )
        res = []
        for m in metrics:
            names = m.names
            box = m.boxes
            if len(box):
                for i, det in enumerate(box):
                    label = names[int(det.cls)]
                    confidence = det.conf.item()
                    x1, y1, x2, y2 = det.xyxy[0].tolist()
                    res.append((label, x1, y1, x2, y2, confidence))
        return res

    def min_map_detect(self, game_image):
        """
        小地图目标检测
        :param game_image: 输入图像（numpy数组）
        :return: 检测结果list，每项为(类别名, x1, y1, x2, y2, 置信度)
        """
        metrics = self.min_map_model.predict(
            game_image, iou=self.iou_thres, conf=self.min_map_conf_thres
        )
        res = []
        for m in metrics:
            names = m.names
            box = m.boxes
            if len(box):
                for i, det in enumerate(box):
                    label = names[int(det.cls)]
                    confidence = det.conf.item()
                    x1, y1, x2, y2 = det.xyxy[0].tolist()
                    res.append((label, x1, y1, x2, y2, confidence))
        return res
