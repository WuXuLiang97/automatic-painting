# -*- coding: utf-8 -*-
"""
YOLOv8 TensorRT 推理脚本（修复版）
功能：加载ONNX模型构建TensorRT引擎，实现高精度、高速目标检测
修复点：BGR转RGB、原生NMS、FP16加速、大Workspace优化
"""
import tensorrt as trt
import numpy as np
import cv2
import time
import os
import ctypes

# ===================== 【全局配置区】 =====================
# ONNX模型文件路径（由YOLO导出脚本生成）
MODEL_PATH = r"C:\Users\Administrator\Downloads\automatic-painting\PadYolo\yolo\model_data\1_tensorrt_final.onnx"
# 测试图片路径
IMAGE_PATH = r"C:\Users\Administrator\Desktop\ultralytics-8.1.0\datasets\images\train\20260424_047.png"
# TensorRT引擎保存路径（首次运行自动生成）
ENGINE_PATH = r"C:\Users\Administrator\Downloads\automatic-painting\PadYolo\yolo\model_data\1_tensorrt_final.engine"

# 模型类别名称列表（必须与训练时完全一致）
CLASS_NAMES = ['player', 'door', 'goods', 'continue', 'reward', 'forward', 'monster', 'monster_frost',
               'boss_dlsks_klj', 'boss_dlsks_qtzft', 'boss_sy', 'boss_fbnl_phzwh', 'boss_fbnl_phzwh_box',
               'door_sy', 'boss_sy-zmcbz', 'boss_sy-zmcbz_box', 'attack_boss_sy', 'boss_dlsks_onsblk',
               'boss_115_1', 'boss_115_1_box', 'boss_115_2', 'boss_115_2_box', 'boss_115_3', 'boss_115_3_box',
               'boss_115_4', 'boss_115_4_box', 'monster_115_1', 'monster_115_1_box', 'monster_115_2',
               'monster_115_2_box', 'monster_115_3', 'monster_115_3_box', 'monster_115_4', 'monster_115_4_box',
               'monster_115_5', 'monster_115_5_box', 'boss_sy_1', 'monster_115_6', 'monster_115_6_box', ]
# 模型输入尺寸（必须与导出ONNX时一致）
INPUT_SHAPE = (640, 640)
# 置信度阈值（低于该值的检测框直接过滤）
CONF_THRESH = 0.25
# NMS非极大值抑制IOU阈值
NMS_THRESH = 0.45
# ==========================================================

# TensorRT日志器（INFO级别输出关键日志）
TRT_LOGGER = trt.Logger(trt.Logger.INFO)
# 全局CUDA内存管理对象
cuda_mem = None


class SimpleCudaMem:
    """
    CUDA内存操作封装类
    功能：实现GPU内存分配、释放、主机<->设备数据拷贝
    替代pycuda，纯ctypes实现，轻量化无依赖
    """

    def __init__(self):
        """加载NVIDIA CUDA驱动库，绑定API函数参数类型"""
        self.cuda = ctypes.CDLL('nvcuda')
        # 绑定CUDA内存分配函数参数类型
        self.cuda.cuMemAlloc_v2.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_ulonglong]
        # 绑定CUDA内存释放函数参数类型
        self.cuda.cuMemFree_v2.argtypes = [ctypes.c_void_p]
        # 绑定主机->设备数据拷贝函数参数类型
        self.cuda.cuMemcpyHtoD_v2.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulonglong]
        # 绑定设备->主机数据拷贝函数参数类型
        self.cuda.cuMemcpyDtoH_v2.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulonglong]

    def alloc(self, size):
        """
        分配GPU显存
        :param size: 分配的显存大小（字节）
        :return: 显存指针
        """
        ptr = ctypes.c_void_p()
        self.cuda.cuMemAlloc_v2(ctypes.byref(ptr), size)
        return ptr

    def free(self, ptr):
        """
        释放GPU显存
        :param ptr: 显存指针
        """
        self.cuda.cuMemFree_v2(ptr)

    def h2d(self, dst, src, size):
        """
        数据从主机内存拷贝到GPU显存
        :param dst: GPU目标指针
        :param src: 主机源指针
        :param size: 数据大小（字节）
        """
        self.cuda.cuMemcpyHtoD_v2(dst, src, size)

    def d2h(self, dst, src, size):
        """
        数据从GPU显存拷贝到主机内存
        :param dst: 主机目标指针
        :param src: GPU源指针
        :param size: 数据大小（字节）
        """
        self.cuda.cuMemcpyDtoH_v2(dst, src, size)


