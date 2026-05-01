# -*- coding: utf-8 -*-
"""
YOLOv8 TensorRT 【多模型】极致并发版
✅ 支持任意多个模型、各自独立Engine
✅ 全局分开加载、权重隔离、互不干扰
✅ 每个线程独立Context/显存、无锁全并行
✅ 完全兼容新版TensorRT、Windows稳定运行
"""
import time
import tensorrt as trt
import numpy as np
import cv2
import os
import ctypes
import threading


# -------------------------- 全局【多模型】Engine管理器 --------------------------
class TrtEngineSingleton:
    """多模型全局引擎管理器，每个模型单独缓存Engine"""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                # 多模型字典：key=模型唯一标识, value=对应trt_engine
                cls._instance.engine_dict = {}
                cls._instance.TRT_LOGGER = trt.Logger(trt.Logger.WARNING)
        return cls._instance

    def init_engine(self, model_key, onnx_path, engine_path):
        # 已加载直接返回
        if model_key in self.engine_dict:
            return

        # 加载或构建引擎
        if os.path.exists(engine_path):
            with open(engine_path, 'rb') as f:
                runtime = trt.Runtime(self.TRT_LOGGER)
                engine = runtime.deserialize_cuda_engine(f.read())
        else:
            builder = trt.Builder(self.TRT_LOGGER)
            network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
            config = builder.create_builder_config()
            config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, 4 << 30)
            # 新版TRT兼容写法（关键，不报错）
            if builder.platform_has_fast_fp16:
                config.set_flag(trt.BuilderFlag.FP16)

            parser = trt.OnnxParser(network, self.TRT_LOGGER)
            with open(onnx_path, 'rb') as f:
                if not parser.parse(f.read()):
                    raise RuntimeError(f"模型[{model_key}] ONNX 解析失败")

            serialized_engine = builder.build_serialized_network(network, config)
            with open(engine_path, 'wb') as f:
                f.write(serialized_engine)

            runtime = trt.Runtime(self.TRT_LOGGER)
            engine = runtime.deserialize_cuda_engine(serialized_engine)

        # 存入多模型字典
        self.engine_dict[model_key] = engine

    def get_engine(self, model_key):
        return self.engine_dict.get(model_key)


# -------------------------- 线程私有CUDA内存管理（不变） --------------------------
class ThreadCudaMem:
    def __init__(self):
        self.cuda = ctypes.CDLL('nvcuda')
        self.cuda.cuMemAlloc_v2.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_ulonglong]
        self.cuda.cuMemFree_v2.argtypes = [ctypes.c_void_p]
        self.cuda.cuMemcpyHtoD_v2.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulonglong]
        self.cuda.cuMemcpyDtoH_v2.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulonglong]

        self.d_input = None
        self.d_output = None
        self.in_size = 0
        self.out_size = 0

    def realloc_if_need(self, in_bytes, out_bytes):
        if self.in_size == in_bytes and self.out_size == out_bytes:
            return
        self.free_all()
        self.d_input = self._alloc(in_bytes)
        self.d_output = self._alloc(out_bytes)
        self.in_size = in_bytes
        self.out_size = out_bytes

    def _alloc(self, size):
        ptr = ctypes.c_void_p()
        self.cuda.cuMemAlloc_v2(ctypes.byref(ptr), size)
        return ptr

    def free_all(self):
        if self.d_input:
            self.cuda.cuMemFree_v2(self.d_input)
            self.d_input = None
        if self.d_output:
            self.cuda.cuMemFree_v2(self.d_output)
            self.d_output = None

    def h2d(self, data_ptr, size):
        self.cuda.cuMemcpyHtoD_v2(self.d_input, data_ptr, size)

    def d2h(self, data_ptr, size):
        self.cuda.cuMemcpyDtoH_v2(data_ptr, self.d_output, size)


