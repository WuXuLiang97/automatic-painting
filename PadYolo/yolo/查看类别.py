# -*- coding: utf-8 -*-
import os
import sys

import torch
from ultralytics import YOLO
# 你的模型加载代码
model = YOLO(os.path.join("model_data", "min_map_best.pt"))

# ============= 核心：打印标签编号和对应名称 =============
a = []
a = list(model.names.values())
print(a)
print(f"总类别数量: {len(a)}")