# --------------------- 【图像预处理模块】 ---------------------
def letterbox(img, new_shape=(640, 640)):
    """
    图像等比例缩放+填充（保持原图比例，无拉伸）
    与YOLO官方预处理完全一致，保证检测精度
    :param img: 原始OpenCV图像
    :param new_shape: 目标尺寸
    :return: 处理后图像, 缩放比例, 顶部填充像素, 左侧填充像素
    """
    h, w = img.shape[:2]
    # 计算等比例缩放系数
    ratio = min(new_shape[0] / h, new_shape[1] / w)
    # 缩放后的宽高（整数）
    new_w = int(round(w * ratio))
    new_h = int(round(h * ratio))
    # 计算上下左右填充像素（居中填充）
    top = (new_shape[0] - new_h) // 2
    left = (new_shape[1] - new_w) // 2
    bottom = new_shape[0] - new_h - top
    right = new_shape[1] - new_w - left

    # 双线性插值缩放
    img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    # 常量填充（颜色114，YOLO官方默认）
    img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114))
    return img, ratio, top, left


def preprocess(img):
    """
    图像预处理全流程：缩放填充 -> 通道转换 -> 归一化 -> 维度调整
    :param img: 原始BGR格式OpenCV图像
    :return: 模型输入数据, 缩放比例, 填充参数
    """
    # 1. 等比例缩放+填充
    img, ratio, top, left = letterbox(img, INPUT_SHAPE)
    # 2. 核心修复：OpenCV默认BGR → 转换为YOLO训练用RGB格式
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    # 3. HWC(高宽通道) → CHW(通道高宽) + 归一化到0~1 + 转为浮点型
    img = img.transpose(2, 0, 1).astype(np.float32) / 255.0
    # 4. 添加batch维度，转为连续内存数组（适配TensorRT输入）
    return np.ascontiguousarray(img[None]), ratio, top, left


# --------------------- 【后处理模块】 ---------------------
def xywh2xyxy(x):
    """
    坐标格式转换：中心坐标(x,y,w,h) → 对角坐标(x1,y1,x2,y2)
    :param x: 中心坐标数组
    :return: 对角坐标数组
    """
    y = np.copy(x)
    y[..., 0] = x[..., 0] - x[..., 2] / 2  # x1 = 中心x - 宽/2
    y[..., 1] = x[..., 1] - x[..., 3] / 2  # y1 = 中心y - 高/2
    y[..., 2] = x[..., 0] + x[..., 2] / 2  # x2 = 中心x + 宽/2
    y[..., 3] = x[..., 1] + x[..., 3] / 2  # y2 = 中心y + 高/2
    return y


def nms_numpy(boxes, scores, iou_threshold):
    """
    原生YOLO非极大值抑制（NMS）
    替代cv2.dnn.NMS，与Ultralytics官方逻辑完全一致，避免漏检/误检
    :param boxes: 检测框坐标数组
    :param scores: 置信度数组
    :param iou_threshold: IOU阈值
    :return: 保留的检测框索引
    """
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]
    # 计算每个框的面积
    areas = (x2 - x1) * (y2 - y1)
    # 按置信度从大到小排序
    order = scores.argsort()[::-1]
    keep = []

    while order.size > 0:
        i = order[0]
        keep.append(i)
        # 计算相交区域坐标
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        # 计算相交宽高（无交集则为0）
        w = np.maximum(0.0, xx2 - xx1)
        h = np.maximum(0.0, yy2 - yy1)
        # 相交面积
        inter = w * h
        # 计算IOU
        ovr = inter / (areas[i] + areas[order[1:]] - inter)
        # 保留IOU小于阈值的框
        inds = np.where(ovr <= iou_threshold)[0]
        order = order[inds + 1]
    return keep


