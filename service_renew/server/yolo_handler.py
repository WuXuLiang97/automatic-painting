from yolo.yolo_main import YoloV8

class YoloHandler:
    """封装 YOLO 模型加载与推理"""
    def __init__(self, warmup_image=None):
        self.model = YoloV8(use_gpu=False)
        try:
            self.model.loadModel()
            if warmup_image is not None:
                # 预热阶段不需要返回结果
                try:
                    self.model.detect(warmup_image)
                    self.model.min_map_detect(warmup_image)
                except Exception as e:
                    print(f"YOLO 预热失败: {e}")
        except Exception as e:
            print(f"YOLO 模型加载失败: {e}")

    def process(self, image):
        return self.model.detect(image)
    
    def process_minimap(self, image):
        return self.model.min_map_detect(image)
