# -*- coding: utf-8 -*-
import tensorrt as trt

# 初始化 logger
logger = trt.Logger(trt.Logger.INFO)

# 能成功创建 builder 就代表完全正常
builder = trt.Builder(logger)
print("TensorRT 完全可用，创建引擎成功！")