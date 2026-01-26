# yolo_main.py
import os
from typing import Tuple
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
    YOLOv8 ONNX 推理封装类 (支持 GPU/CPU 选择)
    """
    def __init__(self, use_gpu: bool = True):
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

        # 新增：根据可用 providers 决定最终执行设备
        available = ort.get_available_providers()
        if use_gpu and "CUDAExecutionProvider" in available:
            self.providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        else:
            self.providers = ["CPUExecutionProvider"]

    def loadModel(self):
        """加载 ONNX 模型"""
        sess_opts = ort.SessionOptions()
        # 适度减少内存峰值
        sess_opts.enable_mem_pattern = True
        sess_opts.enable_cpu_mem_arena = True
        try:
            self.model = ort.InferenceSession(
                MODEL_PATH,
                sess_options=sess_opts,
                providers=self.providers,
            )
            self.min_map_model = ort.InferenceSession(
                MIN_MAP_MODEL_PATH,
                sess_options=sess_opts,
                providers=self.providers,
            )
            print(f"YOLO 模型加载完成，providers={self.model.get_providers()}")
        except Exception as e:
            raise RuntimeError(f"加载 YOLO 模型失败: {e}")

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
        后处理：解码输出 + 每个类别独立的 NMS
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

        # 初始化结果列表
        results = []
        
        # 对每个类别分别做 NMS
        for cls_id in range(len(class_names)):
            # 当前类别的掩码
            cls_mask = (class_ids == cls_id)
            cls_boxes = box_xyxy[cls_mask]
            cls_scores = scores[cls_mask]
            
            # 如果当前类别没有预测框，则跳过
            if len(cls_scores) == 0:
                continue
            
            # 执行 NMS
            keep = cv2.dnn.NMSBoxes(cls_boxes.tolist(), cls_scores.tolist(), conf_thres, iou_thres)
            
            if len(keep) > 0:
                keep = keep.flatten()
                for index in keep:
                    x1, y1, x2, y2 = map(int, cls_boxes[index])
                    confidence = float(cls_scores[index])
                    label = class_names[cls_id]
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