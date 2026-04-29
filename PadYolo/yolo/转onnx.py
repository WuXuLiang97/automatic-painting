# -*- coding: utf-8 -*-
import os
import sys
from ultralytics import YOLO


# 1. 加载你的YOLO模型
model = YOLO(os.path.join("model_data", "0.pt"))

# 2. 核心：导出为ONNX格式（自动优化+简化）
model.export(
    format="onnx",       # 固定导出格式：ONNX
    simplify=True,       # ✅ 强烈推荐：简化模型，减小体积+提升推理速度
    opset=13,            # ONNX版本（12/13兼容性最好，通用所有平台）
    imgsz=640,           # 输入尺寸（必须和你训练时的尺寸一致！）
    device="cpu",        # 使用CPU导出（无显卡也能跑）
    # half=True,         # 可选：FP16半精度（减小模型体积，需要GPU支持）
)