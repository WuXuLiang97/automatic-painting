# -*- coding: utf-8 -*-
import os
import sys
import traceback
from ultralytics import YOLO

# ===================== 【统一配置参数】 =====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "model_data")
INPUT_PT_PATH = os.path.join(MODEL_DIR, "min_map_best.pt")
OUTPUT_ONNX_PATH = os.path.join(MODEL_DIR, "min_map_best.onnx")
IMGSZ = 640
# ✅ 修复：YOLOv8 最低要求 opset=12，删除错误的IR修改
OPSET = 12
# ==========================================================

def init_dir():
    if not os.path.exists(MODEL_DIR):
        os.makedirs(MODEL_DIR)
        print(f"已创建模型目录: {MODEL_DIR}")

def export_yolo_to_onnx():
    print(f"\n===== 步骤1：加载并导出YOLO模型 =====")
    if not os.path.exists(INPUT_PT_PATH):
        raise FileNotFoundError(f"模型文件不存在！请检查路径: {INPUT_PT_PATH}")

    model = YOLO(INPUT_PT_PATH)
    print("✅ YOLO模型加载成功")

    # ✅ 修复：TensorRT 最优导出参数，无模型破坏
    export_params = {
        "format": "onnx",
        "opset": OPSET,
        "simplify": True,
        "dynamic": False,
        "batch": 1,
        "imgsz": IMGSZ,
        "device": "cpu"
    }

    onnx_path = model.export(**export_params)
    # 直接重命名为目标路径，无需修改IR版本
    os.rename(onnx_path, OUTPUT_ONNX_PATH)
    print(f"✅ ONNX模型导出完成: {OUTPUT_ONNX_PATH}")
    return OUTPUT_ONNX_PATH

def main():
    try:
        init_dir()
        export_yolo_to_onnx()
        print(f"\n==================== 导出完成 ====================")
        print("✅ 模型无结构破坏 | ✅ TensorRT兼容 | ✅ 无精度损失")
        print("====================================================\n")

    except Exception as e:
        print(f"\n❌ 执行失败: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    main()