from ultralytics import YOLO

model = YOLO("model_data/best.pt")
min_map_model = YOLO("model_data/min_map_best.pt")

model.export(
    format="onnx",
    dynamic=True,
    simplify=True,
    opset=11,
    half=True,
    device="cpu",
    verbose=False,
)
min_map_model.export(
    format="onnx",
    dynamic=True,
    simplify=True,
    opset=11,
    half=True,
    device="cpu",
    verbose=False,
)

# # 使用 OpenVINO 转换工具（mo = Model Optimizer）
# mo --input_model yolov8n.onnx \
#    --input_shape [1,3,320,320] \  # 固定输入尺寸（batch=1, 3通道, 320×320）
#    --data_type FP16 \  # 半精度，平衡速度和精度
#    --output_dir openvino_model  # 输出目录
