# yolo_main.py
import os
from typing import Tuple
import torch
import cv2
import numpy as np
from root_dir import root_path
import onnxruntime as ort
import platform

LOCAL_RANK = int(os.getenv("LOCAL_RANK", -1))
MODEL_PATH = os.path.join(root_path, "yolo", "model_data", "best.onnx")
MIN_MAP_MODEL_PATH = os.path.join(root_path, "yolo", "model_data", "min_map_best.onnx")


class YoloV8:
    """
    YOLOv8 ONNX 推理封装类
    支持常规检测和小地图检测，自动选择 GPU/CPU。
    """

    def __init__(self):
        self.min_map_model = None  # ONNX Runtime session
        self.model = None          # ONNX Runtime session
        self.min_map_conf_thres = 0.5
        self.conf_thres = 0.3
        self.iou_thres = 0.5

        # 模型输入尺寸（请根据你导出的 ONNX 模型确认，通常是 640）
        self.input_size = 640  # 修改为你的模型实际尺寸，如 320, 640 等

        # 类别名：请确保顺序与训练时一致
        self.names = [
            "player",                    # 0
            "door",                      # 1
            "goods",                     # 2
            "continue",                  # 3
            "reward",                    # 4
            "forward",                   # 5
            "monster",                   # 6
            "monster_frost",             # 7
            "boss_dlsks_klj",            # 8
            "boss_dlsks_qtzft",          # 9
            "boss_sy",                   # 10
            "boss_fbnl_phzwh",           # 11
            "boss_fbnl_phzwh_box",       # 12
            "door_sy",                   # 13
            "boss_sy-zmcbz",             # 14
            "boss_sy-zmcbz_box",         # 15
            "attack_boss_sy",            # 16
            "boss_dlsks_onsblk",         # 17
            "boss_115_1",                # 18
            "boss_115_1_box",            # 19
            "boss_115_2",                # 20
            "boss_115_2_box",            # 21
            "boss_115_3",                # 22
            "boss_115_3_box",            # 23
            "boss_115_4",                # 24
            "boss_115_4_box",            # 25
            "monster_115_1",             # 26
            "monster_115_1_box",         # 27
            "monster_115_2",             # 28
            "monster_115_2_box",         # 29
            "monster_115_3",             # 30
            "monster_115_3_box",         # 31
            "monster_115_4",             # 32
            "monster_115_4_box",         # 33
            "monster_115_5",             # 34
            "monster_115_5_box",         # 35
            "boss_sy_1",                 # 36
            "monster_115_6",             # 37
            "monster_115_6_box",         # 38
        ]

        self.min_map_names = [
            "map_hero",      # 0
            "map_boss",      # 1
            "map_query",     # 2
            "map_elite",     # 3
            "map_special",   # 4
            "map_query_1",   # 5
        ]

    def _detect_hardware(self):
        """自动选择最优执行提供者：优先 GPU (CUDA)，否则 CPU"""
        if torch.cuda.is_available():
            return ["CUDAExecutionProvider", "CPUExecutionProvider"]

        # 如果没有 GPU，使用 CPU
        return ["CPUExecutionProvider"]

    def loadModel(self):
        """加载 ONNX 模型"""
        providers = self._detect_hardware()

        # 加载常规模型
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"模型文件不存在: {MODEL_PATH}")
        self.model = ort.InferenceSession(MODEL_PATH, providers=providers)

        # 加载小地图模型
        if not os.path.exists(MIN_MAP_MODEL_PATH):
            raise FileNotFoundError(f"小地图模型文件不存在: {MIN_MAP_MODEL_PATH}")
        self.min_map_model = ort.InferenceSession(MIN_MAP_MODEL_PATH, providers=providers)

        # 可选：打印模型输入信息用于调试
        # print(f"常规模型输入: {self.model.get_inputs()[0].name}, 形状: {self.model.get_inputs()[0].shape}")
        # print(f"小地图模型输入: {self.min_map_model.get_inputs()[0].name}, 形状: {self.min_map_model.get_inputs()[0].shape}")

        # print(f"✅ 模型已加载，使用设备: {providers[0]}")
        # print(f"   常规模型: {os.path.basename(MODEL_PATH)}")
        # print(f"   小地图模型: {os.path.basename(MIN_MAP_MODEL_PATH)}")

    def _preprocess(self, image: np.ndarray) -> Tuple[np.ndarray, float]:
        """预处理：缩放、填充、归一化"""
        h, w = image.shape[:2]
        scale = min(self.input_size / w, self.input_size / h)
        new_w = int(w * scale)
        new_h = int(h * scale)

        # 缩放
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # 填充到 input_size x input_size
        padded = np.zeros((self.input_size, self.input_size, 3), dtype=np.uint8)
        padded[:new_h, :new_w] = resized

        # HWC -> CHW, BGR -> RGB, 归一化
        padded = padded.astype(np.float32)
        padded = padded[:, :, ::-1].transpose(2, 0, 1)  # BGR2RGB + HWC2CHW
        padded /= 255.0

        # 添加 batch 维度
        input_tensor = np.expand_dims(padded, axis=0)  # [1, 3, 640, 640]
        return input_tensor, scale

    def _postprocess(
        self,
        output: np.ndarray,
        scale: float,
        conf_thres: float,
        iou_thres: float,
        class_names: list
    ) -> list:
        """
        后处理：解码输出 + NMS
        :param output: 模型原始输出
        :param scale: 缩放比例
        :param conf_thres: 置信度阈值
        :param iou_thres: NMS IoU 阈值
        :param class_names: 类别名列表（动态传入）
        :return: [(label, x1, y1, x2, y2, confidence), ...]
        """
        if output.ndim == 3:
            predictions = np.squeeze(output[0]).T  # [8400, num_classes + 4]
        else:
            raise ValueError("不支持的输出格式")

        boxes = predictions[:, :4]  # cx, cy, w, h
        scores = np.max(predictions[:, 4:], axis=1)
        class_ids = np.argmax(predictions[:, 4:], axis=1)

        # 置信度过滤
        valid_mask = scores >= conf_thres
        if not valid_mask.any():
            return []

        boxes = boxes[valid_mask]
        scores = scores[valid_mask]
        class_ids = class_ids[valid_mask]

        # cx,cy,w,h -> x1,y1,x2,y2
        box_xyxy = np.empty_like(boxes)
        box_xyxy[:, 0] = boxes[:, 0] - boxes[:, 2] / 2  # x1
        box_xyxy[:, 1] = boxes[:, 1] - boxes[:, 3] / 2  # y1
        box_xyxy[:, 2] = boxes[:, 0] + boxes[:, 2] / 2  # x2
        box_xyxy[:, 3] = boxes[:, 1] + boxes[:, 3] / 2  # y2

        # 反缩放
        box_xyxy /= scale

        # NMS
        indices = cv2.dnn.NMSBoxes(
            box_xyxy.tolist(), scores.tolist(), conf_thres, iou_thres
        )
        if len(indices) == 0:
            return []

        # 构造结果
        results = []
        indices = indices.flatten()
        for i in indices:
            x1, y1, x2, y2 = map(int, box_xyxy[i])
            confidence = float(scores[i])
            class_id = class_ids[i]
            if class_id >= len(class_names):
                continue  # 防止越界（模型输出类别 ID 超出范围）
            label = class_names[class_id]
            results.append((label, x1, y1, x2, y2, confidence))

        return results

    def detect(self, game_image):
        """
        常规目标检测
        :param game_image: numpy array (H, W, C), BGR
        :return: [(label, x1, y1, x2, y2, conf), ...]
        """
        if self.model is None:
            raise RuntimeError("模型未加载，请先调用 loadModel()")

        input_tensor, scale = self._preprocess(game_image)
        outputs = self.model.run(None, {self.model.get_inputs()[0].name: input_tensor})

        results = self._postprocess(
            outputs[0], scale, self.conf_thres, self.iou_thres, self.names
        )
        return results

    def min_map_detect(self, game_image):
        """
        小地图目标检测
        :param game_image: numpy array (H, W, C), BGR
        :return: [(label, x1, y1, x2, y2, conf), ...]
        """
        if self.min_map_model is None:
            raise RuntimeError("小地图模型未加载，请先调用 loadModel()")

        input_tensor, scale = self._preprocess(game_image)
        outputs = self.min_map_model.run(
            None, {self.min_map_model.get_inputs()[0].name: input_tensor}
        )

        results = self._postprocess(
            outputs[0], scale, self.min_map_conf_thres, self.iou_thres, self.min_map_names
        )
        return results