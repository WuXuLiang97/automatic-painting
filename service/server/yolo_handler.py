from yolo.yolo_main import YoloV8
from .logger import get_logger

logger = get_logger('yolo_handler')

class YoloHandler:
    """封装 YOLO 模型加载与推理"""
    def __init__(self, warmup_image=None):
        self.model = YoloV8(use_gpu=False)
        self._model_loaded = False
        try:
            self.model.loadModel()
            self._model_loaded = True
            if warmup_image is not None:
                # 预热阶段不需要返回结果
                try:
                    self.model.detect(warmup_image)
                    self.model.min_map_detect(warmup_image)
                except RuntimeError as e:
                    logger.warning(f"YOLO 预热失败（运行时错误）: {e}", exc_info=True)
                except ValueError as e:
                    logger.warning(f"YOLO 预热失败（参数错误）: {e}", exc_info=True)
                except Exception as e:
                    logger.warning(f"YOLO 预热失败（未知错误）: {e}", exc_info=True)
        except FileNotFoundError as e:
            logger.error(f"YOLO 模型文件未找到: {e}", exc_info=True)
            self._model_loaded = False
        except RuntimeError as e:
            logger.error(f"YOLO 模型加载失败（运行时错误）: {e}", exc_info=True)
            self._model_loaded = False
        except Exception as e:
            logger.error(f"YOLO 模型加载失败（未知错误）: {e}", exc_info=True)
            self._model_loaded = False

    def process(self, image):
        """处理常规目标检测"""
        if not self._model_loaded:
            raise RuntimeError("YOLO 模型未加载")
        if image is None:
            raise ValueError("输入图像为空")
        try:
            return self.model.detect(image)
        except RuntimeError as e:
            logger.error(f"YOLO 推理失败（运行时错误）: {e}", exc_info=True)
            raise
        except ValueError as e:
            logger.error(f"YOLO 推理失败（参数错误）: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"YOLO 推理失败（未知错误）: {e}", exc_info=True)
            raise
    
    def process_minimap(self, image):
        """处理小地图目标检测"""
        if not self._model_loaded:
            raise RuntimeError("YOLO 模型未加载")
        if image is None:
            raise ValueError("输入图像为空")
        try:
            return self.model.min_map_detect(image)
        except RuntimeError as e:
            logger.error(f"YOLO 小地图推理失败（运行时错误）: {e}", exc_info=True)
            raise
        except ValueError as e:
            logger.error(f"YOLO 小地图推理失败（参数错误）: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"YOLO 小地图推理失败（未知错误）: {e}", exc_info=True)
            raise