# -------------------------- 多模型 YOLOv8 TRT 主类 --------------------------
class YOLOv8TRTInfer:
    def __init__(self,
                 model_key,        # 【必传】模型唯一标识，如：fight、map、item
                 onnx_path,
                 engine_path,
                 class_names,
                 input_shape=(640, 640),
                 conf_thres=0.25,
                 nms_thres=0.45):

        self.model_key = model_key
        self.class_names = class_names
        self.input_shape = input_shape
        self.conf_thres = conf_thres
        self.nms_thres = nms_thres

        # 多模型管理器加载对应引擎
        self.engine_mgr = TrtEngineSingleton()
        self.engine_mgr.init_engine(model_key, onnx_path, engine_path)
        self.engine = self.engine_mgr.get_engine(model_key)

        # 线程本地隔离
        self._local = threading.local()

    def _get_thread_context(self):
        if not hasattr(self._local, 'context'):
            self._local.context = self.engine.create_execution_context()
            self._local.cuda_mem = ThreadCudaMem()
        return self._local.context, self._local.cuda_mem

    def _letterbox(self, img):
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
        img, ratio, top, left = self._letterbox(img)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.transpose(2, 0, 1).astype(np.float32) / 255.0
        return np.ascontiguousarray(img[None]), ratio, top, left

    @staticmethod
    def _xywh2xyxy(x):
        y = np.copy(x)
        y[..., 0] = x[..., 0] - x[..., 2] / 2
        y[..., 1] = x[..., 1] - x[..., 3] / 2
        y[..., 2] = x[..., 0] + x[..., 2] / 2
        y[..., 3] = x[..., 1] + x[..., 3] / 2
        return y

    def _nms(self, boxes, scores):
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
        pred = output[0].T
        boxes = self._xywh2xyxy(pred[:, :4])
        cls_scores = pred[:, 4:]
        max_scores = cls_scores.max(axis=1)
        classes = cls_scores.argmax(axis=1)
        mask = max_scores > self.conf_thres

        boxes, scores, classes = boxes[mask], max_scores[mask], classes[mask]
        if len(boxes) == 0:
            return []

        boxes[:, [0, 2]] -= left
        boxes[:, [1, 3]] -= top
        boxes /= ratio

        h, w = img.shape[:2]
        boxes = np.clip(boxes, 0, [w, h, w, h]).astype(np.int32)
        indices = self._nms(boxes, scores)

        res = []
        for i in indices:
            x1, y1, x2, y2 = boxes[i]
            cls_id = int(classes[i])
            conf = float(scores[i])
            label = self.class_names[cls_id] if 0 <= cls_id < len(self.class_names) else "unknown"
            res.append((label, x1, y1, x2, y2, conf))
        return res

    def predict(self, image):
        context, cuda_mem = self._get_thread_context()

        if isinstance(image, str):
            img = cv2.imread(image)
            if img is None:
                return []
        else:
            img = image

        input_data, ratio, top, left = self._preprocess(img)
        input_name = self.engine.get_tensor_name(0)
        output_name = self.engine.get_tensor_name(1)
        out_shape = self.engine.get_tensor_shape(output_name)

        in_bytes = input_data.nbytes
        out_bytes = np.prod(out_shape) * 4
        cuda_mem.realloc_if_need(in_bytes, out_bytes)

        cuda_mem.h2d(input_data.ctypes.data, in_bytes)
        context.set_input_shape(input_name, input_data.shape)
        context.execute_v2([cuda_mem.d_input.value, cuda_mem.d_output.value])

        output = np.empty(out_shape, dtype=np.float32)
        cuda_mem.d2h(output.ctypes.data, out_bytes)

        return self._postprocess(output, img, ratio, top, left)

    def __del__(self):
        if hasattr(self._local, "cuda_mem"):
            self._local.cuda_mem.free_all()


# ===================== 【多模型 实战调用示例】 =====================
if __name__ == "__main__":
    IMAGE_PATH = r"C:\Users\Administrator\Desktop\ultralytics-8.1.0\datasets\images\train\20260424_047.png"

    # ========== 模型1：战斗检测模型 ==========
    MODEL1_ONNX = r"C:\Users\Administrator\Downloads\automatic-painting\PadYolo\yolo\model_data\1_tensorrt_final.onnx"
    MODEL1_ENGINE = r"C:\Users\Administrator\Downloads\automatic-painting\PadYolo\yolo\model_data\1_tensorrt_final.engine"
    MODEL1_CLS = ['player', 'door', 'goods', 'continue', 'reward', 'forward', 'monster']

    # ========== 模型2：小地图检测模型 ==========
    MODEL2_ONNX = r"C:\Users\Administrator\Downloads\automatic-painting\PadYolo\yolo\model_data\min_map_best.onnx"
    MODEL2_ENGINE = r"C:\Users\Administrator\Downloads\automatic-painting\PadYolo\yolo\model_data\min_map_best.engine"
    MODEL2_CLS = ['map_hero','map_boss','map_query','map_elite','map_special','map_query_1']

    # 实例化多个模型，每个模型给唯一 model_key
    yolo_fight = YOLOv8TRTInfer(
        model_key="fight_model",   # 唯一标识
        onnx_path=MODEL1_ONNX,
        engine_path=MODEL1_ENGINE,
        class_names=MODEL1_CLS,
        conf_thres=0.3
    )

    yolo_map = YOLOv8TRTInfer(
        model_key="map_model",     # 唯一标识
        onnx_path=MODEL2_ONNX,
        engine_path=MODEL2_ENGINE,
        class_names=MODEL2_CLS,
        conf_thres=0.3
    )

    # ========== 多线程分别跑不同模型 ==========
    def thread_fight():
        while True:
            res = yolo_fight.predict(IMAGE_PATH)
            print(f"【战斗模型】检测目标数：{len(res)}")
            time.sleep(0.02)

    def thread_map():
        while True:
            res = yolo_map.predict(r'C:\Users\Administrator\Downloads\automatic-painting\PadYolo\yolo\model_data\2013.png')
            print(f"【小地图模型】检测目标数：{len(res)}")
            time.sleep(0.02)

    # 启动双模型并发
    threading.Thread(target=thread_fight, daemon=True).start()
    threading.Thread(target=thread_map, daemon=True).start()

    time.sleep(60)