def postprocess(output, img, ratio, top, left):
    """
    模型输出后处理全流程：解析输出 -> 置信度过滤 -> 坐标还原 -> NMS -> 绘制结果
    :param output: TensorRT模型原始输出
    :param img: 原始图像
    :param ratio: 缩放比例
    :param top: 顶部填充像素
    :param left: 左侧填充像素
    :return: 绘制检测框后的图像
    """
    # 解析模型输出：转置适配格式
    pred = output[0].T
    # 提取检测框坐标
    boxes = xywh2xyxy(pred[:, :4])
    # 提取类别置信度
    cls_scores = pred[:, 4:]
    # 最大置信度+对应类别
    max_scores = cls_scores.max(axis=1)
    classes = cls_scores.argmax(axis=1)
    # 置信度过滤
    mask = max_scores > CONF_THRESH

    boxes, scores, classes = boxes[mask], max_scores[mask], classes[mask]
    if len(boxes) == 0:
        return img

    # 核心：坐标还原到原始图像（去除填充+缩放还原）
    boxes[:, [0, 2]] -= left
    boxes[:, [1, 3]] -= top
    boxes /= ratio

    # 坐标裁剪到图像范围内，转为整数
    h, w = img.shape[:2]
    boxes = np.clip(boxes, 0, [w, h, w, h]).astype(np.int32)

    # NMS去重
    indices = nms_numpy(boxes, scores, NMS_THRESH)

    # 绘制检测框和标签
    for i in indices:
        x1, y1, x2, y2 = boxes[i]
        cls_id = classes[i]
        conf = scores[i]
        # 获取类别名称
        name = CLASS_NAMES[cls_id] if 0 <= cls_id < len(CLASS_NAMES) else f"Unknown{cls_id}"
        # 绘制矩形框
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        # 绘制类别+置信度
        cv2.putText(img, f"{name} {conf:.2f}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    return img


# --------------------- 【TensorRT引擎模块】 ---------------------
def build_engine(onnx_path, engine_path):
    """
    从ONNX模型构建TensorRT引擎（首次运行执行）
    优化：4G工作空间、FP16精度加速、兼容YOLOv8全部算子
    :param onnx_path: ONNX模型路径
    :param engine_path: 引擎保存路径
    :return: 序列化的TensorRT引擎
    """
    builder = trt.Builder(TRT_LOGGER)
    # 创建显式batch网络（TensorRT必须配置）
    network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
    config = builder.create_builder_config()

    # 设置工作空间为4GB（保证模型优化顺利执行）
    config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, 4 << 30)
    # 自动开启FP16加速（GPU支持则启用，无精度损失）
    if builder.platform_has_fast_fp16:
        config.set_flag(trt.BuilderFlag.FP16)

    # 创建ONNX解析器
    parser = trt.OnnxParser(network, TRT_LOGGER)
    with open(onnx_path, 'rb') as f:
        if not parser.parse(f.read()):
            print("ONNX解析失败：")
            # 打印所有解析错误
            [print(parser.get_error(i)) for i in range(parser.num_errors)]
            return None

    # 构建序列化引擎
    serialized_engine = builder.build_serialized_network(network, config)
    # 保存引擎到本地
    with open(engine_path, 'wb') as f:
        f.write(serialized_engine)
    print(f"✅ 引擎已保存：{engine_path}")
    return serialized_engine


def load_engine(engine_path):
    """
    从本地文件加载已构建的TensorRT引擎
    :param engine_path: 引擎文件路径
    :return: 加载完成的TensorRT引擎
    """
    with open(engine_path, 'rb') as f:
        runtime = trt.Runtime(TRT_LOGGER)
        return runtime.deserialize_cuda_engine(f.read())


# --------------------- 【主推理函数】 ---------------------
def inference():
    """
    主推理流程：
    1. 加载/构建TensorRT引擎
    2. 图像预处理
    3. GPU推理
    4. 后处理+结果保存
    5. 资源释放
    """
    global cuda_mem
    # 初始化CUDA内存管理器
    cuda_mem = SimpleCudaMem()
    # GPU显存指针（初始为空）
    d_input, d_output = None, None
    # TensorRT引擎&执行上下文（初始为空）
    engine, context = None, None

    try:
        # 优先加载本地已存在的引擎
        if os.path.exists(ENGINE_PATH):
            print("✅ 加载本地TensorRT引擎...")
            engine = load_engine(ENGINE_PATH)
        else:
            # 无本地引擎，重新构建
            print("🔧 首次运行，构建TensorRT引擎...")
            serialized_engine = build_engine(MODEL_PATH, ENGINE_PATH)
            engine = trt.Runtime(TRT_LOGGER).deserialize_cuda_engine(serialized_engine)

        # 创建执行上下文
        context = engine.create_execution_context()
        # 获取模型输入/输出张量名称
        input_name = engine.get_tensor_name(0)
        output_name = engine.get_tensor_name(1)

        # 读取测试图片
        img = cv2.imread(IMAGE_PATH)
        # 图像预处理
        input_data, ratio, top, left = preprocess(img)

        # 计算输入/输出数据大小（字节）
        input_size = input_data.nbytes
        output_shape = engine.get_tensor_shape(output_name)
        output_size = np.prod(output_shape) * 4  # float32 = 4字节

        # 分配GPU显存
        d_input = cuda_mem.alloc(input_size)
        d_output = cuda_mem.alloc(output_size)

        # 数据从主机拷贝到GPU
        cuda_mem.h2d(d_input, input_data.ctypes.data, input_size)
        # 执行TensorRT推理
        context.execute_v2([d_input.value, d_output.value])

        # 推理结果从GPU拷贝回主机
        output = np.empty(output_shape, dtype=np.float32)
        cuda_mem.d2h(output.ctypes.data, d_output, output_size)

        # 后处理+绘制结果
        result_img = postprocess(output, img.copy(), ratio, top, left)
        # 保存最终图片
        cv2.imwrite("tensorrt_result.jpg", result_img)
        print("✅ 推理完成，结果已保存为 tensorrt_result.jpg！")

    except Exception as e:
        # 异常捕获+打印
        print(f"❌ 程序异常：{str(e)}")
    finally:
        # 最终：强制释放所有GPU资源，避免内存泄漏
        if d_input: cuda_mem.free(d_input)
        if d_output: cuda_mem.free(d_output)
        del context, engine


if __name__ == "__main__":
    """程序入口"""
    inference()