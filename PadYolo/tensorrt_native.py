# -*- coding: utf-8 -*-
"""
YOLOv8 TensorRT 封装推理类
功能：高精度TensorRT推理，返回结果与Ultralytics YOLOv8 predict完全一致
"""
import tensorrt as trt
import numpy as np
import cv2
import time
import os
import ctypes


class YOLOv8TRTInfer:
    def __init__(self, onnx_path, engine_path, class_names, input_shape=(640, 640),
                 conf_thres=0.25, nms_thres=0.45):
        """
        初始化TensorRT推理类
        :param onnx_path: ONNX模型路径
        :param engine_path: TensorRT引擎保存路径
        :param class_names: 类别名称列表
        :param input_shape: 模型输入尺寸 (w, h)
        :param conf_thres: 置信度阈值
        :param nms_thres: NMS IOU阈值
        """
        # 基础配置
        self.onnx_path = onnx_path
        self.engine_path = engine_path
        self.class_names = class_names
        self.input_shape = input_shape
        self.conf_thres = conf_thres
        self.nms_thres = nms_thres

        # TensorRT 核心对象
        self.TRT_LOGGER = trt.Logger(trt.Logger.WARNING)
        self.engine = None
        self.context = None
        self.cuda_mem = None
        self.input_name = None
        self.output_name = None

        # CUDA内存初始化
        self.cuda_mem = self.SimpleCudaMem()

        # 加载/构建引擎
        self._init_engine()

    class SimpleCudaMem:
        """CUDA内存操作封装（内部类）"""
        def __init__(self):
            self.cuda = ctypes.CDLL('nvcuda')
            self.cuda.cuMemAlloc_v2.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_ulonglong]
            self.cuda.cuMemFree_v2.argtypes = [ctypes.c_void_p]
            self.cuda.cuMemcpyHtoD_v2.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulonglong]
            self.cuda.cuMemcpyDtoH_v2.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulonglong]

        def alloc(self, size):
            ptr = ctypes.c_void_p()
            self.cuda.cuMemAlloc_v2(ctypes.byref(ptr), size)
            return ptr

        def free(self, ptr):
            self.cuda.cuMemFree_v2(ptr)

        def h2d(self, dst, src, size):
            self.cuda.cuMemcpyHtoD_v2(dst, src, size)

        def d2h(self, dst, src, size):
            self.cuda.cuMemcpyDtoH_v2(dst, src, size)

    def _init_engine(self):
        """初始化TensorRT引擎（内部调用）"""
        # 加载已有引擎
        if os.path.exists(self.engine_path):
            self.engine = self._load_engine()
        else:
            # 构建新引擎
            self._build_engine()
            self.engine = self._load_engine()

        # 创建执行上下文
        self.context = self.engine.create_execution_context()
        self.input_name = self.engine.get_tensor_name(0)
        self.output_name = self.engine.get_tensor_name(1)

    def _build_engine(self):
        """构建TensorRT引擎"""
        builder = trt.Builder(self.TRT_LOGGER)
        network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
        config = builder.create_builder_config()
        config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, 4 << 30)
        if builder.platform_has_fast_fp16:
            config.set_flag(trt.BuilderFlag.FP16)

        parser = trt.OnnxParser(network, self.TRT_LOGGER)
        with open(self.onnx_path, 'rb') as f:
            if not parser.parse(f.read()):
                raise RuntimeError("ONNX模型解析失败！")

        serialized_engine = builder.build_serialized_network(network, config)
        with open(self.engine_path, 'wb') as f:
            f.write(serialized_engine)

    def _load_engine(self):
        """加载TensorRT引擎"""
        with open(self.engine_path, 'rb') as f:
            runtime = trt.Runtime(self.TRT_LOGGER)
            return runtime.deserialize_cuda_engine(f.read())

    def _letterbox(self, img):
        """图像等比例缩放+填充"""
        h, w = img.shape[:2]
        ratio = min(self.input_shape[0] / h, self.input_shape[1] / w)
        new_w = int(round(w * ratio))
        new_h = int(round(h * ratio))
        top = (self.input_shape[0] - new_h) // 2
        left = (self.input_shape[1] - new_w) // 2
        bottom = self.input_shape[0] - new_h - top
        right = self.input_shape[1] - new_w - left

        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114))
        return img, ratio, top, left

    def _preprocess(self, img):
        """图像预处理"""
        img, ratio, top, left = self._letterbox(img)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.transpose(2, 0, 1).astype(np.float32) / 255.0
        return np.ascontiguousarray(img[None]), ratio, top, left

    @staticmethod
    def _xywh2xyxy(x):
        """坐标格式转换"""
        y = np.copy(x)
        y[..., 0] = x[..., 0] - x[..., 2] / 2
        y[..., 1] = x[..., 1] - x[..., 3] / 2
        y[..., 2] = x[..., 0] + x[..., 2] / 2
        y[..., 3] = x[..., 1] + x[..., 3] / 2
        return y

    def _nms(self, boxes, scores):
        """非极大值抑制"""
        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]
        areas = (x2 - x1) * (y2 - y1)
        order = scores.argsort()[::-1]
        keep = []

        while order.size > 0:
            i = order[0]
            keep.append(i)
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            w = np.maximum(0.0, xx2 - xx1)
            h = np.maximum(0.0, yy2 - yy1)
            inter = w * h
            ovr = inter / (areas[i] + areas[order[1:]] - inter)
            inds = np.where(ovr <= self.nms_thres)[0]
            order = order[inds + 1]
        return keep

    def _postprocess(self, output, img, ratio, top, left):
        """
        后处理：返回和YOLO一致的结果列表
        :return: [(label, x1, y1, x2, y2, confidence), ...]
        """
        pred = output[0].T
        boxes = self._xywh2xyxy(pred[:, :4])
        cls_scores = pred[:, 4:]
        max_scores = cls_scores.max(axis=1)
        classes = cls_scores.argmax(axis=1)
        mask = max_scores > self.conf_thres

        boxes, scores, classes = boxes[mask], max_scores[mask], classes[mask]
        if len(boxes) == 0:
            return []

        # 坐标还原到原图
        boxes[:, [0, 2]] -= left
        boxes[:, [1, 3]] -= top
        boxes /= ratio

        # 修复：使用传入的img参数获取宽高
        h, w = img.shape[:2]
        boxes = np.clip(boxes, 0, [w, h, w, h]).astype(np.int32)

        # NMS
        indices = self._nms(boxes, scores)

        # 构造YOLO格式结果
        res = []
        for i in indices:
            x1, y1, x2, y2 = boxes[i]
            cls_id = int(classes[i])
            conf = float(scores[i])
            label = self.class_names[cls_id] if 0 <= cls_id < len(self.class_names) else "unknown"
            res.append((label, x1, y1, x2, y2, conf))
        return res

    def predict(self, image):
        """
        对外核心接口：与YOLOv8 predict返回格式完全一致
        :param image: 图片路径 或 cv2读取的BGR图像
        :return: 检测结果列表 [(label, x1, y1, x2, y2, confidence), ...]
        """
        d_input, d_output = None, None
        try:
            # 1. 读取图像
            if isinstance(image, str):
                img = cv2.imread(image)
                if img is None:
                    raise ValueError("图片读取失败！")
            else:
                img = image

            # 2. 预处理
            input_data, ratio, top, left = self._preprocess(img)

            # 3. 分配显存
            input_size = input_data.nbytes
            output_shape = self.engine.get_tensor_shape(self.output_name)
            output_size = np.prod(output_shape) * 4

            d_input = self.cuda_mem.alloc(input_size)
            d_output = self.cuda_mem.alloc(output_size)

            # 4. 推理
            self.cuda_mem.h2d(d_input, input_data.ctypes.data, input_size)
            self.context.execute_v2([d_input.value, d_output.value])

            # 5. 获取结果
            output = np.empty(output_shape, dtype=np.float32)
            self.cuda_mem.d2h(output.ctypes.data, d_output, output_size)

            # 6. 后处理返回结果（修复：传入img参数）
            return self._postprocess(output, img, ratio, top, left)

        finally:
            # 释放显存
            if d_input:
                self.cuda_mem.free(d_input)
            if d_output:
                self.cuda_mem.free(d_output)

    def __del__(self):
        """析构函数：释放所有资源"""
        del self.context, self.engine


