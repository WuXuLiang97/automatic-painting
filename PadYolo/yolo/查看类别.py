# -*- coding: utf-8 -*-
import os
import sys

import torch
from ultralytics import YOLO
# 你的模型加载代码
model = YOLO(os.path.join("model_data", "min_map_best.pt"))

# ============= 核心：打印标签编号和对应名称 =============
a = []
# 遍历字典，逐个输出编号和对应标签
for class_id, class_name in model.names.items():
    # print(f"  {class_id}: {class_name}")
    # print(f"  - {class_name}")
    print(f"'{class_name}',")
    a.append(class_name)
print(len(a))