# ===================== 【调用示例】 =====================
if __name__ == "__main__":
    # 1. 配置参数
    MODEL_PATH = r"D:\automatic-painting0501\PadYolo\yolo\model_data\1_tensorrt_final.onnx"
    ENGINE_PATH = r"D:\automatic-painting0501\PadYolo\yolo\model_data\1_tensorrt_final.engine"
    IMAGE_PATH = r"D:\automatic-painting0501\PadYolo\1.bmp"
    CLASS_NAMES = ['player', 'door', 'goods', 'continue', 'reward', 'forward', 'monster', 'monster_frost',
                   'boss_dlsks_klj', 'boss_dlsks_qtzft', 'boss_sy', 'boss_fbnl_phzwh', 'boss_fbnl_phzwh_box',
                   'door_sy', 'boss_sy-zmcbz', 'boss_sy-zmcbz_box', 'attack_boss_sy', 'boss_dlsks_onsblk',
                   'boss_115_1', 'boss_115_1_box', 'boss_115_2', 'boss_115_2_box', 'boss_115_3', 'boss_115_3_box',
                   'boss_115_4', 'boss_115_4_box', 'monster_115_1', 'monster_115_1_box', 'monster_115_2',
                   'monster_115_2_box', 'monster_115_3', 'monster_115_3_box', 'monster_115_4', 'monster_115_4_box',
                   'monster_115_5', 'monster_115_5_box', 'boss_sy_1', 'monster_115_6', 'monster_115_6_box', ]

    MIN_MODEL_PATH = r"D:\automatic-painting0501\PadYolo\yolo\model_data\min_map_best.onnx"
    MIN_ENGINE_PATH = r"D:\automatic-painting0501\PadYolo\yolo\model_data\min_map_best.engine"
    MIN_IMAGE_PATH = r"D:\automatic-painting0501\PadYolo\1.bmp"
    MIN_CLASS_NAMES = ['map_hero', 'map_boss', 'map_query', 'map_elite', 'map_special', 'map_query_1', ]
    # 2. 初始化TensorRT模型
    trt_model = YOLOv8TRTInfer(
        onnx_path=MODEL_PATH,
        engine_path=ENGINE_PATH,
        class_names=CLASS_NAMES,
        input_shape=(640, 640),
        conf_thres=0.25,
        nms_thres=0.45
    )

    # 2. 初始化TensorRT模型
    min_trt_model = YOLOv8TRTInfer(
        onnx_path=MIN_MODEL_PATH,
        engine_path=MIN_ENGINE_PATH,
        class_names=MIN_CLASS_NAMES,
        input_shape=(640, 640),
        conf_thres=0.25,
        nms_thres=0.45
    )

    # 3. 推理
    results = trt_model.predict(IMAGE_PATH)

    results2 = min_trt_model.predict(IMAGE_PATH)

    # 4. 输出结果
    print("检测结果：")
    for res in results:
        label, x1, y1, x2, y2, conf = res
        print(f"标签：{label}\t坐标：({x1},{y1},{x2},{y2})\t置信度：{conf:.2f}")

    print("检测结果2：")
    for res in results2:
        label, x1, y1, x2, y2, conf = res
        print(f"标签：{label}\t坐标：({x1},{y1},{x2},{y2})\t置信度：{conf:.2f}")